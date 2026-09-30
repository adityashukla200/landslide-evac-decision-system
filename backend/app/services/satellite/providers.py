"""Satellite Remote Sensing and Cloudburst Nowcasting Providers.

Simulates and ingests high-cadence satellite observation streams:
1. Sentinel-1 SAR: Interferometric coherence loss & ground deformation velocity (InSAR mm/yr)
2. Sentinel-2 Optical: Modified Normalized Difference Water Index (MNDWI) surface water expansion
3. NASA GPM IMERG: Half-hourly calibrated precipitation nowcast (mm/h)
4. INSAT-3D/3DR: Thermal Infrared (TIR) rapid-scan cloud-top cooling rate (dT_b / dt < -15K/15min)
5. SatelliteRiskFusionEngine: Fuses ground sensors + satellite data into an updated threat score
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.db.models import Village, SatelliteObservation, RiskAssessment

logger = logging.getLogger(__name__)


class SatelliteObsResult(dict):
    """Result dictionary with attribute-style dot access for satellite readings."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class Sentinel1SARProvider:
    """Sentinel-1 C-band Synthetic Aperture Radar (SAR) and InSAR deformation service."""

    @classmethod
    def fetch_observation(cls, village_id: str, lat: float = 31.0, lon: float = 78.7) -> SatelliteObsResult:
        return SatelliteObsResult({
            "sensor": "SENTINEL-1-SAR",
            "coherence_loss": 0.42,
            "deformation_rate_mm_year": -32.5,
            "timestamp": datetime.now(timezone.utc),
        })


    @staticmethod
    def get_village_deformation(village: Village, now: datetime) -> Dict[str, Any]:
        """Compute InSAR phase coherence and line-of-sight (LOS) ground displacement.
        
        Villages with steep slope profiles and high historical landslide frequency
        (e.g., Bhatwari, Maneri, Gangnani) experience higher creeping deformation rates.
        """
        elev = village.elevation
        lat = village.lat

        # Deterministic simulation anchored to real village slope topography
        high_risk_anchor = elev > 1400 and lat > 30.75
        base_coherence_loss = 0.58 if high_risk_anchor else 0.18
        displacement_rate_mm_yr = -45.0 if high_risk_anchor else -6.2  # negative = subsidence / downslope creep

        return {
            "satellite": "SENTINEL_1",
            "band": "C-band (5.405 GHz)",
            "coherence_loss": round(base_coherence_loss, 3),
            "los_displacement_mm_yr": round(displacement_rate_mm_yr, 2),
            "sar_backscatter_drop_db": round(-3.8 if high_risk_anchor else -0.5, 2),
            "deformation_anomaly_detected": high_risk_anchor,
            "pass_type": "DESCENDING_ORBIT_136",
            "last_acquisition": (now - timedelta(hours=3)).isoformat(),
        }


class Sentinel2OpticalProvider:
    """Sentinel-2 MSI Optical Surface Water and Landslide Scar service."""

    @classmethod
    def fetch_observation(cls, village_id: str, lat: float = 31.0, lon: float = 78.7) -> SatelliteObsResult:
        return SatelliteObsResult({
            "sensor": "SENTINEL-2-MSI",
            "ndwi": 0.35,
            "mndwi": 0.48,
            "cloud_cover_pct": 14.5,
            "timestamp": datetime.now(timezone.utc),
        })

    @staticmethod
    def get_village_optical_indices(village: Village, now: datetime) -> Dict[str, Any]:
        """Compute Normalized Difference Water Index (NDWI) and bare scar detection."""
        elev = village.elevation
        water_extent_ha = round(18.5 + (elev / 250.0), 2)
        scar_area_ha = round(4.2 if elev > 1500 else 0.8, 2)

        return {
            "satellite": "SENTINEL_2",
            "sensor": "MSI (13 spectral bands)",
            "mndwi_surface_water_ha": water_extent_ha,
            "landslide_scar_extent_ha": scar_area_ha,
            "cloud_cover_pct": 28.5,
            "water_body_expanded_vs_baseline_pct": 34.0 if elev > 1200 else 5.0,
            "last_acquisition": (now - timedelta(hours=6)).isoformat(),
        }


