"""Unit tests for ML models, probability calibration, baseline, and spatial/temporal validation logic."""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from ml.models.base_model import LandslideRiskModel, predict, MODEL_FEATURES, get_model, IsotonicCalibrator, PlattCalibrator
from ml.models.baseline import RainfallThresholdBaseline
from ml.evaluate import compute_metrics, compute_lead_time_hours, compute_ece, compute_brier_skill_score, compute_matched_operating_points


@pytest.fixture
def mock_physics_data():
    """Generate small mock physics dataset for rapid unit testing."""
    n = 200
    np.random.seed(42)
    slope = np.random.uniform(15.0, 50.0, n)
    cohesion = np.random.uniform(3.0, 25.0, n)
    friction = np.random.uniform(22.0, 42.0, n)
    depth = np.random.uniform(0.8, 3.5, n)
    sat = np.random.uniform(0.1, 0.9, n)
    rain = np.random.uniform(0.0, 150.0, n)
    fs = np.random.uniform(0.5, 2.5, n)
    failed = (fs < 1.0).astype(int)

    return pd.DataFrame({
        "slope_deg": slope,
        "cohesion_kpa": cohesion,
        "friction_angle_deg": friction,
        "soil_depth_m": depth,
        "antecedent_moisture": sat,
        "rainfall_mm": rain,
        "fs_deterministic": fs,
        "fs_noisy": fs + np.random.normal(0, 0.05, n),
        "failed": failed,
    })


@pytest.fixture
def mock_village_data():
    """Generate small mock village spatio-temporal dataframe."""
    np.random.seed(42)
    rows = []
    villages = [f"VIL_{i:02d}" for i in range(1, 11)]
    dates = pd.date_range("2022-06-01", periods=24 * 7, freq="h")

    for v in villages:
        elev = 1500.0 + hash(v) % 800
        slope = 28.0 + (hash(v) % 15)
        for t in dates:
            r1 = float(np.random.exponential(1.5))
            r3 = r1 * 2.5
            r24 = r1 * 8.0
            rows.append({
                "time": t,
                "village_id": v,
                "elevation": elev,
                "slope": slope,
                "aspect": 180.0,
                "curvature": 0.0,
                "upstream_catchment_area": 25.0,
                "distance_to_stream": 50.0,
                "ndvi": 0.5,
                "antecedent_moisture": 0.45,
                "rain_1h": r1,
                "rain_3h": r3,
                "rain_6h": r3 * 1.5,
                "rain_24h": r24,
                "rain_72h": r24 * 1.8,
                "factor_of_safety": 1.4,
                "landslide_within_6h": 1 if (r3 > 15.0 and slope > 30.0) else 0,
            })
    return pd.DataFrame(rows)


def test_baseline_threshold_calibration_and_predict(mock_village_data):
    """Test RainfallThresholdBaseline calibration and prediction."""
    baseline = RainfallThresholdBaseline(rain_3h_threshold_mm=30.0, rain_24h_threshold_mm=75.0)

    y = mock_village_data["landslide_within_6h"].values
    best_params = baseline.calibrate(mock_village_data, y)
    assert "rain_3h" in best_params
    assert "rain_24h" in best_params

    preds = baseline.predict(mock_village_data)
    assert len(preds) == len(mock_village_data)
    assert set(np.unique(preds)).issubset({0, 1})

    probs = baseline.predict_proba(mock_village_data)
    assert len(probs) == len(mock_village_data)
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)


def test_model_pretraining_finetuning_and_calibration(mock_physics_data, mock_village_data, tmp_path):
    """Test LandslideRiskModel pretraining, fine-tuning, calibration, save, and load."""
    model = LandslideRiskModel(n_estimators=10, max_depth=3, random_state=42)

    # 1. Pretrain on physics
    model.pretrain_on_physics(mock_physics_data)
    assert model.is_pretrained is True
    assert model.model is not None

    # 2. Split into train and calibration folds
    n_half = len(mock_village_data) // 2
    train_fold = mock_village_data.iloc[:n_half]
    calib_fold = mock_village_data.iloc[n_half:]

    # 3. Fine-tune and calibrate
    model.fine_tune(train_fold, calib_df=calib_fold, scale_pos_weight=5.0)
    assert model.is_fitted is True
    assert model.calibrator is not None
    assert model.calibration_method in ("isotonic", "platt")
    assert "brier_chosen" in model.calibration_metrics

    # 4. Predict proba on DataFrame
    probs = model.predict_proba(mock_village_data.head(20))
    assert len(probs) == 20
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)

    # 5. Predict on single dict returns float
    single_record = mock_village_data.iloc[0].to_dict()
    prob_single = model.predict(single_record)
    assert isinstance(prob_single, float)
    assert 0.0 <= prob_single <= 1.0

    # 6. Save and reload with calibrator
    save_file = tmp_path / "test_model_calibrated.joblib"
    model.save(save_file)
    assert save_file.exists()

    loaded_model = LandslideRiskModel()
    loaded_model.load(save_file)
    assert loaded_model.is_fitted is True
    assert loaded_model.calibration_method == model.calibration_method
    loaded_probs = loaded_model.predict_proba(mock_village_data.head(5))
    np.testing.assert_allclose(probs[:5], loaded_probs, rtol=1e-5)


