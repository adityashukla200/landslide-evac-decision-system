"""Unit tests for ML Data module, loaders, synthetic generator, and feature store."""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.data.synthetic import SyntheticDataGenerator
from ml.data.loaders import (
    load_rainfall,
    load_dem,
    load_soil_moisture,
    load_land_use,
    load_landslide_inventory,
    load_feature_table,
)


@pytest.fixture(scope="module")
def generator():
    """Module-level generator instance with deterministic seed."""
    return SyntheticDataGenerator(seed=42)


@pytest.fixture(scope="module")
def seeded_villages(generator):
    """Retrieve 25 pilot villages from database."""
    villages = generator.get_or_load_villages()
    assert len(villages) == 25
    return villages


def test_villages_from_database(seeded_villages):
    """Verify villages are read directly from the database and not invented."""
    assert len(seeded_villages) == 25
    ids = {v["id"] for v in seeded_villages}
    assert "VIL_UTK_01" in ids
    assert "VIL_UTK_25" in ids
    for v in seeded_villages:
        assert 800 <= v["elevation"] <= 3200
        assert 30.5 <= v["lat"] <= 31.3
        assert 78.0 <= v["lon"] <= 78.9


def test_terrain_features_plausibility(generator, seeded_villages):
    """Verify synthetic terrain features are consistent with seeded village elevations."""
    terrain_df = generator.generate_terrain_features(seeded_villages)
    assert len(terrain_df) == 25

    required_cols = {
        "village_id",
        "elevation",
        "slope",
        "aspect",
        "curvature",
        "upstream_catchment_area",
        "distance_to_stream",
        "ndvi",
    }
    assert required_cols.issubset(terrain_df.columns)

    for _, row in terrain_df.iterrows():
        assert 14.0 <= row["slope"] <= 55.0, f"Unrealistic slope: {row['slope']}"
        assert 0.0 <= row["aspect"] <= 360.0
        assert -0.06 <= row["curvature"] <= 0.06
        assert row["upstream_catchment_area"] > 0
        assert 10.0 <= row["distance_to_stream"] <= 500.0
        assert 0.15 <= row["ndvi"] <= 0.85


def test_rainfall_monsoon_seasonality_and_cloudbursts(generator, seeded_villages):
    """Verify monsoon seasonality (June-Sept peak) and presence of cloudbursts (100+ mm in 3h)."""
    # Test on a 3-village subset for fast unit testing of generation logic
    subset_villages = seeded_villages[:3]
    df = generator.generate_full_dataset(subset_villages)[1]

    # Verify time range
    assert df["time"].min() == pd.Timestamp("2019-01-01 00:00:00")
    assert df["time"].max() == pd.Timestamp("2023-12-31 23:00:00")

    # Check seasonality: July/August rain vs January/February rain
    df["month"] = df["time"].dt.month
    monsoon_mean_rain = df[df["month"].isin([7, 8])]["rain_1h"].mean()
    winter_mean_rain = df[df["month"].isin([1, 2])]["rain_1h"].mean()
    assert monsoon_mean_rain >= 3.0 * winter_mean_rain, (
        f"Monsoon rain ({monsoon_mean_rain:.2f} mm/h) should be at least 3x winter rain ({winter_mean_rain:.2f} mm/h)"
    )

    # Check extreme cloudburst occurrence (100+ mm in 3 hours)
    max_3h = df["rain_3h"].max()
    assert max_3h >= 100.0, f"Expected cloudburst > 100 mm in 3h, found max: {max_3h:.2f} mm"

    # Check antecedent soil moisture bounds
    assert df["antecedent_moisture"].min() >= 0.04
    assert df["antecedent_moisture"].max() <= 1.0


def test_landslide_inventory_properties():
    """Verify synthetic landslide inventory contains ~300 events with realistic columns."""
    inv = load_landslide_inventory()
    assert 250 <= len(inv) <= 350, f"Expected ~300 events, found {len(inv)}"

    required_cols = {"village_id", "lat", "lon", "date", "type", "rain_3h_at_failure", "slope_deg"}
    assert required_cols.issubset(inv.columns)

    # All landslide events must occur under substantial rainfall and steep slopes
    assert inv["slope_deg"].min() >= 18.0
    assert inv["rain_3h_at_failure"].min() >= 20.0
    assert set(inv["type"]).issubset({"debris_flow", "rockfall", "shallow_translational", "mudslide"})


def test_feature_table_structure_and_rare_labels():
    """Verify feature table parquet has valid schema, no NaNs, and rare positive labels (< 1%)."""
    ft = load_feature_table()
    assert len(ft) == 1_095_600  # 25 villages * 43,824 hours

    expected_cols = [
        "village_id",
        "time",
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
        "landslide_within_6h",
    ]
    assert list(ft.columns) == expected_cols
    assert ft.isna().sum().sum() == 0, "Feature table must contain zero null/NaN values"

    pos_rate = ft["landslide_within_6h"].mean()
    assert 0.0005 <= pos_rate <= 0.005, f"Positive rate {pos_rate:.4%} out of expected range (< 1%)"


def test_loaders_fallback_with_empty_directories(tmp_path):
    """Verify all loaders gracefully fall back to synthetic generator when raw directory is empty."""
    empty_dir = tmp_path / "empty_raw"
    empty_dir.mkdir()

    # Dem loader fallback
    dem_df = load_dem(raw_dir=empty_dir)
    assert len(dem_df) == 25
    assert "slope" in dem_df.columns

    # Soil moisture loader fallback
    sm_df = load_soil_moisture(raw_dir=empty_dir)
    assert "antecedent_moisture" in sm_df.columns

    # Land use loader fallback
    lu_df = load_land_use(raw_dir=empty_dir)
    assert "ndvi" in lu_df.columns
