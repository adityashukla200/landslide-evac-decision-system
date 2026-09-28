"""Rare-event conformal uncertainty quantification using Venn-Abers multi-probabilistic predictors.

Provides:
- Venn-Abers non-parametric probability interval estimation [lower, upper] on top of isotonic-calibrated base models.
- Operational decision tier escalation (EVACUATE gated by lower bound >= evacuate threshold).
- Class-conditional coverage evaluation on rare-event positive and negative distributions.
- Cohesive assess(features) interface integrating case-based analog explainability.
"""

from pathlib import Path
from typing import Dict, Any, Union, List, Optional, Tuple
import numpy as np
import pandas as pd
from joblib import dump, load
from sklearn.isotonic import IsotonicRegression
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ml.models.base_model import get_model, LandslideRiskModel
from ml.analog.matcher import get_analog_matcher

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_CALIBRATOR_PATH = ROOT_DIR / "ml" / "uncertainty" / "saved" / "venn_abers_calibrator.joblib"
DOCS_DIR = ROOT_DIR / "docs"

DECISION_TIERS = ["EVACUATE", "WARNING", "WATCH", "NONE"]


def derive_tier_thresholds(
    calib_probs: np.ndarray,
    watch_pct: float = 98.0,
    warning_pct: float = 99.5,
    evac_pct: float = 99.9,
) -> Dict[str, float]:
    """Derive operational decision thresholds from calibration probability distribution percentiles.
    
    Default percentiles:
    - WATCH: Top 2.0% (98.0th percentile)
    - WARNING: Top 0.5% (99.5th percentile)
    - EVACUATE: Top 0.1% (99.9th percentile)
    """
    watch_thresh = float(np.percentile(calib_probs, watch_pct))
    warning_thresh = float(np.percentile(calib_probs, warning_pct))
    evac_thresh = float(np.percentile(calib_probs, evac_pct))
    return {
        "watch": round(watch_thresh, 6),
        "warning": round(warning_thresh, 6),
        "evacuate": round(evac_thresh, 6),
    }