def test_functional_predict_interface():
    """Test module-level predict function returning calibrated probability."""
    sample_features = {
        "rain_1h": 15.0,
        "rain_3h": 45.0,
        "rain_6h": 65.0,
        "rain_24h": 120.0,
        "rain_72h": 150.0,
        "antecedent_moisture": 0.75,
        "elevation": 1850.0,
        "slope": 38.0,
        "aspect": 190.0,
        "curvature": 0.02,
        "upstream_catchment_area": 40.0,
        "distance_to_stream": 45.0,
        "ndvi": 0.4,
        "factor_of_safety": 0.88,
    }
    prob = predict(sample_features)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_spatial_temporal_split_integrity():
    """Verify zero overlap between spatial/temporal train, calib, and test partitions."""
    all_villages = [f"VIL_UTK_{i:02d}" for i in range(1, 26)]
    holdout_villages = set([f"VIL_UTK_{i:02d}" for i in range(21, 26)])
    train_villages = set([v for v in all_villages if v not in holdout_villages])

    # Spatial disjointness
    assert len(train_villages.intersection(holdout_villages)) == 0
    assert len(train_villages) == 20
    assert len(holdout_villages) == 5

    # Temporal disjointness
    train_years = {2019, 2020, 2021}
    calib_year = {2022}
    test_year = {2023}
    assert len(train_years.intersection(calib_year)) == 0
    assert len(train_years.intersection(test_year)) == 0
    assert len(calib_year.intersection(test_year)) == 0


def test_ece_calculation():
    """Verify Expected Calibration Error (ECE) is within [0, 1] and decreases with better calibration."""
    y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    # Severely uncalibrated predictions (inflated)
    y_prob_poor = np.array([0.9, 0.85, 0.8, 0.75, 0.7, 0.95, 0.9, 0.88, 0.85, 0.9])
    ece_poor = compute_ece(y_true, y_prob_poor)

    # Well-calibrated predictions
    y_prob_good = np.array([0.05, 0.08, 0.1, 0.12, 0.15, 0.85, 0.88, 0.9, 0.92, 0.95])
    ece_good = compute_ece(y_true, y_prob_good)

    assert 0.0 <= ece_poor <= 1.0
    assert 0.0 <= ece_good <= 1.0
    assert ece_good < ece_poor


def test_brier_skill_score():
    """Verify Brier Skill Score calculation against climatology."""
    y_train = np.array([0] * 99 + [1] * 1)  # 1% positive climatology
    y_test = np.array([0] * 90 + [1] * 10)  # 10% positive test

    # Perfect predictions -> BSS should be close to 1.0
    y_prob_perfect = y_test.astype(float)
    bss, bs_m, bs_clim = compute_brier_skill_score(y_test, y_prob_perfect, y_train)
    assert bss > 0.8
    assert bs_m == 0.0

    # Terrible predictions -> BSS should be negative
    y_prob_terrible = 1.0 - y_test.astype(float)
    bss_bad, _, _ = compute_brier_skill_score(y_test, y_prob_terrible, y_train)
    assert bss_bad < 0.0


def test_matched_operating_points():
    """Verify matching POD and matching FAR find thresholds within small tolerance."""
    np.random.seed(42)
    n = 1000
    y_true = (np.random.rand(n) < 0.05).astype(int)
    # Model probabilities correlated with y_true
    model_proba = np.clip(y_true * 0.4 + np.random.beta(1, 10, n) * 0.2, 0.0, 1.0)

    # Baseline predictions with ~0.60 POD
    baseline_pred = np.zeros(n, dtype=int)
    pos_idx = np.where(y_true == 1)[0]
    baseline_pred[pos_idx[: int(0.6 * len(pos_idx))]] = 1
    # add some false positives
    neg_idx = np.where(y_true == 0)[0]
    baseline_pred[neg_idx[:30]] = 1

    matched = compute_matched_operating_points(y_true, model_proba, baseline_pred)
    assert "matched_pod_operating_point" in matched
    assert "matched_far_operating_point" in matched

    pt_a = matched["matched_pod_operating_point"]
    pt_b = matched["matched_far_operating_point"]

    # Difference in POD should be small (< 0.10)
    assert abs(pt_a["model_pod"] - pt_a["baseline_pod"]) < 0.10
    # Difference in FAR should be small (< 0.10)
    assert abs(pt_b["model_far"] - pt_b["baseline_far"]) < 0.10
