"""Case-based analog matching and explainability generator using vector similarity or DTW."""

from typing import Dict, Any, List, Optional, Union, Tuple
import numpy as np

from ml.analog.library import get_analog_library
from ml.analog.embeddings import HandcraftedEmbedder, PyTorchAutoencoderEmbedder
from ml.analog.index import AnalogIndex


def compute_dtw_distance(s1: np.ndarray, s2: np.ndarray) -> float:
    """Compute Dynamic Time Warping (DTW) distance between two 1D rainfall time series."""
    n = len(s1)
    m = len(s2)
    dtw = np.full((n + 1, m + 1), np.inf, dtype=np.float32)
    dtw[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(s1[i - 1] - s2[j - 1])
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])

    return float(dtw[n, m])


class AnalogMatcher:
    """Case-based retrieval engine finding top-k historical/synthetic storm analogs."""

    def __init__(self, library: Optional[List[Dict[str, Any]]] = None) -> None:
        self.library = library or get_analog_library()
        self.handcrafted_embedder = HandcraftedEmbedder()
        self.autoencoder_embedder = PyTorchAutoencoderEmbedder(latent_dim=16)

        # Pre-train autoencoder on library
        self.autoencoder_embedder.fit(self.library, epochs=35)

        # Build indices for both embedding types
        self.hc_embeddings = np.stack([self.handcrafted_embedder.embed(e) for e in self.library])
        self.ae_embeddings = np.stack([self.autoencoder_embedder.embed(e) for e in self.library])

        self.hc_index = AnalogIndex(dim=16)
        self.hc_index.build(self.hc_embeddings, self.library)

        self.ae_index = AnalogIndex(dim=16)
        self.ae_index.build(self.ae_embeddings, self.library)

    def _generate_reason(self, current: Dict[str, Any], analog: Dict[str, Any]) -> str:
        """Generate human-readable reason explaining why the analog is relevant."""
        r3_cur = float(current.get("rain_3h", 0.0))
        r24_cur = float(current.get("rain_24h", 0.0))
        slope_cur = float(current.get("slope", 30.0))
        fs_cur = float(current.get("factor_of_safety", 1.2))
        m_cur = float(current.get("antecedent_moisture", 0.45))

        slope_a = float(analog.get("slope", 30.0))
        fs_a = float(analog.get("factor_of_safety", 1.2))
        m_a = float(analog.get("antecedent_moisture", 0.45))
        a_landslide = analog.get("outcome", {}).get("landslide", False)

        parts = []
        if r3_cur >= 35.0 or r24_cur >= 80.0:
            parts.append(f"Severe cloudburst rainfall pattern (3h={r3_cur:.1f}mm, 24h={r24_cur:.1f}mm)")
        else:
            parts.append(f"Moderate storm rainfall accumulation (24h={r24_cur:.1f}mm)")

        if slope_cur >= 30.0:
            parts.append(f"steep hillslope terrain ({slope_cur:.1f} deg vs {slope_a:.1f} deg)")

        if fs_cur < 1.0 or fs_a < 1.0:
            parts.append(f"critical limit-equilibrium instability (FS={fs_cur:.2f} vs {fs_a:.2f})")
        elif m_cur > 0.70:
            parts.append(f"elevated antecedent regolith saturation (m={m_cur:.2f} vs {m_a:.2f})")

        reason_str = "; ".join(parts)
        outcome_str = "triggered massive translational failure" if a_landslide else "remained geotechnically stable"
        return f"{reason_str}; analog scenario {outcome_str}."

    def find_analogs(
        self,
        current_state: Dict[str, Any],
        k: int = 3,
        method: str = "embedding",
        embedding_type: str = "autoencoder",
    ) -> List[Dict[str, Any]]:
        """Find top-k analog events matching current village weather and terrain conditions.
        
        Args:
            current_state: dict containing rainfall series or peaks, slope, moisture, FS, etc.
            k: number of analogs to return (default: 3).
            method: 'embedding' or 'dtw'.
            embedding_type: 'autoencoder' or 'handcrafted'.
        """
        k = max(1, min(k, len(self.library)))

        if method.lower() == "dtw":
            # DTW-based hyetograph matching
            cur_series = current_state.get("approx_rainfall_72h_series") or current_state.get("rainfall_72h")
            if cur_series is None:
                # Synthesize 72h series from available rolling metrics
                r24 = float(current_state.get("rain_24h", 30.0))
                r3 = float(current_state.get("rain_3h", 10.0))
                r72 = float(current_state.get("rain_72h", r24 * 1.5))
                cur_series = [r72 / 72.0] * 48 + [r24 / 24.0] * 21 + [r3 / 3.0] * 3

            cur_arr = np.array(cur_series[-72:], dtype=np.float32)
            cur_slope = float(current_state.get("slope", 30.0))
            cur_m = float(current_state.get("antecedent_moisture", 0.45))
            cur_fs = float(current_state.get("factor_of_safety", 1.2))

            dtw_scores = []
            for event in self.library:
                ev_series = np.array(event.get("approx_rainfall_72h_series", [0.0] * 72), dtype=np.float32)
                dtw_dist = compute_dtw_distance(cur_arr, ev_series)

                # Composite distance factoring in terrain & FS
                ev_slope = float(event.get("slope", 30.0))
                ev_m = float(event.get("antecedent_moisture", 0.45))
                ev_fs = float(event.get("factor_of_safety", 1.2))

                geo_dist = abs(cur_slope - ev_slope) / 20.0 + abs(cur_m - ev_m) + abs(cur_fs - ev_fs)
                comp_dist = (dtw_dist / 60.0) + geo_dist

                # Map distance to similarity [0%, 100%]
                sim_pct = round(float(np.clip(100.0 * np.exp(-comp_dist / 4.0), 0.0, 100.0)), 1)
                dtw_scores.append((sim_pct, event))

            dtw_scores.sort(key=lambda x: x[0], reverse=True)
            top_matches = dtw_scores[:k]

        else:
            # Vector embedding search (FAISS / Scikit-Learn)
            if embedding_type.lower() == "handcrafted":
                query_vec = self.handcrafted_embedder.embed(current_state)
                index_matches = self.hc_index.search(query_vec, k=k)
            else:
                query_vec = self.autoencoder_embedder.embed(current_state)
                index_matches = self.ae_index.search(query_vec, k=k)

            top_matches = [(round(float(sim * 100.0), 1), ev) for sim, ev in index_matches]

        # Format output
        results = []
        for sim_pct, event in top_matches:
            reason = self._generate_reason(current_state, event)
            results.append({
                "event_id": event.get("event_id"),
                "name": event.get("name"),
                "similarity_pct": sim_pct,
                "date": event.get("date"),
                "location": event.get("location"),
                "provenance": event.get("provenance"),
                "outcome": event.get("outcome", {}),
                "reason": reason,
                "synopsis": event.get("synopsis", ""),
            })

        return results

    def extract_key_drivers(self, current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify physical factors driving hazard risk for current state."""
        r3 = float(current_state.get("rain_3h", 0.0))
        r24 = float(current_state.get("rain_24h", 0.0))
        slope = float(current_state.get("slope", 30.0))
        fs = float(current_state.get("factor_of_safety", 1.2))
        m = float(current_state.get("antecedent_moisture", 0.45))
        dist_stream = float(current_state.get("distance_to_stream", 60.0))

        drivers = []
        # 1. Slope Stability / FS
        if fs < 1.0:
            drivers.append({
                "factor": "Geotechnical Factor of Safety",
                "value": f"{fs:.2f}",
                "status": "CRITICAL",
                "description": "Limit-equilibrium shear resisting force breached by driving gravitational shear stresses (FS < 1.0).",
            })
        elif fs < 1.25:
            drivers.append({
                "factor": "Geotechnical Factor of Safety",
                "value": f"{fs:.2f}",
                "status": "ELEVATED",
                "description": "Marginal stability regime (1.0 <= FS < 1.25); highly vulnerable to pore-pressure surge.",
            })

        # 2. Short-term burst rainfall
        if r3 >= 38.0:
            drivers.append({
                "factor": "3-Hour Storm Intensity",
                "value": f"{r3:.1f} mm",
                "status": "CRITICAL",
                "description": "Exceeds regional cloudburst threshold (>= 38 mm in 3 hours).",
            })
        elif r3 >= 20.0:
            drivers.append({
                "factor": "3-Hour Storm Intensity",
                "value": f"{r3:.1f} mm",
                "status": "ELEVATED",
                "description": "Intense short-duration convective downpour.",
            })

        # 3. Antecedent moisture
        if m >= 0.80:
            drivers.append({
                "factor": "Antecedent Soil Moisture",
                "value": f"{m * 100:.1f}% saturation",
                "status": "CRITICAL",
                "description": "Near-saturated regolith drastically reducing effective normal stress and soil suction.",
            })
        elif m >= 0.60:
            drivers.append({
                "factor": "Antecedent Soil Moisture",
                "value": f"{m * 100:.1f}% saturation",
                "status": "ELEVATED",
                "description": "Elevated pre-existing saturation leaving minimal storage deficit.",
            })

        # 4. Slope gradient
        if slope >= 34.0:
            drivers.append({
                "factor": "Hillslope Gradient",
                "value": f"{slope:.1f} deg",
                "status": "HIGH_SUSCEPTIBILITY",
                "description": "Steep mountain slope exceeding internal soil friction angle.",
            })

        # 5. Stream proximity
        if dist_stream <= 30.0:
            drivers.append({
                "factor": "Distance to Stream Channel",
                "value": f"{dist_stream:.1f} m",
                "status": "TOE_EROSION_RISK",
                "description": "Close proximity to active drainage channel with fluvial toe scour potential.",
            })

        return drivers

    def build_explanation_json(
        self,
        current_state: Dict[str, Any],
        k: int = 3,
        method: str = "embedding",
        embedding_type: str = "autoencoder",
    ) -> Dict[str, Any]:
        """Produce comprehensive case-based explainability JSON object."""
        analogs = self.find_analogs(current_state, k=k, method=method, embedding_type=embedding_type)
        key_drivers = self.extract_key_drivers(current_state)

        # Average historical failure rate among retrieved analogs
        analog_landslide_count = sum(1 for a in analogs if a.get("outcome", {}).get("landslide", False))
        analog_failure_rate = round(float(analog_landslide_count / max(len(analogs), 1)), 4)

        return {
            "top_analogs": analogs,
            "key_drivers": key_drivers,
            "analog_landslide_rate": analog_failure_rate,
            "matching_method": method,
            "embedding_type": embedding_type if method == "embedding" else None,
        }


# Singleton instance
_global_analog_matcher: Optional[AnalogMatcher] = None


def get_analog_matcher() -> AnalogMatcher:
    """Retrieve or initialize singleton AnalogMatcher instance."""
    global _global_analog_matcher
    if _global_analog_matcher is None:
        _global_analog_matcher = AnalogMatcher()
    return _global_analog_matcher


def find_analogs(
    current_state: Dict[str, Any],
    k: int = 3,
    method: str = "embedding",
    embedding_type: str = "autoencoder",
) -> List[Dict[str, Any]]:
    """Functional interface finding top-k analog disaster/synthetic events."""
    matcher = get_analog_matcher()
    return matcher.find_analogs(current_state, k=k, method=method, embedding_type=embedding_type)
