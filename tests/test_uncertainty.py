"""Unit tests for /ml/uncertainty conformal prediction and operational decision tier engine."""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from ml.uncertainty.conformal import (
    VennAbersCalibrator,
    assess,
    get_conformal_predictor,
    derive_tier_thresholds,
    DECISION_TIERS,
)
from ml.models.base_model import get_model, LandslideRiskModel


def test_tier_threshold_derivation():
    """Verify tier thresholds obey monotonic ordering: 0 < WATCH < WARNING < EVACUATE < 1."""
    np.random.seed(42)
    synthetic_probs = np.random.beta(a=0.5, b=50, size=10000)  # Heavy right-skewed rare-event distribution
    thresholds = derive_tier_thresholds(synthetic_probs, watch_pct=98.0, warning_pct=99.5, evac_pct=99.9)

    assert "watch" in thresholds
    assert "warning" in thresholds
    assert "evacuate" in thresholds

    watch = thresholds["watch"]
    warning = thresholds["warning"]
    evacuate = thresholds["evacuate"]

    assert 0.0 < watch < warning < evacuate <= 1.0


def test_conformal_predictor_loaded_and_monotonic():
    """Verify loaded Venn-Abers predictor adheres to strict multi-probabilistic ordering."""
    predictor = get_conformal_predictor()
    assert predictor.is_fitted
    assert predictor.grid_scores is not None
    assert predictor.p0_grid is not None
    assert predictor.p1_grid is not None

    # Check p0 <= p1 monotonically across the entire grid
    assert np.all(predictor.p0_grid <= predictor.p1_grid + 1e-9)

    # Threshold values check
    th = predictor.tier_thresholds
    assert 0.0 < th["watch"] < th["warning"] < th["evacuate"] < 1.0


def test_predict_interval_ordering_and_bounds():
    """Test that 0 <= lower <= probability <= upper <= 1 holds for arbitrary inputs."""
    predictor = get_conformal_predictor()
    model = get_model()

    test_samples = [
        {"rain_1h": 0.0, "rain_3h": 0.0, "rain_24h": 0.0, "slope": 10.0, "factor_of_safety": 2.5, "antecedent_moisture": 0.2},
        {"rain_1h": 15.0, "rain_3h": 40.0, "rain_24h": 90.0, "slope": 32.0, "factor_of_safety": 1.1, "antecedent_moisture": 0.65},
        {"rain_1h": 45.0, "rain_3h": 95.0, "rain_24h": 160.0, "slope": 42.0, "factor_of_safety": 0.72, "antecedent_moisture": 0.92},
    ]

    for sample in test_samples:
        lower, prob, upper = predictor.predict_interval(sample, base_model=model)
        assert 0.0 <= lower <= 1.0
        assert 0.0 <= prob <= 1.0
        assert 0.0 <= upper <= 1.0
        assert lower <= prob + 1e-6
        assert prob <= upper + 1e-6


def test_conservative_escalation_rules():
    """Verify decision tier classification logic, specifically that EVACUATE requires lower >= evacuate_thresh."""
    predictor = get_conformal_predictor()
    th = predictor.tier_thresholds
    evac_thresh = th["evacuate"]
    warn_thresh = th["warning"]
    watch_thresh = th["watch"]

    # 1. NONE: prob below watch
    tier = predictor.classify_tier(probability=watch_thresh - 0.005, lower=0.0, upper=0.010)
    assert tier == "NONE"

    # 2. WATCH: prob >= watch_thresh, but < warn_thresh
    tier = predictor.classify_tier(probability=watch_thresh + 0.001, lower=watch_thresh - 0.001, upper=watch_thresh + 0.005)
    assert tier == "WATCH"

    # 3. WARNING: prob >= warn_thresh, but lower < evac_thresh
    tier = predictor.classify_tier(probability=warn_thresh + 0.010, lower=warn_thresh - 0.002, upper=0.100)
    assert tier == "WARNING"

    # 4. High probability but lower bound below evac_thresh -> Must NOT escalate to EVACUATE, stays WARNING
    tier = predictor.classify_tier(probability=evac_thresh + 0.050, lower=evac_thresh - 0.010, upper=0.350)
    assert tier == "WARNING"

    # 5. EVACUATE: Triggered ONLY when lower >= evac_thresh
    tier = predictor.classify_tier(probability=evac_thresh + 0.050, lower=evac_thresh + 0.001, upper=0.350)
    assert tier == "EVACUATE"


def test_assess_schema_and_analog_separation():
    """Verify assess() returns the expected contract and does NOT confuse analog rate with probability."""
    sample = {
        "rain_1h": 22.0,
        "rain_3h": 55.0,
        "rain_24h": 110.0,
        "slope": 36.0,
        "elevation": 1850.0,
        "factor_of_safety": 0.88,
        "antecedent_moisture": 0.78,
    }

    res = assess(sample)

    assert "probability" in res
    assert "lower" in res
    assert "upper" in res
    assert "tier" in res
    assert "tier_thresholds" in res
    assert "explanation_json" in res

    assert res["tier"] in DECISION_TIERS
    assert 0.0 <= res["lower"] <= res["probability"] <= res["upper"] <= 1.0

    # Verify explainability structure
    expl = res["explanation_json"]
    assert "top_analogs" in expl
    assert "key_drivers" in expl
    assert len(expl["top_analogs"]) > 0

    # Ensure analog landslide rate is clearly separated from calibrated probability
    analog_rate = expl.get("analog_landslide_rate")
    assert analog_rate is not None
    assert isinstance(analog_rate, float)
    assert "analog_landslide_rate" != "probability"


def test_calibrator_save_and_load(tmp_path: Path):
    """Test serialization and loading of VennAbersCalibrator artifact."""
    orig = get_conformal_predictor()
    temp_file = tmp_path / "test_conformal.joblib"

    orig.save(temp_file)
    assert temp_file.exists()

    loaded = VennAbersCalibrator().load(temp_file)
    assert loaded.is_fitted
    assert np.allclose(loaded.p0_grid, orig.p0_grid)
    assert np.allclose(loaded.p1_grid, orig.p1_grid)
    assert loaded.tier_thresholds == orig.tier_thresholds
