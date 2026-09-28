"""Traditional Rainfall Intensity-Duration (I-D) threshold baseline model."""

from typing import Dict, Any, Union, Optional
import numpy as np
import pandas as pd


class RainfallThresholdBaseline:
    """Empirical Intensity-Duration (I-D) threshold baseline for landslide warning.
    
    Triggers evacuation alarm when short-term intensity (3h) or cumulative antecedent (24h)
    rainfall breaches empirical physical thresholds on steep terrain.
    """

    def __init__(
        self,
        rain_3h_threshold_mm: float = 38.0,
        rain_24h_threshold_mm: float = 85.0,
        slope_threshold_deg: float = 24.0,
    ) -> None:
        """Initialize threshold baseline with empirical Caine/GSI Himalayan parameters."""
        self.rain_3h_thresh = rain_3h_threshold_mm
        self.rain_24h_thresh = rain_24h_threshold_mm
        self.slope_thresh = slope_threshold_deg

    def calibrate(self, X: pd.DataFrame, y: np.ndarray) -> Dict[str, float]:
        """Fit thresholds on training fold to maximize Critical Success Index (CSI)."""
        best_csi = -1.0
        best_params = {
            "rain_3h": self.rain_3h_thresh,
            "rain_24h": self.rain_24h_thresh,
        }

        # Grid search over candidate threshold combinations
        cand_3h = [28.0, 35.0, 42.0, 50.0]
        cand_24h = [65.0, 80.0, 95.0, 115.0]

        r3 = X["rain_3h"].values
        r24 = X["rain_24h"].values
        slope = X["slope"].values

        for t3 in cand_3h:
            for t24 in cand_24h:
                pred = ((r3 >= t3) | ((r24 >= t24) & (slope >= self.slope_thresh))).astype(int)
                tp = int(np.sum((pred == 1) & (y == 1)))
                fp = int(np.sum((pred == 1) & (y == 0)))
                fn = int(np.sum((pred == 0) & (y == 1)))

                denom = tp + fp + fn
                csi = (tp / denom) if denom > 0 else 0.0

                if csi > best_csi:
                    best_csi = csi
                    best_params["rain_3h"] = t3
                    best_params["rain_24h"] = t24

        self.rain_3h_thresh = best_params["rain_3h"]
        self.rain_24h_thresh = best_params["rain_24h"]
        return best_params

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict binary alert (1 = Alarm, 0 = Normal)."""
        r3 = X["rain_3h"].values
        r24 = X["rain_24h"].values
        slope = X["slope"].values

        alarm = (r3 >= self.rain_3h_thresh) | ((r24 >= self.rain_24h_thresh) & (slope >= self.slope_thresh))
        return alarm.astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Compute pseudo-probabilities based on threshold margin excess for AUC/Brier comparison."""
        r3 = X["rain_3h"].values
        r24 = X["rain_24h"].values
        slope = X["slope"].values

        ratio_3h = r3 / max(self.rain_3h_thresh, 1.0)
        ratio_24h = (r24 / max(self.rain_24h_thresh, 1.0)) * (slope >= self.slope_thresh).astype(float)
        max_ratio = np.maximum(ratio_3h, ratio_24h)

        # Logistic transformation centered around 1.0
        probs = 1.0 / (1.0 + np.exp(-4.5 * (max_ratio - 1.0)))
        return np.clip(probs, 0.0001, 0.9999)
