"""Data loaders with graceful synthetic fallback for offline execution.

Provides robust loaders for:
- Rainfall (GPM IMERG / IMD gridded or synthetic fallback)
- DEM / Topography (SRTM GeoTIFF/CSV or synthetic fallback)
- Soil Moisture (In-situ / Satellite or bucket model fallback)
- Land Use / NDVI (Satellite or synthetic vegetation index fallback)
- Landslide Inventory (Field catalog or synthetic physics-triggered events)
- Feature Table (Pre-computed parquet or dynamic generator)
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.data.synthetic import SyntheticDataGenerator

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"


def load_rainfall(
    raw_dir: Optional[Path] = None,
    villages: Optional[List[Dict[str, Any]]] = None,
    generator: Optional[SyntheticDataGenerator] = None,
) -> pd.DataFrame:
    """Load rainfall telemetry/grids. Tries local raw files first; falls back to synthetic generator."""
    raw_path = raw_dir or (RAW_DATA_DIR / "rainfall")
    if raw_path.exists():
        # Check for local real rainfall dataset (parquet, csv)
        parquet_files = list(raw_path.glob("*.parquet"))
        if parquet_files:
            print(f"[Loader] Loading real rainfall observations from {parquet_files[0]}")
            return pd.read_parquet(parquet_files[0])
        csv_files = list(raw_path.glob("*.csv"))
        if csv_files:
            print(f"[Loader] Loading real rainfall observations from {csv_files[0]}")
            return pd.read_csv(csv_files[0])

    # Synthetic fallback
    print("[Loader] Raw rainfall data not found in /data/raw/rainfall. Falling back to synthetic generator.")
    gen = generator or SyntheticDataGenerator(seed=42)
    v_list = villages or gen.get_or_load_villages()
    return gen.generate_5year_hourly_rainfall(v_list)


def load_dem(
    raw_dir: Optional[Path] = None,
    villages: Optional[List[Dict[str, Any]]] = None,
    generator: Optional[SyntheticDataGenerator] = None,
) -> pd.DataFrame:
    """Load DEM elevation & terrain derivatives. Tries local raw files first; falls back to synthetic."""
    raw_path = raw_dir or (RAW_DATA_DIR / "dem")
    if raw_path.exists():
        csv_files = list(raw_path.glob("*.csv"))
        if csv_files:
            print(f"[Loader] Loading real DEM terrain data from {csv_files[0]}")
            return pd.read_csv(csv_files[0])
        parquet_files = list(raw_path.glob("*.parquet"))
        if parquet_files:
            print(f"[Loader] Loading real DEM terrain data from {parquet_files[0]}")
            return pd.read_parquet(parquet_files[0])

    print("[Loader] Raw DEM data not found in /data/raw/dem. Falling back to synthetic terrain generator.")
    gen = generator or SyntheticDataGenerator(seed=42)
    v_list = villages or gen.get_or_load_villages()
    return gen.generate_terrain_features(v_list)


def load_soil_moisture(
    raw_dir: Optional[Path] = None,
    villages: Optional[List[Dict[str, Any]]] = None,
    generator: Optional[SyntheticDataGenerator] = None,
) -> pd.DataFrame:
    """Load soil moisture time-series. Tries local raw files first; falls back to bucket model."""
    raw_path = raw_dir or (RAW_DATA_DIR / "soil_moisture")
    if raw_path.exists():
        files = list(raw_path.glob("*.csv")) + list(raw_path.glob("*.parquet"))
        if files:
            print(f"[Loader] Loading real soil moisture data from {files[0]}")
            return pd.read_parquet(files[0]) if files[0].suffix == ".parquet" else pd.read_csv(files[0])

    print("[Loader] Raw soil moisture data not found in /data/raw/soil_moisture. Using bucket model fallback.")
    rainfall_df = load_rainfall(raw_dir=raw_dir, villages=villages, generator=generator)
    return rainfall_df[["village_id", "time", "antecedent_moisture"]]


def load_land_use(
    raw_dir: Optional[Path] = None,
    villages: Optional[List[Dict[str, Any]]] = None,
    generator: Optional[SyntheticDataGenerator] = None,
) -> pd.DataFrame:
    """Load land use / NDVI data. Tries local raw files first; falls back to synthetic vegetation index."""
    raw_path = raw_dir or (RAW_DATA_DIR / "land_use")
    if raw_path.exists():
        files = list(raw_path.glob("*.csv")) + list(raw_path.glob("*.parquet"))
        if files:
            print(f"[Loader] Loading real land use / NDVI data from {files[0]}")
            return pd.read_parquet(files[0]) if files[0].suffix == ".parquet" else pd.read_csv(files[0])

    print("[Loader] Raw land use/NDVI not found in /data/raw/land_use. Using synthetic NDVI fallback.")
    terrain_df = load_dem(raw_dir=raw_dir, villages=villages, generator=generator)
    return terrain_df[["village_id", "ndvi"]]


def load_landslide_inventory(
    raw_file: Optional[Path] = None,
    generator: Optional[SyntheticDataGenerator] = None,
) -> pd.DataFrame:
    """Load landslide catalog CSV (lat, lon, date, type). Tries local file first; falls back to synthetic."""
    inv_path = raw_file or (RAW_DATA_DIR / "landslides" / "landslide_inventory.csv")
    if inv_path.exists():
        print(f"[Loader] Loading landslide inventory from {inv_path}")
        df = pd.read_csv(inv_path)
        required_cols = {"lat", "lon", "date", "type"}
        if required_cols.issubset(df.columns):
            return df

    print("[Loader] Real landslide catalog not found. Generating synthetic landslide inventory...")
    gen = generator or SyntheticDataGenerator(seed=42)
    villages = gen.get_or_load_villages()
    terrain_df = gen.generate_terrain_features(villages)
    rainfall_df = gen.generate_5year_hourly_rainfall(villages)
    inventory_df, _ = gen.generate_landslide_inventory_and_feature_table(
        villages, rainfall_df, terrain_df
    )
    # Save to disk for future re-use
    inv_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_df.to_csv(inv_path, index=False)
    return inventory_df


def load_feature_table(
    parquet_path: Optional[Path] = None,
    generator: Optional[SyntheticDataGenerator] = None,
) -> pd.DataFrame:
    """Load processed multi-window feature table parquet. If missing, runs generation pipeline."""
    target_path = parquet_path or (PROCESSED_DATA_DIR / "feature_table.parquet")
    if target_path.exists():
        print(f"[Loader] Loading processed feature table from {target_path}")
        return pd.read_parquet(target_path)

    print(f"[Loader] Feature table {target_path} not found. Running generation pipeline...")
    gen = generator or SyntheticDataGenerator(seed=42)
    villages = gen.get_or_load_villages()
    terrain_df = gen.generate_terrain_features(villages)
    rainfall_df = gen.generate_5year_hourly_rainfall(villages)
    inventory_df, feature_df = gen.generate_landslide_inventory_and_feature_table(
        villages, rainfall_df, terrain_df
    )

    # Persist artifacts
    target_path.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_parquet(target_path, index=False, engine="pyarrow")

    inv_path = RAW_DATA_DIR / "landslides" / "landslide_inventory.csv"
    inv_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_df.to_csv(inv_path, index=False)

    return feature_df