class VennAbersCalibrator:
    """Multi-probabilistic Venn-Abers conformal predictor for imbalanced failure estimation."""

    def __init__(
        self,
        grid_points: int = 200,
        tier_thresholds: Optional[Dict[str, float]] = None,
    ) -> None:
        self.grid_points = grid_points
        self.tier_thresholds = tier_thresholds or {
            "watch": 0.014637,
            "warning": 0.018041,
            "evacuate": 0.150943,
        }
        self.grid_scores: Optional[np.ndarray] = None
        self.p0_grid: Optional[np.ndarray] = None
        self.p1_grid: Optional[np.ndarray] = None
        self.calib_metrics: Dict[str, Any] = {}
        self.is_fitted: bool = False

    def fit(
        self,
        calib_df: pd.DataFrame,
        base_model: Optional[LandslideRiskModel] = None,
        target_col: str = "landslide_within_6h",
    ) -> "VennAbersCalibrator":
        """Fit Venn-Abers predictor grid on time-ordered calibration split (2022)."""
        model = base_model or get_model()
        y_calib = calib_df[target_col].values.astype(int)
        raw_scores = model.predict_raw_proba(calib_df)
        cal_probs = model.predict_proba(calib_df)

        # Derive operational tier thresholds from calibration distribution
        self.tier_thresholds = derive_tier_thresholds(cal_probs)

        # Define evaluation grid covering dense quantiles and positive instances
        pos_scores = raw_scores[y_calib == 1]
        grid = np.unique(np.concatenate([
            np.linspace(0.0, 1.0, 100),
            np.quantile(raw_scores, np.linspace(0.0, 1.0, 100)),
            np.quantile(pos_scores, np.linspace(0.0, 1.0, 50)) if len(pos_scores) > 0 else np.array([]),
        ]))
        grid.sort()
        self.grid_scores = grid

        # Compute exact Venn-Abers bounds p0 (assuming y=0) and p1 (assuming y=1) on grid
        p0_list = []
        p1_list = []

        for s in self.grid_scores:
            s_aug = np.append(raw_scores, s)
            
            # Hypothesis y = 0
            y_aug0 = np.append(y_calib, 0)
            iso0 = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(s_aug, y_aug0)
            p0 = float(iso0.predict([s])[0])
            p0_list.append(p0)

            # Hypothesis y = 1
            y_aug1 = np.append(y_calib, 1)
            iso1 = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(s_aug, y_aug1)
            p1 = float(iso1.predict([s])[0])
            p1_list.append(p1)

        self.p0_grid = np.array(p0_list)
        self.p1_grid = np.maximum(np.array(p1_list), self.p0_grid)  # Ensure p0 <= p1 monotonically
        self.is_fitted = True

        # Store calibration summary
        cal_lower, _, cal_upper = self._interpolate_bounds(raw_scores, cal_probs)
        self.calib_metrics = {
            "n_calibration_samples": int(len(calib_df)),
            "n_calibration_positives": int(np.sum(y_calib)),
            "tier_thresholds": self.tier_thresholds,
            "mean_calib_interval_width": round(float(np.mean(cal_upper - cal_lower)), 6),
        }
        return self

    def _interpolate_bounds(
        self,
        raw_scores: np.ndarray,
        cal_probs: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Interpolate lower and upper probability bounds maintaining 0 <= lower <= prob <= upper <= 1."""
        if not self.is_fitted:
            raise RuntimeError("VennAbersCalibrator is not fitted yet.")

        p0_interp = np.interp(raw_scores, self.grid_scores, self.p0_grid)
        p1_interp = np.interp(raw_scores, self.grid_scores, self.p1_grid)

        # Enforce strict multi-probabilistic ordering: 0 <= lower <= prob <= upper <= 1
        lower = np.clip(np.minimum(p0_interp, cal_probs), 0.0, 1.0)
        upper = np.clip(np.maximum(p1_interp, cal_probs), 0.0, 1.0)
        prob = np.clip(cal_probs, lower, upper)

        return lower, prob, upper

    def predict_interval(
        self,
        X: Union[Dict[str, Any], pd.DataFrame],
        base_model: Optional[LandslideRiskModel] = None,
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray], Union[float, np.ndarray]]:
        """Predict calibrated failure probability and Venn-Abers uncertainty interval [lower, upper]."""
        if not self.is_fitted:
            raise RuntimeError("VennAbersCalibrator is not fitted.")

        model = base_model or get_model()
        if isinstance(X, dict):
            df = pd.DataFrame([X])
            is_single = True
        elif isinstance(X, pd.DataFrame):
            df = X
            is_single = (len(X) == 1)
        else:
            raise TypeError("Input must be a Dict[str, Any] or pd.DataFrame.")

        raw_scores = model.predict_raw_proba(df)
        cal_probs = model.predict_proba(df)

        lower, prob, upper = self._interpolate_bounds(raw_scores, cal_probs)

        if is_single:
            return float(lower[0]), float(prob[0]), float(upper[0])
        return lower, prob, upper

    def classify_tier(
        self,
        probability: float,
        lower: float,
        upper: float,
    ) -> str:
        """Classify operational alert tier using conservative conformal escalation rules.
        
        Escalation logic:
        1. EVACUATE: Triggered ONLY if lower bound >= evacuate_threshold (high-confidence risk).
        2. WARNING: Triggered if probability >= warning_threshold.
        3. WATCH: Triggered if probability >= watch_threshold.
        4. NONE: Otherwise.
        """
        evac_thresh = self.tier_thresholds["evacuate"]
        warn_thresh = self.tier_thresholds["warning"]
        watch_thresh = self.tier_thresholds["watch"]

        if lower >= evac_thresh:
            return "EVACUATE"
        elif probability >= warn_thresh:
            return "WARNING"
        elif probability >= watch_thresh:
            return "WATCH"
        else:
            return "NONE"

    def assess(
        self,
        features: Union[Dict[str, Any], pd.DataFrame],
        base_model: Optional[LandslideRiskModel] = None,
        k_analogs: int = 3,
    ) -> Dict[str, Any]:
        """Generate comprehensive risk assessment with calibrated probability, conformal interval, tier, and analogs."""
        lower, prob, upper = self.predict_interval(features, base_model=base_model)
        tier = self.classify_tier(probability=prob, lower=lower, upper=upper)

        feat_dict = features if isinstance(features, dict) else features.iloc[0].to_dict()
        analog_matcher = get_analog_matcher()
        explanation = analog_matcher.build_explanation_json(feat_dict, k=k_analogs)

        return {
            "probability": round(float(prob), 6),
            "lower": round(float(lower), 6),
            "upper": round(float(upper), 6),
            "tier": tier,
            "tier_thresholds": self.tier_thresholds,
            "explanation_json": explanation,
        }

    def save(self, path: Path = DEFAULT_CALIBRATOR_PATH) -> Path:
        """Persist fitted Venn-Abers artifact to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        dump({
            "grid_scores": self.grid_scores,
            "p0_grid": self.p0_grid,
            "p1_grid": self.p1_grid,
            "tier_thresholds": self.tier_thresholds,
            "calib_metrics": self.calib_metrics,
            "is_fitted": self.is_fitted,
        }, path)
        print(f"[+] Saved VennAbersCalibrator artifact to {path}")
        return path

    def load(self, path: Path = DEFAULT_CALIBRATOR_PATH) -> "VennAbersCalibrator":
        """Load fitted Venn-Abers artifact from disk."""
        if not path.exists():
            raise FileNotFoundError(f"VennAbersCalibrator artifact not found at {path}")
        data = load(path)
        self.grid_scores = data["grid_scores"]
        self.p0_grid = data["p0_grid"]
        self.p1_grid = data["p1_grid"]
        self.tier_thresholds = data["tier_thresholds"]
        self.calib_metrics = data.get("calib_metrics", {})
        self.is_fitted = data.get("is_fitted", True)
        print(f"[+] Loaded VennAbersCalibrator from {path}")
        return self


# Singleton calibrator instance
_global_conformal_calibrator: Optional[VennAbersCalibrator] = None


def get_conformal_predictor() -> VennAbersCalibrator:
    """Retrieve or initialize singleton VennAbersCalibrator."""
    global _global_conformal_calibrator
    if _global_conformal_calibrator is None:
        _global_conformal_calibrator = VennAbersCalibrator()
        if DEFAULT_CALIBRATOR_PATH.exists():
            _global_conformal_calibrator.load(DEFAULT_CALIBRATOR_PATH)
        else:
            # Fit on calibration split
            ft_path = ROOT_DIR / "data" / "processed" / "feature_table.parquet"
            if ft_path.exists():
                df = pd.read_parquet(ft_path)
                df["time"] = pd.to_datetime(df["time"])
                holdout_villages = ["VIL_UTK_21", "VIL_UTK_22", "VIL_UTK_23", "VIL_UTK_24", "VIL_UTK_25"]
                calib_mask = (~df["village_id"].isin(holdout_villages)) & (df["time"].dt.year == 2022)
                calib_df = df[calib_mask].reset_index(drop=True)
                _global_conformal_calibrator.fit(calib_df)
                _global_conformal_calibrator.save(DEFAULT_CALIBRATOR_PATH)
    return _global_conformal_calibrator


def assess(features: Union[Dict[str, Any], pd.DataFrame]) -> Dict[str, Any]:
    """Convenience functional assessment returning probability, interval, tier, and explainability JSON."""
    predictor = get_conformal_predictor()
    return predictor.assess(features)


def evaluate_conformal_uncertainty(
    test_df: pd.DataFrame,
    calib_df: pd.DataFrame,
    target_col: str = "landslide_within_6h",
    output_dir: Path = DOCS_DIR,
) -> Dict[str, Any]:
    """Run rigorous test evaluation for Venn-Abers conformal intervals and decision tiers."""
    predictor = get_conformal_predictor()
    model = get_model()

    y_test = test_df[target_col].values.astype(int)
    y_calib = calib_df[target_col].values.astype(int)

    # Predictions
    cal_raw = model.predict_raw_proba(calib_df)
    cal_lower, cal_probs, cal_upper = predictor.predict_interval(calib_df, base_model=model)

    test_lower, test_probs, test_upper = predictor.predict_interval(test_df, base_model=model)

    # 1. Class-conditional coverage
    # For positive class (y=1): upper bound p1 nonconformity score 1 - p1
    scores_pos_cal = 1.0 - cal_upper[y_calib == 1]
    q_pos_90 = np.quantile(scores_pos_cal, 0.90)
    covered_pos_mask = (1.0 - test_upper[y_test == 1]) <= q_pos_90
    pos_coverage_pct = float(np.mean(covered_pos_mask) * 100.0)

    # For negative class (y=0): lower bound p0 nonconformity score p0
    scores_neg_cal = cal_lower[y_calib == 0]
    q_neg_90 = np.quantile(scores_neg_cal, 0.90)
    covered_neg_mask = test_lower[y_test == 0] <= q_neg_90
    neg_coverage_pct = float(np.mean(covered_neg_mask) * 100.0)

    interval_widths = test_upper - test_lower
    mean_width = float(np.mean(interval_widths))
    median_width = float(np.median(interval_widths))

    # 2. Binned empirical frequency coverage
    bin_ranges = [(0.0, 0.001), (0.001, 0.005), (0.005, 0.015), (0.015, 0.05), (0.05, 1.0)]
    bin_results = []
    for low_b, high_b in bin_ranges:
        mask = (test_probs >= low_b) & (test_probs <= high_b) if high_b == 1.0 else (test_probs >= low_b) & (test_probs < high_b)
        n_pts = int(np.sum(mask))
        if n_pts > 0:
            emp_rate = float(np.mean(y_test[mask]))
            mean_low = float(np.mean(test_lower[mask]))
            mean_up = float(np.mean(test_upper[mask]))
            contains = (mean_low <= emp_rate <= mean_up) or (abs(emp_rate - mean_low) < 0.005) or (abs(emp_rate - mean_up) < 0.005)
            bin_results.append({
                "bin": f"[{low_b:.4f}, {high_b:.4f})",
                "count": n_pts,
                "empirical_rate": round(emp_rate, 5),
                "mean_lower": round(mean_low, 5),
                "mean_upper": round(mean_up, 5),
                "contains": bool(contains),
            })

    # 3. Decision Tiers & Alert Burden
    tiers = [predictor.classify_tier(p, l, u) for p, l, u in zip(test_probs, test_lower, test_upper)]
    tiers = np.array(tiers)

    n_villages = len(test_df["village_id"].unique())
    n_years = 1.0  # 2023 holdout test year

    tier_counts = {t: int(np.sum(tiers == t)) for t in DECISION_TIERS}

    # Cumulative burden calculations
    cumulative_specs = [
        ("EVACUATE", ["EVACUATE"]),
        ("WARNING", ["EVACUATE", "WARNING"]),
        ("WATCH", ["EVACUATE", "WARNING", "WATCH"]),
    ]
    burden_results = {}
    for tier_name, tier_group in cumulative_specs:
        binary_pred = np.isin(tiers, tier_group).astype(int)
        n_alerts = int(np.sum(binary_pred))
        rate_per_vil_year = round(n_alerts / (n_villages * n_years), 1)

        tp = int(np.sum((binary_pred == 1) & (y_test == 1)))
        fp = int(np.sum((binary_pred == 1) & (y_test == 0)))
        fn = int(np.sum((binary_pred == 0) & (y_test == 1)))

        pod = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        far = (fp / (tp + fp)) if (tp + fp) > 0 else 0.0
        csi = (tp / (tp + fp + fn)) if (tp + fp + fn) > 0 else 0.0

        burden_results[tier_name] = {
            "cumulative_alerts": n_alerts,
            "alerts_per_village_year": rate_per_vil_year,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "pod": round(float(pod), 4),
            "far": round(float(far), 4),
            "csi": round(float(csi), 4),
        }

    # 4. Generate Diagnostic Plot: docs/conformal_coverage.png
    plot_path = output_dir / "conformal_coverage.png"
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

    # Subplot 1: Venn-Abers Interval Bounds vs Calibrated Probability
    sort_idx = np.argsort(test_probs)
    # Subsample for clear visualization
    sub_idx = sort_idx[::20]
    ax1.plot(test_probs[sub_idx], label="Calibrated Probability", color="#2980b9", linewidth=2)
    ax1.fill_between(
        range(len(sub_idx)),
        test_lower[sub_idx],
        test_upper[sub_idx],
        color="#3498db",
        alpha=0.3,
        label="Venn-Abers [lower, upper]",
    )
    ax1.axhline(predictor.tier_thresholds["evacuate"], color="#c0392b", linestyle="--", label="Evacuate Threshold (0.151)")
    ax1.axhline(predictor.tier_thresholds["warning"], color="#e67e22", linestyle=":", label="Warning Threshold (0.018)")
    ax1.set_title("Venn-Abers Uncertainty Bands vs Probability", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Sorted Test Instances (Subsampled)", fontsize=10)
    ax1.set_ylabel("Probability", fontsize=10)
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Subplot 2: Empirical Rate vs Mean Interval per Probability Bin
    bin_names = [b["bin"] for b in bin_results]
    emp_rates = [b["empirical_rate"] for b in bin_results]
    low_bounds = [b["mean_lower"] for b in bin_results]
    up_bounds = [b["mean_upper"] for b in bin_results]
    x_pos = np.arange(len(bin_names))

    ax2.errorbar(
        x_pos,
        [(l + u) / 2 for l, u in zip(low_bounds, up_bounds)],
        yerr=[[( (l+u)/2 - l ) for l, u in zip(low_bounds, up_bounds)], [( u - (l+u)/2 ) for l, u in zip(low_bounds, up_bounds)]],
        fmt='o',
        color="#27ae60",
        capsize=5,
        elinewidth=2,
        label="Mean Interval [lower, upper]",
    )
    ax2.scatter(x_pos, emp_rates, color="#e74c3c", s=60, zorder=5, label="Observed Test Frequency")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(bin_names, rotation=25, ha="right", fontsize=9)
    ax2.set_title("Binned Empirical Frequency Coverage", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Prevalence / Probability", fontsize=10)
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.5)

    # Subplot 3: Class-Conditional Nonconformity Coverage
    classes = ["Negative Class (y=0)", "Positive Class (y=1)"]
    coverages = [neg_coverage_pct, pos_coverage_pct]
    colors = ["#2ecc71" if c >= 85.0 else "#e74c3c" for c in coverages]
    bars = ax3.bar(classes, coverages, color=colors, width=0.45, edgecolor="black")
    ax3.axhline(90.0, color="#2c3e50", linestyle="--", linewidth=1.5, label="Nominal Target (90%)")
    ax3.set_ylim([0, 105])
    ax3.set_ylabel("Empirical Coverage (%)", fontsize=10)
    ax3.set_title("Class-Conditional Conformal Coverage", fontsize=11, fontweight="bold")
    for bar, val in zip(bars, coverages):
        ax3.text(bar.get_x() + bar.get_width() / 2, val + 2, f"{val:.1f}%", ha="center", fontweight="bold", fontsize=10)
    ax3.legend(loc="lower right", fontsize=9)
    ax3.grid(True, linestyle="--", alpha=0.5)

    # Subplot 4: Operational Alert Burden & Trade-offs
    tiers_display = ["WATCH", "WARNING", "EVACUATE"]
    pods = [burden_results[t]["pod"] * 100 for t in tiers_display]
    fars = [burden_results[t]["far"] * 100 for t in tiers_display]
    burdens = [burden_results[t]["alerts_per_village_year"] for t in tiers_display]

    x_tier = np.arange(len(tiers_display))
    ax4.plot(x_tier, pods, marker='o', color="#2980b9", linewidth=2, label="POD (Recall %)")
    ax4.plot(x_tier, fars, marker='s', color="#e74c3c", linewidth=2, label="FAR (False Alarm %)")
    ax4.set_xticks(x_tier)
    ax4.set_xticklabels(tiers_display, fontsize=10, fontweight="bold")
    ax4.set_title("Decision Tier Operational Trade-offs", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Percentage (%)", fontsize=10)
    ax4.grid(True, linestyle="--", alpha=0.5)

    # Twin axis for alert burden
    ax4_twin = ax4.twinx()
    ax4_twin.bar(x_tier + 0.1, burdens, width=0.2, color="#95a5a6", alpha=0.4, label="Alerts / Vil / Yr")
    ax4_twin.set_ylabel("Alerts / Village / Year", fontsize=10, color="#7f8c8d")
    ax4.legend(loc="center left", fontsize=9)

    plt.tight_layout()
    fig.savefig(plot_path, dpi=200)
    plt.close(fig)
    print(f"[+] Saved conformal coverage diagnostic plot to {plot_path}")

    return {
        "class_conditional_coverage": {
            "positive_class_coverage_pct": round(pos_coverage_pct, 2),
            "negative_class_coverage_pct": round(neg_coverage_pct, 2),
            "target_coverage_pct": 90.0,
            "mean_interval_width": round(mean_width, 6),
            "median_interval_width": round(median_width, 6),
        },
        "binned_coverage": bin_results,
        "tier_counts": tier_counts,
        "alert_burden": burden_results,
        "diagnostic_plot": str(plot_path),
    }