class NASAGPMNowcastProvider:
    """NASA Global Precipitation Measurement (GPM) IMERG Half-Hourly Precipitation."""

    @classmethod
    def fetch_observation(cls, village_id: str, lat: float = 31.0, lon: float = 78.7) -> SatelliteObsResult:
        return SatelliteObsResult({
            "sensor": "NASA-GPM-IMERG",
            "rainfall_rate_mm_hr": 24.5,
            "accumulation_3h_mm": 52.0,
            "timestamp": datetime.now(timezone.utc),
        })

    @staticmethod
    def get_precipitation_nowcast(village: Village, now: datetime) -> Dict[str, Any]:
        lat = village.lat
        elevation_factor = max(1.0, village.elevation / 1000.0)
        instantaneous_rate = round(14.5 * (1.0 + (lat - 30.7) * 4.0) * (elevation_factor * 0.7), 2)
        instantaneous_rate = max(2.0, min(85.0, instantaneous_rate))
        acc_3h = round(instantaneous_rate * 2.4, 2)

        return {
            "satellite": "NASA_GPM_IMERG",
            "product": "IMERG_Early_Run_v07B",
            "instantaneous_rain_rate_mm_h": instantaneous_rate,
            "accumulated_3h_rainfall_mm": acc_3h,
            "convective_storm_cell_present": instantaneous_rate > 30.0,
            "spatial_resolution": "0.1 deg x 0.1 deg (~10km)",
            "nowcast_valid_time": now.isoformat(),
        }


class INSAT3DCloudburstProvider:
    """ISRO INSAT-3D/3DR Rapid-Scan Cloudburst Precursor Monitoring."""

    @classmethod
    def fetch_observation(cls, village_id: str, lat: float = 31.0, lon: float = 78.7, simulated_cooling_k: float = -8.0) -> SatelliteObsResult:
        is_cloudburst = simulated_cooling_k < -15.0
        return SatelliteObsResult({
            "sensor": "INSAT-3D-RAPID",
            "cloud_top_cooling_rate_k_15min": simulated_cooling_k,
            "cloudburst_risk": is_cloudburst,
            "timestamp": datetime.now(timezone.utc),
        })

    @staticmethod
    def detect_cloudburst_precursor(village: Village, now: datetime) -> Dict[str, Any]:
        elev = village.elevation
        is_cloudburst_risk = elev > 1350 and village.lat > 30.78
        cooling_rate = -19.4 if is_cloudburst_risk else -4.2
        brightness_temp_c = -72.0 if is_cloudburst_risk else -38.0

        return {
            "satellite": "INSAT_3D_ISRO",
            "sensor": "Imager TIR-1 (10.8 um)",
            "cloud_cooling_rate_k_15min": round(cooling_rate, 2),
            "cloud_top_temperature_celsius": round(brightness_temp_c, 1),
            "explosive_convective_updraft": is_cloudburst_risk,
            "cloudburst_precursor_warning": is_cloudburst_risk,
            "cloudburst_probability": 0.88 if is_cloudburst_risk else 0.12,
            "lead_time_to_ground_impact_minutes": 25 if is_cloudburst_risk else 120,
            "rapid_scan_cadence_minutes": 15,
            "timestamp": now.isoformat(),
        }


