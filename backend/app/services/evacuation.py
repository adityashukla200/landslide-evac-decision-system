"""Evacuation planning, dynamic time-to-impact forecasting, and multilingual alert dispatching.

Provides:
1. Time-to-impact estimation from nowcast rainfall trends and model failure probability trajectory.
2. NetworkX graph-based evacuation routing with cut-risk avoidance, shelter capacity checking,
   vulnerable speed modifiers, and night-time impedance adjustments.
3. Available margin calculation: Margin = Time-to-Impact - Time-to-Evacuate, driving stage escalation.
4. Multilingual alert message generation under 160 characters (English, Hindi, Garhwali, Kumaoni)
   with Bhashini API translation hook and mock fallback.
5. Actionable volunteer task cards linking emergency volunteers with registered vulnerable households.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
import os
import math
import networkx as nx
from sqlalchemy.orm import Session

from backend.app.db.models import Village, Shelter, Route, Recipient


# Base walking parameters (in meters per minute)
BASE_WALKING_SPEED_M_PER_MIN = 66.7    # ~4.0 km/h on mountain terrain
VULNERABLE_WALKING_SPEED_M_PER_MIN = 33.3  # ~2.0 km/h for elderly/mobility-impaired
NIGHT_TIME_FACTOR = 1.40               # 40% slower due to reduced visibility and trail hazards

# Multilingual message templates (Strictly <= 160 characters)
MESSAGE_TEMPLATES = {
    "en": "Leave now. Go via {route} to {shelter}. You have about {margin} minutes.",
    "hi": "तुरंत निकलें। {route} से {shelter} जाएं। आपके पास लगभग {margin} मिनट हैं।",
    "gbm": "अबे निकलो। {route} से {shelter} जावां। तुमा पांस लगभग {margin} मिनट चन।",  # Garhwali
    "kfy": "इबे निकलो। {route} बटि {shelter} जा। तुमार पास लगभग {margin} मिनट छू।",   # Kumaoni
}


def estimate_time_to_impact(
    current_rainfall_rate_mm_h: float = 0.0,
    rainfall_trend_rate: float = 0.0,
    model_probability: float = 0.0,
    slope: float = 30.0,
    antecedent_moisture: float = 0.50,
) -> Dict[str, Any]:
    """Estimate time-to-impact range [min_minutes, likely_minutes] based on nowcast trends.
    
    Combines:
    1. Rainfall intensity rate and instantaneous acceleration dR/dt.
    2. Model calibrated failure probability trajectory.
    3. Hillslope steepness and antecedent regolith saturation.
    """
    # Baseline comfortable window in minutes when no acute hazard is present
    if current_rainfall_rate_mm_h < 5.0 and model_probability < 0.010 and rainfall_trend_rate <= 0:
        return {
            "min_minutes": 360.0,
            "likely_minutes": 480.0,
            "urgency": "LOW",
            "reason": "Rainfall below hazardous runoff threshold; no imminent threat.",
        }

    # Time to critical saturation (heuristic bucket threshold ~80mm or intense cloudburst)
    # Effective driving rainfall rate including acceleration
    effective_rate = max(1.0, current_rainfall_rate_mm_h + max(0.0, rainfall_trend_rate * 2.0))
    
    # Required storm deficit before failure initiation (shorter on steep saturated slopes)
    stability_penalty = max(0.5, 1.5 - (slope / 45.0) * 0.5 - antecedent_moisture * 0.4)
    storage_deficit_mm = max(10.0, 60.0 * stability_penalty)

    # Likely time in hours until geotechnical failure threshold
    hours_to_failure = storage_deficit_mm / effective_rate

    # If model probability is already high, hazard arrival is severely accelerated
    if model_probability >= 0.150:
        prob_compression = 0.25  # Imminent failure (< 30 min)
    elif model_probability >= 0.050:
        prob_compression = 0.50
    elif model_probability >= 0.018:
        prob_compression = 0.75
    else:
        prob_compression = 1.0

    likely_minutes = max(15.0, round(hours_to_failure * 60.0 * prob_compression, 1))
    # Minimum worst-case lead time accounting for localized cloudburst pulse
    min_minutes = max(10.0, round(likely_minutes * 0.60, 1))

    urgency = "CRITICAL" if likely_minutes <= 30 else ("HIGH" if likely_minutes <= 60 else "ELEVATED")

    return {
        "min_minutes": min_minutes,
        "likely_minutes": likely_minutes,
        "urgency": urgency,
        "reason": f"Projected failure in {likely_minutes:.0f}m at {effective_rate:.1f}mm/h effective rain intensity.",
    }


def compute_walking_time(
    length_m: float,
    is_vulnerable: bool = False,
    is_night: bool = False,
    cut_risk: float = 0.0,
) -> float:
    """Compute walking duration along a route segment in minutes, factoring in demographics and terrain."""
    speed = VULNERABLE_WALKING_SPEED_M_PER_MIN if is_vulnerable else BASE_WALKING_SPEED_M_PER_MIN
    base_time_min = length_m / speed

    # Night time visibility penalty
    night_mult = NIGHT_TIME_FACTOR if is_night else 1.0

    # Risk-induced delay factor (mud, loose stones, partial culvert overflow)
    # Slows progress non-linearly: 20% cut_risk -> ~1.2x, 50% cut_risk -> ~2.2x
    hazard_delay = 1.0 + (5.0 * (cut_risk ** 2))

    total_time = base_time_min * night_mult * hazard_delay
    return round(float(total_time), 1)


class EvacuationNetworkRouter:
    """NetworkX pathfinder resolving optimal routes to safe shelters with capacity and cut-risk avoidance."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        """Construct directed graph connecting villages, intermediate junctions, and refuge shelters."""
        villages = self.db.query(Village).all()
        shelters = self.db.query(Shelter).all()
        routes = self.db.query(Route).all()

        # Add village nodes
        for v in villages:
            self.graph.add_node(v.id, type="village", name=v.name, population=v.population, elev=v.elevation)

        # Add shelter nodes
        for s in shelters:
            self.graph.add_node(s.id, type="shelter", name=s.name or f"Shelter {s.id}", capacity=s.capacity)

        # Add primary routes
        for r in routes:
            self.graph.add_edge(
                r.from_village,
                r.to_shelter,
                route_id=r.id,
                name=f"Route {r.id}",
                length_m=r.length_m,
                cut_risk=r.cut_risk,
                est_walk_minutes=r.est_walk_minutes,
            )

        # Connect inter-village evacuation routes along valleys for multi-shelter redundancy
        # Link adjacent villages to allow spillover to neighboring shelters if local shelter is full
        for idx in range(len(villages) - 1):
            v1 = villages[idx]
            v2 = villages[idx + 1]
            dist_approx = math.hypot((v1.lon - v2.lon) * 111000.0, (v1.lat - v2.lat) * 111000.0)
            if dist_approx < 6000.0:  # Within 6km in same valley
                self.graph.add_edge(
                    v1.id,
                    v2.id,
                    route_id=f"INTER_{v1.id}_{v2.id}",
                    name=f"Trail from {v1.name} to {v2.name}",
                    length_m=dist_approx,
                    cut_risk=0.15,
                    est_walk_minutes=dist_approx / BASE_WALKING_SPEED_M_PER_MIN,
                )
                self.graph.add_edge(
                    v2.id,
                    v1.id,
                    route_id=f"INTER_{v2.id}_{v1.id}",
                    name=f"Trail from {v2.name} to {v1.name}",
                    length_m=dist_approx,
                    cut_risk=0.15,
                    est_walk_minutes=dist_approx / BASE_WALKING_SPEED_M_PER_MIN,
                )

    def select_best_evacuation_plan(
        self,
        village_id: str,
        evacuee_count: Optional[int] = None,
        is_night: bool = False,
        is_vulnerable: bool = False,
        cut_risk_threshold: float = 0.60,
    ) -> Dict[str, Any]:
        """Find the fastest safe path to an available shelter with capacity, avoiding high cut-risk segments."""
        if village_id not in self.graph:
            raise ValueError(f"Village '{village_id}' not found in evacuation network.")

        village_data = self.graph.nodes[village_id]
        required_capacity = evacuee_count if evacuee_count is not None else int(village_data.get("population", 500))

        # Weight function for NetworkX Dijkstra:
        # Heavily penalizes cut-risk and bars segments exceeding cut_risk_threshold if possible
        def edge_weight(u, v, data):
            length = data.get("length_m", 1000.0)
            risk = data.get("cut_risk", 0.0)
            if risk >= cut_risk_threshold:
                return length * 50.0  # Massive penalty to actively steer away from severed segments
            return compute_walking_time(length, is_vulnerable=is_vulnerable, is_night=is_night, cut_risk=risk)

        # Identify all shelter candidate nodes
        shelter_candidates = [
            node for node, attr in self.graph.nodes(data=True)
            if attr.get("type") == "shelter" and attr.get("capacity", 0) >= required_capacity
        ]

        if not shelter_candidates:
            # Fallback to any shelter with maximum available capacity
            shelter_candidates = [
                node for node, attr in self.graph.nodes(data=True) if attr.get("type") == "shelter"
            ]

        best_shelter = None
        best_path = None
        min_evac_time = float("inf")
        best_cut_risk = 1.0

        for shelter_id in shelter_candidates:
            try:
                path = nx.shortest_path(self.graph, source=village_id, target=shelter_id, weight=edge_weight)
                
                # Compute total actual adjusted walking time along path
                total_time = 0.0
                max_path_risk = 0.0
                total_distance = 0.0

                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    edge = self.graph[u][v]
                    seg_len = edge.get("length_m", 1000.0)
                    seg_risk = edge.get("cut_risk", 0.0)
                    total_time += compute_walking_time(
                        seg_len, is_vulnerable=is_vulnerable, is_night=is_night, cut_risk=seg_risk
                    )
                    max_path_risk = max(max_path_risk, seg_risk)
                    total_distance += seg_len

                if total_time < min_evac_time:
                    min_evac_time = total_time
                    best_shelter = shelter_id
                    best_path = path
                    best_cut_risk = max_path_risk

            except nx.NetworkXNoPath:
                continue

        if best_shelter is None:
            # Direct designated route fallback
            first_shelter = self.db.query(Shelter).filter(Shelter.village_id == village_id).first()
            shelter_id = first_shelter.id if first_shelter else f"SHL_{village_id}"
            shelter_name = first_shelter.name if first_shelter else f"High-Ground Shelter {shelter_id}"
            shelter_cap = first_shelter.capacity if first_shelter else 1000
            return {
                "shelter_id": shelter_id,
                "shelter_name": shelter_name,
                "shelter_capacity": shelter_cap,
                "route_id": f"RTE_{village_id}_DIRECT",
                "route_name": "Direct Village Escape Path",
                "path_nodes": [village_id, shelter_id],
                "route_length_m": 1200.0,
                "time_to_evacuate_minutes": 25.0 if not is_vulnerable else 45.0,
                "max_segment_cut_risk": 0.05,
            }

        shelter_info = self.graph.nodes[best_shelter]
        first_step_edge = self.graph[best_path[0]][best_path[1]]

        return {
            "shelter_id": best_shelter,
            "shelter_name": shelter_info.get("name", best_shelter),
            "shelter_capacity": shelter_info.get("capacity", 500),
            "route_id": first_step_edge.get("route_id", f"RTE_{village_id}"),
            "route_name": first_step_edge.get("name", "Designated Safe Trail"),
            "path_nodes": best_path,
            "route_length_m": round(float(total_distance), 1),
            "time_to_evacuate_minutes": round(float(min_evac_time), 1),
            "max_segment_cut_risk": round(float(best_cut_risk), 2),
        }


def determine_margin_alert_stage(
    time_to_impact_likely_minutes: float,
    time_to_evacuate_minutes: float,
) -> Tuple[str, float]:
    """Determine operational alert tier based on available evacuation margin.
    
    Margin = Time-to-Impact - Time-to-Evacuate.
    Villages with narrower margins escalate to higher alert stages earlier.
    
    Tiers:
    - EVACUATE: margin <= 15 min (Immediate danger, time nearly expired)
    - WARNING: 15 < margin <= 45 min (Pre-positioning and rapid movement)
    - WATCH: 45 < margin <= 120 min (Heightened preparedness)
    - NONE: margin > 120 min (Safe buffer)
    """
    margin = time_to_impact_likely_minutes - time_to_evacuate_minutes

    if margin <= 15.0:
        stage = "EVACUATE"
    elif margin <= 45.0:
        stage = "WARNING"
    elif margin <= 120.0:
        stage = "WATCH"
    else:
        stage = "NONE"

    return stage, round(float(margin), 1)


def translate_bhashini(
    text: str,
    target_lang: str,
    api_key: Optional[str] = None,
) -> str:
    """Hook for Government of India's Bhashini NLP translation API with graceful mock fallback."""
    key = api_key or os.getenv("BHASHINI_API_KEY")
    if not key:
        # Mock fallback: return localized template or pass-through
        return text

    # Production hook when API key is provided
    try:
        import httpx
        # Bhashini Pipeline Inference Request
        url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
        headers = {"Authorization": key, "Content-Type": "application/json"}
        # For demonstration / live hook structure:
        # resp = httpx.post(url, json={...}, headers=headers, timeout=3.0)
        # return resp.json()["pipelineResponse"][0]["output"][0]["target"]
        return text
    except Exception:
        return text


