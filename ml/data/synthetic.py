"""Synthetic data generator for hilly-region flash flood and landslide early warning system.

Generates 5 years of hourly rainfall, bucket-model antecedent soil moisture, static terrain
features, a realistic landslide inventory (~300 events), and a complete multi-window feature table.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.db.models import Village
from scripts.seed_data import seed_database


class SyntheticDataGenerator:
    """Physics-guided synthetic data generator for hydrological and slope failure modeling."""

    def __init__(self, seed: int = 42) -> None:
        """Initialize generator with fixed random seed for deterministic reproducibility."""
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def get_or_load_villages(self) -> List[Dict[str, Any]]:
        """Read 25 pilot villages from database. If DB is unseeded, seed it first."""
        db = SessionLocal()
        try:
            villages = db.query(Village).order_by(Village.id).all()
            if len(villages) < 25:
                print("[*] Less than 25 villages found in DB. Running seed_database()...")
                seed_database()
                villages = db.query(Village).order_by(Village.id).all()

            village_list = [
                {
                    "id": v.id,
                    "name": v.name,
                    "lat": float(v.lat),
                    "lon": float(v.lon),
                    "elevation": float(v.elevation),
                    "population": int(v.population),
                }
                for v in villages
            ]
            return village_list
        finally:
            db.close()

    def generate_terrain_features(self, villages: List[Dict[str, Any]]) -> pd.DataFrame:
        """Compute static terrain features consistent with seeded village elevation and topography."""
        rng = np.random.default_rng(self.seed)
        records = []

        for v in villages:
            elev = v["elevation"]
            # Slope in degrees (14° to 50°): Higher elevations in Uttarkashi have steeper gorge walls
            norm_elev = np.clip((elev - 850.0) / (2800.0 - 850.0), 0.0, 1.0)
            base_slope = 18.0 + 26.0 * norm_elev
            slope = float(np.clip(base_slope + rng.normal(0, 3.5), 14.0, 52.0))

            # Aspect in degrees (0 - 360°)
            aspect = float((int(v["lat"] * 1000 + v["lon"] * 100) % 360))

            # Curvature (-0.05 to +0.05; negative = concave hollow, positive = convex ridge)
            curvature = float(np.clip(rng.normal(-0.005, 0.015), -0.05, 0.05))

            # Upstream Catchment Area (km²): Lower river valleys have larger upstream catchments
            if elev < 1300:
                catchment_area = float(rng.uniform(65.0, 160.0))
            elif elev < 2000:
                catchment_area = float(rng.uniform(25.0, 75.0))
            else:
                catchment_area = float(rng.uniform(4.0, 32.0))

            # Distance to nearest natural stream / drainage channel (meters)
            dist_stream = float(np.clip(rng.exponential(scale=90.0) + 15.0, 10.0, 450.0))

            # Static NDVI (0.20 to 0.78, alpine scrub vs pine/deodar forests)
            ndvi = float(np.clip(0.72 - 0.35 * norm_elev + rng.normal(0, 0.05), 0.18, 0.82))

            records.append({
                "village_id": v["id"],
                "elevation": elev,
                "slope": round(slope, 2),
                "aspect": round(aspect, 1),
                "curvature": round(curvature, 4),
                "upstream_catchment_area": round(catchment_area, 2),
                "distance_to_stream": round(dist_stream, 1),
                "ndvi": round(ndvi, 3),
            })

        return pd.DataFrame(records)

    def generate_full_dataset(
        self,
        villages: List[Dict[str, Any]],
        start_date: str = "2019-01-01 00:00:00",
        end_date: str = "2023-12-31 23:00:00",
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate high-performance 5-year hourly dataset, ~300 landslide events, and feature table."""
        time_index = pd.date_range(start=start_date, end=end_date, freq="1h")
        n_hours = len(time_index)
        doy = time_index.dayofyear.values
        hour = time_index.hour.values

        # Terrain lookup
        terrain_df = self.generate_terrain_features(villages)
        terrain_map = terrain_df.set_index("village_id").to_dict(orient="index")

        # Monsoon Seasonality Envelope (Peak July 24, DOY 205)
        monsoon_factor = np.exp(-0.5 * ((doy - 205.0) / 32.0) ** 2)
        winter_dist = 0.25 * np.exp(-0.5 * (np.minimum(np.abs(doy - 20), np.abs(doy - 380)) / 22.0) ** 2)
        base_rain_prob = 0.03 + 0.35 * monsoon_factor + winter_dist
        diurnal_factor = np.clip(1.0 + 0.4 * np.sin((hour - 10) * np.pi / 12.0), 0.6, 1.4)
        rain_prob = np.clip(base_rain_prob * diurnal_factor, 0.01, 0.65)

        all_village_dfs: List[pd.DataFrame] = []
        all_inventory_events: List[Dict[str, Any]] = []

        total_target_events = 300
        # Allocate events only to villages with steep slopes (slope >= 22.0)
        steep_indices = [idx for idx, v in enumerate(villages) if terrain_map[v["id"]]["slope"] >= 22.0]
        events_per_village = [0] * len(villages)
        # Distribute 300 events evenly across steep villages
        base_per_steep = total_target_events // len(steep_indices)
        remainder = total_target_events % len(steep_indices)
        for i, s_idx in enumerate(steep_indices):
            events_per_village[s_idx] = base_per_steep + (1 if i < remainder else 0)

        for v_idx, v in enumerate(villages):
            v_id = v["id"]
            elev = v["elevation"]
            t_info = terrain_map[v_id]
            slope = t_info["slope"]
            v_rng = np.random.default_rng(self.seed + 1000 + v_idx)

            # Orographic factor
            orographic = 1.0 + 0.35 * np.exp(-0.5 * ((elev - 1700.0) / 600.0) ** 2)

            # Rainfall generation
            rain_mask = v_rng.random(n_hours) < rain_prob
            gamma_scale = (2.8 + 5.5 * monsoon_factor) * orographic
            intensity = v_rng.gamma(shape=1.15, scale=gamma_scale, size=n_hours)
            rainfall = np.where(rain_mask, intensity, 0.0)
            rainfall = np.round(rainfall, 2)

            # Inject 100+ mm / 3h cloudburst extremes
            years = [2019, 2020, 2021, 2022, 2023]
            for yr in years:
                n_bursts = v_rng.integers(1, 3)
                for _ in range(n_bursts):
                    burst_day = v_rng.integers(185, 235)  # July-August
                    burst_h = v_rng.integers(14, 20)
                    matches = np.where((time_index.year == yr) & (time_index.dayofyear == burst_day) & (time_index.hour == burst_h))[0]
                    if len(matches) > 0:
                        idx = matches[0]
                        if idx + 2 < n_hours:
                            rainfall[idx] = round(float(v_rng.uniform(34.0, 48.0)), 2)
                            rainfall[idx + 1] = round(float(v_rng.uniform(48.0, 68.0)), 2)
                            rainfall[idx + 2] = round(float(v_rng.uniform(28.0, 42.0)), 2)

            # Bucket model for antecedent soil moisture
            soil_moist = np.zeros(n_hours, dtype=np.float32)
            s_current = 22.0
            k_drainage = 0.018

            for t in range(n_hours):
                p_t = rainfall[t]
                et_t = 0.0 if p_t > 0.5 else (0.26 * diurnal_factor[t] if monsoon_factor[t] > 0.3 else 0.12)
                s_current = np.clip(s_current + p_t - et_t - (k_drainage * s_current), 5.0, 100.0)
                soil_moist[t] = round(s_current / 100.0, 4)

            # Vectorized rolling cumulative rainfall windows
            r_series = pd.Series(rainfall)
            rain_1h = rainfall
            rain_3h = r_series.rolling(3, min_periods=1).sum().round(2).to_numpy()
            rain_6h = r_series.rolling(6, min_periods=1).sum().round(2).to_numpy()
            rain_24h = r_series.rolling(24, min_periods=1).sum().round(2).to_numpy()
            rain_72h = r_series.rolling(72, min_periods=1).sum().round(2).to_numpy()

            # Landslide Trigger Index
            slope_factor = max((slope - 16.0) / 25.0, 0.1) ** 1.3
            moist_factor = (np.clip(soil_moist / 0.65, 0.1, 1.5)) ** 1.8
            rain_term = (np.maximum(rain_3h - 22.0, 0.0) / 30.0) + (np.maximum(rain_24h - 55.0, 0.0) / 60.0)
            trigger_score = rain_term * moist_factor * slope_factor

            # Find top candidate peaks with minimum 48h separation
            num_events_v = events_per_village[v_idx]
            candidate_indices = np.argsort(trigger_score)[::-1]
            selected_h_indices = []

            for cand_h in candidate_indices:
                if len(selected_h_indices) >= num_events_v:
                    break
                if trigger_score[cand_h] < 0.2:
                    break
                # Ensure 48h separation
                if all(abs(cand_h - existing) >= 48 for existing in selected_h_indices):
                    selected_h_indices.append(cand_h)

            # Event label array (landslide_within_6h: 1 if landslide occurs in [t+1, t+6])
            landslide_label = np.zeros(n_hours, dtype=np.int8)

            for ev_h in selected_h_indices:
                ev_time = time_index[ev_h]
                offset_lat = float(v_rng.normal(0, 0.003))
                offset_lon = float(v_rng.normal(0, 0.003))

                # Event type classification
                if rain_3h[ev_h] > 60.0:
                    ev_type = "debris_flow"
                elif slope > 38.0:
                    ev_type = "rockfall"
                elif soil_moist[ev_h] > 0.85:
                    ev_type = "shallow_translational"
                else:
                    ev_type = "mudslide"

                all_inventory_events.append({
                    "village_id": v_id,
                    "lat": round(v["lat"] + offset_lat, 5),
                    "lon": round(v["lon"] + offset_lon, 5),
                    "date": ev_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "type": ev_type,
                    "rain_3h_at_failure": float(rain_3h[ev_h]),
                    "rain_24h_at_failure": float(rain_24h[ev_h]),
                    "soil_moisture_at_failure": float(soil_moist[ev_h]),
                    "slope_deg": float(slope),
                })

                # Mark [ev_h - 6 : ev_h] as 1 (ev_h occurs within the next 1 to 6 hours)
                lead_start = max(0, ev_h - 6)
                landslide_label[lead_start:ev_h] = 1

            # Assemble DataFrame for this village
            v_df = pd.DataFrame({
                "village_id": v_id,
                "time": time_index,
                "rain_1h": rain_1h,
                "rain_3h": rain_3h,
                "rain_6h": rain_6h,
                "rain_24h": rain_24h,
                "rain_72h": rain_72h,
                "antecedent_moisture": soil_moist,
                "elevation": t_info["elevation"],
                "slope": t_info["slope"],
                "aspect": t_info["aspect"],
                "curvature": t_info["curvature"],
                "upstream_catchment_area": t_info["upstream_catchment_area"],
                "distance_to_stream": t_info["distance_to_stream"],
                "ndvi": t_info["ndvi"],
                "landslide_within_6h": landslide_label,
            })
            all_village_dfs.append(v_df)

        inventory_df = pd.DataFrame(all_inventory_events)
        feature_df = pd.concat(all_village_dfs, ignore_index=True)

        return inventory_df, feature_df

    def generate_5year_hourly_rainfall(
        self,
        villages: List[Dict[str, Any]],
        start_date: str = "2019-01-01 00:00:00",
        end_date: str = "2023-12-31 23:00:00",
    ) -> pd.DataFrame:
        """Convenience method generating 5 years of hourly rainfall and antecedent moisture."""
        _, feature_df = self.generate_full_dataset(villages, start_date=start_date, end_date=end_date)
        res = feature_df[["village_id", "time", "rain_1h", "antecedent_moisture"]].copy()
        res.rename(columns={"rain_1h": "rainfall"}, inplace=True)
        return res


def run_pipeline() -> Tuple[Path, Path]:
    """Execute synthetic data pipeline and write artifacts to disk."""
    generator = SyntheticDataGenerator(seed=42)
    villages = generator.get_or_load_villages()

    print(f"[*] Loaded {len(villages)} villages from database.")
    inventory_df, feature_df = generator.generate_full_dataset(villages)

    # Save landslide inventory CSV
    raw_inv_dir = Path("data/raw/landslides")
    raw_inv_dir.mkdir(parents=True, exist_ok=True)
    inv_path = raw_inv_dir / "landslide_inventory.csv"
    inventory_df.to_csv(inv_path, index=False)
    print(f"[+] Saved landslide inventory ({len(inventory_df)} events) to {inv_path}")

    # Save feature table parquet
    proc_dir = Path("data/processed")
    proc_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = proc_dir / "feature_table.parquet"
    feature_df.to_parquet(parquet_path, index=False, engine="pyarrow")
    pos_rate = feature_df["landslide_within_6h"].mean()
    print(f"[+] Saved feature table ({len(feature_df):,} rows, positive label rate: {pos_rate:.4%}) to {parquet_path}")

    return inv_path, parquet_path


if __name__ == "__main__":
    run_pipeline()
