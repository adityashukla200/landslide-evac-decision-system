"""Geotechnical Monte Carlo scenario generator for physics-guided synthetic pretraining.

Samples thousands of combinations of slope, geotechnical parameters, and rainfall infiltration,
injects parameter uncertainty and geotechnical noise, and outputs a labeled dataset (>= 100,000 rows)
to /data/processed/physics_synthetic.parquet.
"""

import sys
from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.physics.slope_stability import compute_infinite_slope_fs

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_PARQUET = ROOT_DIR / "data" / "processed" / "physics_synthetic.parquet"


def generate_physics_scenarios(
    n_samples: int = 120_000,
    seed: int = 42,
    porosity: float = 0.38,
    noise_std: float = 0.08,
) -> pd.DataFrame:
    """Generate Monte Carlo geotechnical scenarios with realistic Himalayan parameter distributions."""
    rng = np.random.default_rng(seed)

    print(f"[*] Generating {n_samples:,} physics-simulated slope stability scenarios (seed={seed})...")

    # 1. Slope angle (degrees): Himalayan hillslopes (12° valley margins to 55° rockwalls)
    slope_deg = rng.uniform(12.0, 54.0, size=n_samples)

    # 2. Effective Soil Cohesion c' (kPa): Colluvium / weathered schist / quartzite debris
    # Log-normal distribution centered around 12 kPa
    cohesion_kpa = np.clip(rng.lognormal(mean=2.45, sigma=0.45, size=n_samples), 2.5, 30.0)

    # 3. Effective Friction Angle phi' (degrees): Typically 22° to 44° for granular Himalayan regolith
    friction_angle_deg = np.clip(rng.normal(loc=33.0, scale=4.0, size=n_samples), 20.0, 44.0)

    # 4. Soil Mantle Depth z (meters): Colluvial regolith thickness
    soil_depth_m = np.clip(rng.gamma(shape=3.5, scale=0.5, size=n_samples), 0.6, 3.8)

    # 5. Cumulative Rainfall P (mm): 0 to 260 mm (including dry spells and cloudbursts)
    # Mixture: 70% moderate rainfall (0-80mm), 30% intense rainfall (80-260mm)
    is_intense = rng.random(size=n_samples) < 0.30
    rain_moderate = rng.exponential(scale=25.0, size=n_samples)
    rain_intense = rng.uniform(70.0, 250.0, size=n_samples)
    rainfall_mm = np.where(is_intense, rain_intense, rain_moderate)
    rainfall_mm = np.clip(rainfall_mm, 0.0, 260.0)

    # 6. Antecedent Soil Moisture m0: [0.10, 0.90]
    antecedent_moisture = rng.uniform(0.12, 0.88, size=n_samples)

    # 7. Infiltration & Saturation ratio m
    soil_capacity_mm = soil_depth_m * porosity * 1000.0
    added_sat = rainfall_mm / soil_capacity_mm
    saturation_ratio = np.clip(antecedent_moisture + added_sat, 0.0, 1.0)

    # 8. Deterministic Factor of Safety
    fs_deterministic = compute_infinite_slope_fs(
        slope_deg=slope_deg,
        cohesion_kpa=cohesion_kpa,
        friction_angle_deg=friction_angle_deg,
        soil_depth_m=soil_depth_m,
        saturation_ratio=saturation_ratio,
        gamma_kn_m3=18.5,
        gamma_w_kn_m3=9.81,
    )

    # 9. Parameter uncertainty and spatial heterogeneity noise
    # Simulates localized root reinforcement variations, micro-fractures, and transient pore pressure spikes
    relative_noise = rng.normal(loc=0.0, scale=noise_std, size=n_samples)
    fs_noisy = np.maximum(fs_deterministic * (1.0 + relative_noise), 0.05)

    # 10. Labels: Failed (FS < 1.0) vs Stable (FS >= 1.0)
    failed = (fs_noisy < 1.0).astype(np.int8)

    df = pd.DataFrame({
        "slope_deg": np.round(slope_deg, 2),
        "cohesion_kpa": np.round(cohesion_kpa, 2),
        "friction_angle_deg": np.round(friction_angle_deg, 2),
        "soil_depth_m": np.round(soil_depth_m, 2),
        "rainfall_mm": np.round(rainfall_mm, 2),
        "antecedent_moisture": np.round(antecedent_moisture, 3),
        "saturation_ratio": np.round(saturation_ratio, 3),
        "fs_deterministic": np.round(fs_deterministic, 3),
        "fs_noisy": np.round(fs_noisy, 3),
        "failed": failed,
    })

    failure_rate = df["failed"].mean()
    print(f"[+] Successfully generated {len(df):,} scenarios. Failure rate: {failure_rate:.2%}")
    return df


def save_physics_dataset(output_path: Path = OUTPUT_PARQUET, n_samples: int = 120_000) -> Path:
    """Generate and persist >= 100,000 synthetic physics scenarios to parquet."""
    df = generate_physics_scenarios(n_samples=n_samples, seed=42)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, engine="pyarrow")
    print(f"[+] Saved {len(df):,} physics scenarios to {output_path}")
    return output_path


if __name__ == "__main__":
    save_physics_dataset()