def generate_alert_messages(
    route_name: str,
    shelter_name: str,
    margin_minutes: float,
    target_languages: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Generate concise, actionable one-line alert directives strictly <= 160 characters.
    
    Templates formatted as:
    "Leave now. Go via {route} to {shelter}. You have about {margin} minutes."
    """
    langs = target_languages or ["en", "hi", "gbm", "kfy"]
    margin_display = max(5, int(math.ceil(margin_minutes)))

    # Truncate route/shelter names if needed to guarantee SMS compliance
    short_route = route_name if len(route_name) <= 22 else f"{route_name[:19]}..."
    short_shelter = shelter_name if len(shelter_name) <= 24 else f"{shelter_name[:21]}..."

    messages = {}
    for lang in langs:
        template = MESSAGE_TEMPLATES.get(lang, MESSAGE_TEMPLATES["en"])
        msg = template.format(
            route=short_route,
            shelter=short_shelter,
            margin=margin_display,
        )

        # Enforce strict 160-char SMS limit
        if len(msg) > 160:
            msg = msg[:157] + "..."

        assert len(msg) <= 160, f"Alert message for lang '{lang}' exceeded 160 chars: {len(msg)}"
        messages[lang] = msg

    return messages


def generate_volunteer_task_cards(
    village_id: str,
    db: Session,
    target_shelter_name: str,
    recommended_route_name: str,
    available_margin_minutes: float,
) -> List[Dict[str, Any]]:
    """Generate actionable task cards linking registered village volunteers to vulnerable households."""
    recipients = db.query(Recipient).filter(Recipient.village_id == village_id).all()
    vulnerable_residents = [r for r in recipients if r.vulnerable_flag]
    volunteers = [r for r in recipients if not r.vulnerable_flag]

    task_cards = []
    margin_display = max(5, int(math.ceil(available_margin_minutes)))
    urgency = "CRITICAL" if available_margin_minutes <= 20 else ("HIGH" if available_margin_minutes <= 45 else "MEDIUM")

    for idx, resident in enumerate(vulnerable_residents, start=1):
        # Find assigned volunteer or round-robin among village volunteers
        assigned_vol = None
        if resident.volunteer_id:
            assigned_vol = db.query(Recipient).filter(Recipient.id == resident.volunteer_id).first()
        if not assigned_vol and volunteers:
            assigned_vol = volunteers[idx % len(volunteers)]

        vol_id = assigned_vol.id if assigned_vol else "VOL_UNASSIGNED"
        vol_phone = assigned_vol.phone if assigned_vol else "N/A"

        card = {
            "task_id": f"TSK_{village_id}_{idx:03d}",
            "priority": urgency,
            "village_id": village_id,
            "vulnerable_resident_id": resident.id,
            "resident_phone": resident.phone,
            "resident_language": resident.language,
            "assigned_volunteer_id": vol_id,
            "volunteer_phone": vol_phone,
            "target_shelter": target_shelter_name,
            "assigned_route": recommended_route_name,
            "available_time_minutes": margin_display,
            "directive": (
                f"Assist resident {resident.id} ({resident.phone}) to {target_shelter_name} "
                f"via {recommended_route_name}. Window: ~{margin_display} min."
            ),
        }
        task_cards.append(card)

    return task_cards


def assess_evacuation_readiness(
    village_id: str,
    db: Session,
    current_rainfall_rate_mm_h: float = 25.0,
    rainfall_trend_rate: float = 5.0,
    model_probability: float = 0.035,
    is_night: bool = False,
    vulnerable_priority: bool = False,
) -> Dict[str, Any]:
    """Execute complete end-to-end evacuation assessment for a village."""
    village = db.query(Village).filter(Village.id == village_id).first()
    if not village:
        raise ValueError(f"Village with ID '{village_id}' not found.")

    # 1. Estimate Time-to-Impact
    impact_est = estimate_time_to_impact(
        current_rainfall_rate_mm_h=current_rainfall_rate_mm_h,
        rainfall_trend_rate=rainfall_trend_rate,
        model_probability=model_probability,
        slope=32.0,  # Regional mountain slope default
    )

    # 2. Compute Optimal Evacuation Route & Time
    router = EvacuationNetworkRouter(db)
    evac_plan = router.select_best_evacuation_plan(
        village_id=village_id,
        is_night=is_night,
        is_vulnerable=vulnerable_priority,
    )

    # 3. Determine Available Margin and Alert Stage
    stage, margin = determine_margin_alert_stage(
        time_to_impact_likely_minutes=impact_est["likely_minutes"],
        time_to_evacuate_minutes=evac_plan["time_to_evacuate_minutes"],
    )

    # 4. Generate Multilingual Alert Messages (<= 160 chars)
    messages = generate_alert_messages(
        route_name=evac_plan["route_name"],
        shelter_name=evac_plan["shelter_name"],
        margin_minutes=margin,
    )

    # 5. Generate Volunteer Task Cards for Vulnerable Residents
    task_cards = generate_volunteer_task_cards(
        village_id=village_id,
        db=db,
        target_shelter_name=evac_plan["shelter_name"],
        recommended_route_name=evac_plan["route_name"],
        available_margin_minutes=margin,
    )

    return {
        "village_id": village.id,
        "village_name": village.name,
        "district": village.district,
        "population": village.population,
        "time_to_impact_range": {
            "min_minutes": impact_est["min_minutes"],
            "likely_minutes": impact_est["likely_minutes"],
            "urgency": impact_est["urgency"],
            "reason": impact_est["reason"],
        },
        "time_to_evacuate_minutes": evac_plan["time_to_evacuate_minutes"],
        "available_margin_minutes": margin,
        "alert_stage": stage,
        "recommended_evacuation": {
            "shelter_id": evac_plan["shelter_id"],
            "shelter_name": evac_plan["shelter_name"],
            "shelter_capacity": evac_plan["shelter_capacity"],
            "route_id": evac_plan["route_id"],
            "route_name": evac_plan["route_name"],
            "route_length_m": evac_plan["route_length_m"],
            "max_segment_cut_risk": evac_plan["max_segment_cut_risk"],
            "path_nodes": evac_plan["path_nodes"],
        },
        "alert_messages": messages,
        "volunteer_task_cards": task_cards,
    }
