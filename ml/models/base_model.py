"""Base XGBoost landslide risk prediction model with physics pretraining, fine-tuning, and probability calibration."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Union, List, Optional, Tuple
import numpy as np
import pandas as pd
import xgboost as xgb
from joblib import dump, load
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from ml.physics.slope_stability import compute_infinite_slope_fs

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_PATH = ROOT_DIR / "ml" / "models" / "saved" / "landslide_xgboost.joblib"

MODEL_FEATURES = [
    "rain_1h",
    "rain_3h",
    "rain_6h",
    "rain_24h",
    "rain_72h",
    "antecedent_moisture",
    "elevation",
    "slope",
    "aspect",
    "curvature",
    "upstream_catchment_area",
    "distance_to_stream",
    "ndvi",
    "factor_of_safety",
]


class PlattCalibrator:
    """Platt scaling (logistic regression on log-odds) probability calibrator."""

    def __init__(self, c: float = 1.0) -> None:
        self.lr = LogisticRegression(solver="lbfgs", C=c, max_iter=1000)
        self.is_fitted = False

    def fit(self, raw_probs: np.ndarray, y: np.ndarray) -> "PlattCalibrator":
        eps = 1e-7
        p_clipped = np.clip(raw_probs, eps, 1.0 - eps)
        logits = np.log(p_clipped / (1.0 - p_clipped)).reshape(-1, 1)
        if len(np.unique(y)) < 2:
            self.constant_prob = float(np.mean(y))
            self.is_fitted = True
            return self
        self.lr.fit(logits, y)
        self.is_fitted = True
        return self

    def predict_proba(self, raw_probs: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("PlattCalibrator must be fitted before predict_proba.")
        if hasattr(self, "constant_prob"):
            return np.full_like(raw_probs, fill_value=self.constant_prob, dtype=float)
        eps = 1e-7
        p_clipped = np.clip(raw_probs, eps, 1.0 - eps)
        logits = np.log(p_clipped / (1.0 - p_clipped)).reshape(-1, 1)
        return self.lr.predict_proba(logits)[:, 1]


class IsotonicCalibrator:
    """Non-parametric isotonic regression probability calibrator."""

    def __init__(self) -> None:
        self.iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        self.is_fitted = False

    def fit(self, raw_probs: np.ndarray, y: np.ndarray) -> "IsotonicCalibrator":
        self.iso.fit(raw_probs, y)
        self.is_fitted = True
        return self

    def predict_proba(self, raw_probs: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("IsotonicCalibrator must be fitted before predict_proba.")
        return np.clip(self.iso.predict(raw_probs), 0.0, 1.0)


class LandslideRiskModel:
    """XGBoost landslide failure prediction model supporting physics pretraining, fine-tuning, and probability calibration."""

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 5,
        learning_rate: float = 0.06,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        random_state: int = 42,
    ) -> None:
        """Initialize XGBoost classifier with hyperparameters configured for imbalanced tabular data."""
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state

        self.model: Optional[xgb.XGBClassifier] = None
        self.is_pretrained: bool = False
        self.is_fitted: bool = False
        self.features: List[str] = MODEL_FEATURES

        # Post-hoc probability calibrator
        self.calibrator: Optional[Union[IsotonicCalibrator, PlattCalibrator]] = None
        self.calibration_method: Optional[str] = None
        self.calibration_metrics: Dict[str, float] = {}

    def _ensure_physics_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure factor_of_safety and required feature columns exist in DataFrame."""
        df = df.copy()
        if "factor_of_safety" not in df.columns:
            elev = df["elevation"].values if "elevation" in df.columns else np.full(len(df), 1500.0)
            slope = df["slope"].values if "slope" in df.columns else np.full(len(df), 30.0)
            sat = df["antecedent_moisture"].values if "antecedent_moisture" in df.columns else np.full(len(df), 0.4)

            cohesion = np.where(elev < 1800, 8.0, 5.5)
            soil_depth = np.where(elev < 1800, 2.0, 1.8)

            df["factor_of_safety"] = compute_infinite_slope_fs(
                slope_deg=slope,
                cohesion_kpa=cohesion,
                friction_angle_deg=31.0,
                soil_depth_m=soil_depth,
                saturation_ratio=sat,
            )
        return df

    def pretrain_on_physics(self, physics_df: pd.DataFrame) -> None:
        """Pretrain model on synthetic geotechnical scenarios."""
        print(f"[*] Pretraining XGBoost on {len(physics_df):,} geotechnical physics scenarios...")
        X_pre = pd.DataFrame({
            "slope": physics_df["slope_deg"],
            "antecedent_moisture": physics_df["antecedent_moisture"],
            "factor_of_safety": physics_df["fs_noisy"],
            "rain_3h": physics_df["rainfall_mm"] * 0.45,
            "rain_24h": physics_df["rainfall_mm"],
            "rain_1h": physics_df["rainfall_mm"] * 0.20,
            "rain_6h": physics_df["rainfall_mm"] * 0.60,
            "rain_72h": physics_df["rainfall_mm"] * 1.10,
            "elevation": 1600.0,
            "aspect": 180.0,
            "curvature": 0.0,
            "upstream_catchment_area": 35.0,
            "distance_to_stream": 80.0,
            "ndvi": 0.55,
        })
        y_pre = physics_df["failed"].values

        n_pos = np.sum(y_pre == 1)
        n_neg = np.sum(y_pre == 0)
        scale_pos = float(n_neg / max(n_pos, 1))

        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators // 2,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            scale_pos_weight=scale_pos,
            random_state=self.random_state,
            n_jobs=4,
            eval_metric="logloss",
        )
        self.model.fit(X_pre[self.features], y_pre)
        self.is_pretrained = True
        print("[+] Completed physics pretraining.")

    def fine_tune(
        self,
        train_df: pd.DataFrame,
        calib_df: Optional[pd.DataFrame] = None,
        scale_pos_weight: Optional[float] = None,
    ) -> None:
        """Fine-tune / train model on village spatio-temporal feature table with optional post-hoc calibration."""
        df = self._ensure_physics_features(train_df)
        X = df[self.features]
        y = df["landslide_within_6h"].values

        n_pos = int(np.sum(y == 1))
        n_neg = int(np.sum(y == 0))

        if scale_pos_weight is None:
            raw_ratio = n_neg / max(n_pos, 1)
            weight = float(np.clip(np.sqrt(raw_ratio) * 2.0, 5.0, 150.0))
        else:
            weight = scale_pos_weight

        print(f"[*] Fine-tuning XGBoost on {len(df):,} village records (Pos: {n_pos:,}, Neg: {n_neg:,}, Weight: {weight:.1f})...")

        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            scale_pos_weight=weight,
            random_state=self.random_state,
            n_jobs=4,
            eval_metric="logloss",
        )

        self.model.fit(X, y)
        self.is_fitted = True
        print("[+] Model fine-tuning complete.")

        # If calibration split provided, calibrate probabilities
        if calib_df is not None:
            self.calibrate(calib_df)

    def calibrate(self, calib_df: pd.DataFrame) -> Dict[str, Any]:
        """Fit post-hoc probability calibrator (Isotonic vs Platt) and pick best validation Brier score."""
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be fitted before calibrating.")

        calib_df = self._ensure_physics_features(calib_df)
        y_calib = calib_df["landslide_within_6h"].values
        raw_probs = self.predict_raw_proba(calib_df)

        brier_uncal = float(brier_score_loss(y_calib, raw_probs))

        # 1. Isotonic Regression
        iso_cal = IsotonicCalibrator().fit(raw_probs, y_calib)
        p_iso = iso_cal.predict_proba(raw_probs)
        brier_iso = float(brier_score_loss(y_calib, p_iso))

        # 2. Platt Scaling
        platt_cal = PlattCalibrator().fit(raw_probs, y_calib)
        p_platt = platt_cal.predict_proba(raw_probs)
        brier_platt = float(brier_score_loss(y_calib, p_platt))

        print(f"[*] Probability Calibration on {len(calib_df):,} validation records:")
        print(f"    - Uncalibrated Brier: {brier_uncal:.6f}")
        print(f"    - Isotonic Brier:     {brier_iso:.6f}")
        print(f"    - Platt Brier:        {brier_platt:.6f}")

        if brier_iso <= brier_platt:
            self.calibrator = iso_cal
            self.calibration_method = "isotonic"
            chosen_brier = brier_iso
            print("[+] Selected Isotonic Regression calibrator (lower validation Brier score).")
        else:
            self.calibrator = platt_cal
            self.calibration_method = "platt"
            chosen_brier = brier_platt
            print("[+] Selected Platt Scaling calibrator (lower validation Brier score).")

        self.calibration_metrics = {
            "method": self.calibration_method,
            "brier_uncalibrated": brier_uncal,
            "brier_isotonic": brier_iso,
            "brier_platt": brier_platt,
            "brier_chosen": chosen_brier,
        }
        return self.calibration_metrics

    def predict_raw_proba(self, X: Union[pd.DataFrame, Dict[str, Any]]) -> np.ndarray:
        """Compute uncalibrated raw model probabilities from XGBoost."""
        if not self.is_fitted and self.model is None:
            raise RuntimeError("Model must be fitted or pretrained before calling predict_raw_proba.")

        if isinstance(X, dict):
            df = pd.DataFrame([X])
        else:
            df = X.copy()

        df = self._ensure_physics_features(df)
        for feat in self.features:
            if feat not in df.columns:
                df[feat] = 0.0

        features_df = df[self.features]
        return self.model.predict_proba(features_df)[:, 1]

    def predict_proba(self, X: Union[pd.DataFrame, Dict[str, Any]]) -> np.ndarray:
        """Predict probability [0.0, 1.0] for input features, applying post-hoc calibration if available."""
        raw_probs = self.predict_raw_proba(X)
        if self.calibrator is not None:
            return self.calibrator.predict_proba(raw_probs)
        return raw_probs

    def predict(self, features: Union[Dict[str, Any], pd.DataFrame]) -> Union[float, np.ndarray]:
        """Predict calibrated probability for single dictionary or array of features."""
        probs = self.predict_proba(features)
        if isinstance(features, dict) or (isinstance(features, pd.DataFrame) and len(features) == 1):
            return float(probs[0])
        return probs

    def save(self, path: Path = DEFAULT_MODEL_PATH) -> Path:
        """Persist model and calibrator artifact to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        dump({
            "model": self.model,
            "calibrator": self.calibrator,
            "calibration_method": self.calibration_method,
            "calibration_metrics": self.calibration_metrics,
            "features": self.features,
            "is_fitted": self.is_fitted,
            "is_pretrained": self.is_pretrained,
        }, path)
        print(f"[+] Saved LandslideRiskModel to {path}")
        return path

    def load(self, path: Path = DEFAULT_MODEL_PATH) -> None:
        """Load model and calibrator artifact from disk."""
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")
        data = load(path)
        self.model = data["model"]
        self.calibrator = data.get("calibrator", None)
        self.calibration_method = data.get("calibration_method", None)
        self.calibration_metrics = data.get("calibration_metrics", {})
        self.features = data.get("features", MODEL_FEATURES)
        self.is_fitted = data.get("is_fitted", True)
        self.is_pretrained = data.get("is_pretrained", True)
        print(f"[+] Loaded LandslideRiskModel from {path} (Calibration: {self.calibration_method})")


# Singleton model instance for server inference
_global_model: Optional[LandslideRiskModel] = None


def get_model() -> LandslideRiskModel:
    """Retrieve or initialize singleton model instance."""
    global _global_model
    if _global_model is None:
        _global_model = LandslideRiskModel()
        if DEFAULT_MODEL_PATH.exists():
            _global_model.load(DEFAULT_MODEL_PATH)
    return _global_model


def predict(features: Union[Dict[str, Any], pd.DataFrame]) -> Union[float, np.ndarray]:
    """Convenience functional predict interface returning calibrated failure probability."""
    model = get_model()
    return model.predict(features)
