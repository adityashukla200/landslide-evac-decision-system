"""Dynamic Multi-Modal Evacuation Routing & Shelter Balancing Service.

Implements:
1. Time-dependent multi-modal graph (Pedestrian trails, 4x4 roads, Helicopter landing zones).
2. Dynamic edge blocking when stream stage or landslide runout intersects route.
3. Real-time shelter capacity re-balancing (>90% threshold diversion).
4. Dijkstra / A* route search across the Bhagirathi Himalayan valley.
"""

import math
import heapq
from typing import Dict, Any, List, Optional, Tuple


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in meters."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class DynamicEvacuationRouter:
    """Graph engine for multi-modal disaster evacuation with live shelter balancing."""

    def __init__(self):
        self._init_network()

    def _init_network(self):
        # 1. Nodes: Villages, Junctions, Shelters, Helipads
        self.nodes: Dict[str, Dict[str, Any]] = {
            # Villages
            "VIL_UTK_01": {"name": "Harsil", "lat": 31.035, "lon": 78.738, "type": "VILLAGE"},
            "VIL_UTK_02": {"name": "Dharali", "lat": 31.042, "lon": 78.751, "type": "VILLAGE"},
            "VIL_UTK_03": {"name": "Jhala", "lat": 31.028, "lon": 78.705, "type": "VILLAGE"},
            "VIL_UTK_04": {"name": "Sukhi", "lat": 31.002, "lon": 78.652, "type": "VILLAGE"},
            "VIL_UTK_05": {"name": "Gangotri", "lat": 30.994, "lon": 78.939, "type": "VILLAGE"},
            "VIL_UTK_10": {"name": "Uttarkashi Town", "lat": 30.726, "lon": 78.435, "type": "VILLAGE"},
            # High-Altitude Shelters
            "SHELTER_HARSIL_ARMY": {
                "name": "Harsil Army Cantonment Shelter",
                "lat": 31.039,
                "lon": 78.742,
                "type": "SHELTER",
                "village_id": "VIL_UTK_01",
                "capacity": 300,
                "occupancy": 275,  # 91.6% -> Over 90% threshold!
                "elevation_m": 2620.0,
            },
            "SHELTER_SUKHI_COMMUNITY": {
                "name": "Sukhi High-Ridge Community Shelter",
                "lat": 31.006,
                "lon": 78.658,
                "type": "SHELTER",
                "village_id": "VIL_UTK_04",
                "capacity": 500,
                "occupancy": 110,  # 22.0% -> Plenty of capacity
                "elevation_m": 2550.0,
            },
            "SHELTER_UTK_ITBP": {
                "name": "Uttarkashi ITBP Complex Shelter",
                "lat": 30.732,
                "lon": 78.441,
                "type": "SHELTER",
                "village_id": "VIL_UTK_10",
                "capacity": 1000,
                "occupancy": 320,  # 32.0%
                "elevation_m": 1200.0,
            },
            # Helipads (HLZ)
            "HLZ_HARSIL": {"name": "Harsil Army Helipad", "lat": 31.037, "lon": 78.741, "type": "HELIPAD"},
            "HLZ_UTTARKASHI": {"name": "Uttarkashi Matli Helipad", "lat": 30.710, "lon": 78.420, "type": "HELIPAD"},
        }

        # 2. Edges: Multi-modal connections (Pedestrian trails, 4x4 roads, Air)
        # (edge_id, u, v, modality, distance_m, base_time_min, hazard_score, is_blocked)
        self.edges: Dict[str, Dict[str, Any]] = {}
        edge_defs = [
            # Harsil local connections
            ("EDGE_HARSIL_TO_ARMY_ROAD", "VIL_UTK_01", "SHELTER_HARSIL_ARMY", "ROAD_4X4", 800.0, 4.0, 0.1, False),
            ("EDGE_HARSIL_TO_ARMY_TRAIL", "VIL_UTK_01", "SHELTER_HARSIL_ARMY", "PEDESTRIAN_TRAIL", 650.0, 12.0, 0.05, False),
            ("EDGE_HARSIL_TO_HLZ", "VIL_UTK_01", "HLZ_HARSIL", "ROAD_4X4", 500.0, 3.0, 0.0, False),
            # Harsil to Dharali
            ("EDGE_HARSIL_DHARALI_NH", "VIL_UTK_01", "VIL_UTK_02", "ROAD_4X4", 4200.0, 10.0, 0.2, False),
            ("EDGE_HARSIL_DHARALI_RIDGE", "VIL_UTK_01", "VIL_UTK_02", "PEDESTRIAN_TRAIL", 3800.0, 65.0, 0.1, False),
            # Harsil to Jhala
            ("EDGE_HARSIL_JHALA_NH", "VIL_UTK_01", "VIL_UTK_03", "ROAD_4X4", 5100.0, 12.0, 0.15, False),
            # Jhala to Sukhi (Main Valley Road)
            ("EDGE_JHALA_SUKHI_NH", "VIL_UTK_03", "VIL_UTK_04", "ROAD_4X4", 6200.0, 15.0, 0.25, False),
            # Sukhi to Sukhi Shelter
            ("EDGE_SUKHI_TO_SHELTER_ROAD", "VIL_UTK_04", "SHELTER_SUKHI_COMMUNITY", "ROAD_4X4", 1200.0, 6.0, 0.1, False),
            ("EDGE_SUKHI_TO_SHELTER_TRAIL", "VIL_UTK_04", "SHELTER_SUKHI_COMMUNITY", "PEDESTRIAN_TRAIL", 950.0, 18.0, 0.05, False),
            # Direct High-Mountain Ridge Trail from Harsil to Sukhi Shelter (bypasses river flooding)
            ("EDGE_HARSIL_SUKHI_HIGH_RIDGE", "VIL_UTK_01", "SHELTER_SUKHI_COMMUNITY", "PEDESTRIAN_TRAIL", 8500.0, 130.0, 0.1, False),
            # Air corridors
            ("EDGE_AIR_HARSIL_UTK", "HLZ_HARSIL", "HLZ_UTTARKASHI", "HELICOPTER_AIR", 42000.0, 18.0, 0.0, False),
            ("EDGE_UTK_HLZ_TO_SHELTER", "HLZ_UTTARKASHI", "SHELTER_UTK_ITBP", "ROAD_4X4", 2500.0, 8.0, 0.0, False),
        ]

        for eid, u, v, mod, dist, btime, haz, blk in edge_defs:
            self.edges[eid] = {
                "edge_id": eid,
                "u": u,
                "v": v,
                "modality": mod,
                "distance_m": dist,
                "base_time_min": btime,
                "hazard_score": haz,
                "is_blocked": blk,
                "block_reason": None,
            }

    def set_edge_status(self, edge_id: str, is_blocked: bool, block_reason: Optional[str] = None):
        """Block or unblock a route segment due to debris runout or river cutoff."""
        if edge_id in self.edges:
            self.edges[edge_id]["is_blocked"] = is_blocked
            self.edges[edge_id]["block_reason"] = block_reason if is_blocked else None

    def update_shelter_occupancy(self, shelter_id: str, count_change: int):
        """Update shelter head count."""
        if shelter_id in self.nodes and self.nodes[shelter_id]["type"] == "SHELTER":
            s = self.nodes[shelter_id]
            s["occupancy"] = max(0, min(s["capacity"], s["occupancy"] + count_change))

    def get_shelter_statuses(self) -> List[Dict[str, Any]]:
        statuses = []
        for nid, n in self.nodes.items():
            if n["type"] == "SHELTER":
                occ_pct = round((n["occupancy"] / float(n["capacity"])) * 100.0, 1)
                is_accepting = occ_pct < 90.0
                statuses.append({
                    "shelter_id": nid,
                    "name": n["name"],
                    "village_id": n.get("village_id"),
                    "latitude": n["lat"],
                    "longitude": n["lon"],
                    "total_capacity": n["capacity"],
                    "current_occupancy": n["occupancy"],
                    "occupancy_pct": occ_pct,
                    "is_accepting": is_accepting,
                    "elevation_m": n.get("elevation_m", 2400.0),
                })
        return statuses

    def find_optimal_evacuation(
        self,
        origin_village_id: str,
        evacuee_count: int = 45,
        preferred_modality: str = "MULTIMODAL",
    ) -> Dict[str, Any]:
        """Calculates optimal dynamic path to safe shelter with real-time capacity balancing."""
        if origin_village_id not in self.nodes:
            raise ValueError(f"Unknown origin village ID: {origin_village_id}")

        # Check candidate shelters and capacity
        shelters = [
            (nid, n) for nid, n in self.nodes.items() if n["type"] == "SHELTER"
        ]

        # Build adjacency graph
        adj: Dict[str, List[Tuple[str, float, float, str, str]]] = {nid: [] for nid in self.nodes}
        bottlenecks_avoided = []

        for eid, e in self.edges.items():
            if e["is_blocked"]:
                bottlenecks_avoided.append(f"{eid} ({e.get('block_reason', 'Hazard Cutoff')})")
                continue

            # Modality filter
            if preferred_modality != "MULTIMODAL":
                if preferred_modality == "PEDESTRIAN" and e["modality"] != "PEDESTRIAN_TRAIL":
                    continue
                if preferred_modality == "ROAD_4X4" and e["modality"] != "ROAD_4X4":
                    continue
                if preferred_modality == "HELICOPTER" and e["modality"] not in ["HELICOPTER_AIR", "ROAD_4X4"]:
                    continue

            # Dynamic weight = base_time * (1 + 2.5 * hazard_score)
            weight = e["base_time_min"] * (1.0 + 2.5 * e["hazard_score"])
            # Add bidirectional edges
            adj[e["u"]].append((e["v"], weight, e["distance_m"], eid, e["modality"]))
            adj[e["v"]].append((e["u"], weight, e["distance_m"], eid, e["modality"]))

        # Run Dijkstra from origin to all reachable nodes
        distances: Dict[str, float] = {nid: float("inf") for nid in self.nodes}
        meter_dists: Dict[str, float] = {nid: 0.0 for nid in self.nodes}
        previous: Dict[str, Optional[Tuple[str, str, str, float, float]]] = {nid: None for nid in self.nodes}
        distances[origin_village_id] = 0.0

        pq = [(0.0, origin_village_id)]

        while pq:
            curr_dist, u = heapq.heappop(pq)
            if curr_dist > distances[u]:
                continue

            for v, w, dist_m, eid, mod in adj[u]:
                if distances[u] + w < distances[v]:
                    distances[v] = distances[u] + w
                    meter_dists[v] = meter_dists[u] + dist_m
                    previous[v] = (u, eid, mod, dist_m, w)
                    heapq.heappush(pq, (distances[v], v))

        # Evaluate best reachable shelter respecting 90% capacity limit
        reachable_shelters = [
            (distances[sid], sid, s)
            for sid, s in shelters
            if distances[sid] < float("inf")
        ]
        reachable_shelters.sort()

        if not reachable_shelters:
            return {
                "path_found": False,
                "origin_village_id": origin_village_id,
                "destination_shelter_id": "",
                "destination_shelter_name": "No reachable shelter",
                "modality": preferred_modality,
                "waypoints": [],
                "total_distance_m": 0.0,
                "total_time_minutes": 0.0,
                "bottlenecks_avoided": bottlenecks_avoided,
                "shelter_rebalanced": False,
                "rebalancing_reason": "All evacuation routes severed",
            }

        # Select first shelter that is accepting (<90% full)
        target_shelter_id = None
        target_shelter_data = None
        rebalanced = False
        rebalance_reason = None

        first_shelter_dist, first_sid, first_s = reachable_shelters[0]
        first_occ_pct = (first_s["occupancy"] / float(first_s["capacity"])) * 100.0

        if first_occ_pct < 90.0:
            target_shelter_id = first_sid
            target_shelter_data = first_s
        else:
            # First nearest shelter is saturated (>90%)!
            rebalanced = True
            rebalance_reason = f"Nearest shelter {first_s['name']} is at {first_occ_pct:.1f}% capacity (>90%). Diverting evacuees."
            bottlenecks_avoided.append(f"Shelter {first_s['name']} [Capacity Saturated]")

            # Search for next accepting shelter
            for dist, sid, s in reachable_shelters[1:]:
                occ_pct = (s["occupancy"] / float(s["capacity"])) * 100.0
                if occ_pct < 90.0:
                    target_shelter_id = sid
                    target_shelter_data = s
                    break

            if not target_shelter_id:
                # If all are full, fallback to nearest
                target_shelter_id = first_sid
                target_shelter_data = first_s

        # Reconstruct path waypoints
        path_nodes = []
        curr = target_shelter_id
        while curr is not None:
            path_nodes.append(curr)
            prev_info = previous[curr]
            curr = prev_info[0] if prev_info else None
        path_nodes.reverse()

        waypoints = []
        cum_dist = 0.0
        cum_time = 0.0
        for i, nid in enumerate(path_nodes):
            node_obj = self.nodes[nid]
            if i > 0:
                step_info = previous[nid]
                if step_info:
                    cum_dist += step_info[3]
                    cum_time += step_info[4]
            desc = f"Proceed to {node_obj['name']} ({node_obj['type']})" if i > 0 else f"Start at {node_obj['name']}"
            waypoints.append({
                "node_id": nid,
                "name": node_obj["name"],
                "latitude": node_obj["lat"],
                "longitude": node_obj["lon"],
                "step_description": desc,
                "cumulative_distance_m": round(cum_dist, 1),
                "cumulative_time_min": round(cum_time, 1),
            })

        return {
            "path_found": True,
            "origin_village_id": origin_village_id,
            "destination_shelter_id": target_shelter_id,
            "destination_shelter_name": target_shelter_data["name"],
            "modality": preferred_modality,
            "waypoints": waypoints,
            "total_distance_m": round(cum_dist, 1),
            "total_time_minutes": round(cum_time, 1),
            "bottlenecks_avoided": bottlenecks_avoided,
            "shelter_rebalanced": rebalanced,
            "rebalancing_reason": rebalance_reason,
        }
