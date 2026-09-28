"""Unit tests for geotechnical slope stability, Monte Carlo scenario generator, and catchment hydrology."""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.physics.slope_stability import compute_infinite_slope_fs, factor_of_safety
from ml.physics.scenario_generator import generate_physics_scenarios
from ml.physics.hydrology import (
    compute_scs_cn_runoff,
    estimate_time_of_concentration,
    compute_catchment_hydrograph,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_fs_decreases_with_slope():
    """Verify that Factor of Safety decreases monotonically as slope angle increases."""
    slopes = np.array([15.0, 25.0, 35.0, 45.0, 55.0])
    fs_values = compute_infinite_slope_fs(
        slope_deg=slopes,
        cohesion_kpa=12.0,
        friction_angle_deg=32.0,
        soil_depth_m=1.8,
        saturation_ratio=0.4,
    )

    # Strictly monotonically decreasing: FS[i] > FS[i+1]
    for i in range(len(fs_values) - 1):
        assert fs_values[i] > fs_values[i + 1], (
            f"FS at slope {slopes[i]}° ({fs_values[i]:.3f}) should exceed FS at {slopes[i+1]}° ({fs_values[i+1]:.3f})"
        )


def test_fs_decreases_with_saturation():
    """Verify that Factor of Safety decreases monotonically as saturation ratio increases."""
    saturations = np.array([0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    fs_values = compute_infinite_slope_fs(
        slope_deg=32.0,
        cohesion_kpa=12.0,
        friction_angle_deg=32.0,
        soil_depth_m=1.8,
        saturation_ratio=saturations,
    )

    for i in range(len(fs_values) - 1):
        assert fs_values[i] > fs_values[i + 1], (
            f"FS at saturation {saturations[i]} ({fs_values[i]:.3f}) should exceed FS at {saturations[i+1]} ({fs_values[i+1]:.3f})"
        )


def test_factor_of_safety_explainability_function():
    """Verify operational factor_of_safety function outputs valid schema, stresses, and diagnosis."""
    gentle_village = {"slope": 18.0, "elevation": 1100.0, "antecedent_moisture": 0.25}
    steep_village = {"slope": 42.0, "elevation": 2400.0, "antecedent_moisture": 0.85}

    # Low rainfall on gentle slope: must be STABLE
    res_stable = factor_of_safety(gentle_village, rainfall_series=[2.0, 1.0, 0.0])
    assert res_stable["factor_of_safety"] > 1.30
    assert res_stable["diagnosis"] == "STABLE"
    assert res_stable["resisting_strength_kpa"] > res_stable["driving_stress_kpa"]

    # Extreme rainfall on steep saturated slope: must be CRITICAL_FAILURE
    extreme_rain = [45.0, 55.0, 30.0]  # 130 mm cloudburst
    res_unstable = factor_of_safety(steep_village, rainfall_series=extreme_rain)
    assert res_unstable["factor_of_safety"] < 1.0
    assert res_unstable["diagnosis"] == "CRITICAL_FAILURE"
    assert res_unstable["driving_stress_kpa"] > res_unstable["resisting_strength_kpa"]


def test_scenario_generator_dataset_properties():
    """Verify the generated physics dataset contains >= 100,000 valid scenarios with noise."""
    parquet_path = ROOT_DIR / "data" / "processed" / "physics_synthetic.parquet"
    assert parquet_path.exists(), "Expected /data/processed/physics_synthetic.parquet to exist."

    df = pd.read_parquet(parquet_path)
    assert len(df) >= 100_000, f"Expected >= 100,000 scenarios, found {len(df):,}"

    required_cols = [
        "slope_deg",
        "cohesion_kpa",
        "friction_angle_deg",
        "soil_depth_m",
        "rainfall_mm",
        "antecedent_moisture",
        "saturation_ratio",
        "fs_deterministic",
        "fs_noisy",
        "failed",
    ]
    assert list(df.columns) == required_cols
    assert df.isna().sum().sum() == 0, "Physics dataset must have zero NaNs"

    # Verify both failure and stable classes are populated
    failure_rate = df["failed"].mean()
    assert 0.05 <= failure_rate <= 0.35, f"Failure rate {failure_rate:.2%} out of expected range (5% - 35%)"

    # Verify noise effect: fs_noisy differs from fs_deterministic
    diff = np.abs(df["fs_noisy"] - df["fs_deterministic"]).mean()
    assert diff > 0.01, "Expected noise perturbation between deterministic and noisy FS"


def test_hydrology_scs_cn_mass_balance():
    """Verify SCS-CN runoff generation obeys conservation of mass: Q <= P and delta_Q >= 0."""
    # Synthetic hyetograph: dry start, cloudburst, receding drizzle
    hyetograph = np.array([0.0, 0.0, 5.0, 18.0, 45.0, 60.0, 25.0, 8.0, 2.0, 0.0])
    q_inc, q_cum = compute_scs_cn_runoff(hyetograph, curve_number=75.0)

    # 1. Non-negativity
    assert np.all(q_inc >= 0.0), "Incremental runoff must be non-negative"
    assert np.all(q_cum >= 0.0), "Cumulative runoff must be non-negative"

    # 2. Conservation: Runoff cannot exceed rainfall
    total_precip = np.sum(hyetograph)
    total_runoff = q_cum[-1]
    assert total_runoff <= total_precip, f"Runoff ({total_runoff:.2f} mm) cannot exceed rainfall ({total_precip:.2f} mm)"

    # 3. Initial abstraction threshold
    # Initial 5mm should produce zero runoff (below Ia)
    assert q_cum[2] == 0.0


def test_catchment_hydrograph_simulation():
    """Verify catchment hydrograph simulation and strict volumetric mass balance."""
    village = {
        "upstream_catchment_area": 45.0,  # km^2
        "slope": 28.0,
        "elevation": 1650.0,
    }
    # 24-hour storm hyetograph with 110 mm total rain
    storm = np.zeros(24)
    storm[6:12] = [10.0, 25.0, 42.0, 20.0, 10.0, 3.0]

    result = compute_catchment_hydrograph(village, storm)

    assert result["peak_discharge_m3s"] > 0.0
    assert result["time_of_concentration_hours"] > 0.3
    assert result["runoff_coefficient"] < 1.0

    # Strict volumetric mass conservation: Precip Vol = Runoff Vol + Retention Vol
    v_precip = result["total_precipitation_vol_m3"]
    v_runoff = result["total_runoff_vol_m3"]
    v_retention = result["retention_vol_m3"]

    assert v_precip > 0.0
    assert v_runoff > 0.0
    assert v_retention >= 0.0
    assert abs(v_runoff + v_retention - v_precip) < 1.0, "Volumetric mass balance violated"
    assert result["mass_balance_error_pct"] < 0.001