class SatelliteRiskFusionEngine:
    """Fuses multi-source satellite products with ground telemetry into calibrated risk."""

    @classmethod
    def fuse_village_satellite_risk(cls, village_id: str, lat: float = 31.0, lon: float = 78.7, current_risk: float = 0.4) -> Dict[str, Any]:
        delta_risk = 0.22
        fused = min(1.0, round(current_risk + delta_risk, 3))
        return {
            "village_id": village_id,
            "fused_risk_score": fused,
            "delta_risk": delta_risk,
            "threat_level": "WARNING" if fused > 0.6 else "WATCH",
            "contributing_sensors": ["SENTINEL-1-SAR", "SENTINEL-2-MSI", "NASA-GPM-IMERG", "INSAT-3D-RAPID"],
        }


    @classmethod
    def compute_village_fused_risk(cls, village: Village, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Synthesize all satellite observation channels and calculate risk boost factor."""
        now = now or datetime.now(timezone.utc)

        sar = Sentinel1SARProvider.get_village_deformation(village, now)
        optical = Sentinel2OpticalProvider.get_village_optical_indices(village, now)
        gpm = NASAGPMNowcastProvider.get_precipitation_nowcast(village, now)
        insat = INSAT3DCloudburstProvider.detect_cloudburst_precursor(village, now)

        # Weighting factors
        # 1. INSAT Cloudburst Updraft: +0.25 threat bump
        insat_boost = 0.25 if insat["cloudburst_precursor_warning"] else 0.0
        # 2. GPM Heavy Rain: +0.15 threat bump if > 35mm/h
        gpm_boost = 0.15 if gpm["instantaneous_rain_rate_mm_h"] > 35.0 else (0.08 if gpm["instantaneous_rain_rate_mm_h"] > 20.0 else 0.0)
        # 3. Sentinel-1 InSAR Deformation: +0.10 threat bump if coherence loss > 0.5
        sar_boost = 0.10 if sar["coherence_loss"] > 0.50 else 0.0

        net_boost = round(insat_boost + gpm_boost + sar_boost, 3)

        if net_boost >= 0.35:
            threat_level = "CRITICAL"
        elif net_boost >= 0.20:
            threat_level = "HIGH"
        elif net_boost >= 0.08:
            threat_level = "ELEVATED"
        else:
            threat_level = "NORMAL"

        return {
            "village_id": village.id,
            "village_name": village.name,
            "insat_cloud_cooling_rate_k_15m": insat["cloud_cooling_rate_k_15min"],
            "insat_cloudburst_probability": insat["cloudburst_probability"],
            "gpm_rain_rate_mm_h": gpm["instantaneous_rain_rate_mm_h"],
            "gpm_3h_accumulation_mm": gpm["accumulated_3h_rainfall_mm"],
            "sentinel1_coherence_loss": sar["coherence_loss"],
            "sentinel1_displacement_rate_mm_yr": sar["los_displacement_mm_yr"],
            "sentinel2_mndwi_surface_water_ha": optical["mndwi_surface_water_ha"],
            "risk_boost_factor": net_boost,
            "threat_level": threat_level,
            "satellite_sources": ["SENTINEL_1", "SENTINEL_2", "NASA_GPM", "INSAT_3D"],
            "updated_at": now,
        }

    @classmethod
    def apply_risk_fusion_to_all(cls, db: Session) -> List[Dict[str, Any]]:
        """Recalculate satellite fusion boost across all villages in database."""
        villages = db.query(Village).all()
        results = []
        now = datetime.now(timezone.utc)

        for v in villages:
            fused = cls.compute_village_fused_risk(v, now)
            results.append(fused)

            # Record in satellite_observations table for operational audit
            obs = SatelliteObservation(
                id=f"sat_{v.id}_{int(now.timestamp())}",
                satellite_source="MULTI_FUSED",
                acquisition_time=now,
                product_type="MULTI_LAYER_FUSION",
                village_id=v.id,
                bbox_geojson=f'{{"type":"Point","coordinates":[{v.lon},{v.lat}]}}',
                metrics=fused,
                risk_score_boost=fused["risk_boost_factor"],
                created_at=now,
            )
            db.add(obs)

        db.commit()
        return results
