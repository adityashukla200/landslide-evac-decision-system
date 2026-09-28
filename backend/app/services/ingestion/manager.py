"""Three-layer data source manager implementing LIVE -> CACHED -> SIMULATED hierarchy."""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import numpy as np
from ml.data.connectors.weather import OpenMeteoConnector
from ml.data.synthetic import SyntheticDataGenerator
from backend.app.services.ingestion.cache import CacheLayer, cache as default_cache

logger = logging.getLogger(__name__)


class DataSourceManager:
    """Manages telemetry ingestion across LIVE, CACHED, and SIMULATED fallback tiers."""

    def __init__(
        self,
        weather_connector: Optional[OpenMeteoConnector] = None,
        cache_backend: Optional[CacheLayer] = None,
        synthetic_generator: Optional[SyntheticDataGenerator] = None,
        cache_ttl_seconds: int = 3600,  # 60 minutes TTL
    ) -> None:
        """Initialize the three-layer data manager."""
        self.weather_connector = weather_connector or OpenMeteoConnector(timeout=5.0, max_retries=3)
        self.cache = cache_backend or default_cache
        self.synthetic_gen = synthetic_generator or SyntheticDataGenerator(seed=42)
        self.cache_ttl = cache_ttl_seconds

        # In-memory status tracking per telemetry source
        self.source_status: Dict[str, Dict[str, Any]] = {
            "weather": {
                "state": "SIMULATED",
                "last_successful_fetch": None,
                "latency_ms": None,
                "error": None,
                "records_fetched": 0,
            },
            "dem": {
                "state": "SIMULATED",
                "last_successful_fetch": None,
                "latency_ms": 0.0,
                "error": None,
            },
            "soil_moisture": {
                "state": "SIMULATED",
                "last_successful_fetch": None,
                "latency_ms": 0.0,
                "error": None,
            },
            "landslide_inventory": {
                "state": "SIMULATED",
                "last_successful_fetch": None,
                "latency_ms": 0.0,
                "error": None,
            },
        }

    def get_village_weather(
        self,
        village_id: str,
        lat: float,
        lon: float,
        elevation: float = 1200.0,
        force_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch weather data for village adhering strictly to LIVE -> CACHED -> SIMULATED order."""
        cache_key = f"weather:{village_id}"

        # 1. Force simulated if requested (for drills/tests)
        if force_source == "SIMULATED":
            return self._generate_simulated_weather(village_id, lat, lon, elevation)

        # 2. Layer 1: Attempt LIVE fetch
        if force_source != "CACHED":
            try:
                start_time = time.perf_counter()
                live_data = self.weather_connector.fetch_village_weather_sync(village_id, lat, lon)
                latency = (time.perf_counter() - start_time) * 1000.0

                # Cache successful response with 60-minute TTL
                live_data["data_source"] = "LIVE"
                self.cache.set(cache_key, live_data, ttl_seconds=self.cache_ttl)

                # Update live status
                self.source_status["weather"]["state"] = "LIVE"
                self.source_status["weather"]["last_successful_fetch"] = datetime.now(timezone.utc).isoformat()
                self.source_status["weather"]["latency_ms"] = round(latency, 2)
                self.source_status["weather"]["error"] = None
                self.source_status["weather"]["records_fetched"] += 1

                return live_data

            except Exception as exc:
                logger.warning(
                    f"[DataSourceManager] Live fetch failed for {village_id}: {exc}. "
                    f"Falling back to CACHED layer."
                )
                self.source_status["weather"]["error"] = str(exc)

        # 3. Layer 2: Check CACHED layer
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            cached_data["data_source"] = "CACHED"
            self.source_status["weather"]["state"] = "CACHED"
            logger.info(f"[DataSourceManager] Returned CACHED weather for {village_id}.")
            return cached_data

        # 4. Layer 3: Fall back to SIMULATED layer
        logger.info(f"[DataSourceManager] Cache empty/expired for {village_id}. Falling back to SIMULATED layer.")
        simulated_data = self._generate_simulated_weather(village_id, lat, lon, elevation)
        self.source_status["weather"]["state"] = "SIMULATED"
        return simulated_data

    def _generate_simulated_weather(
        self,
        village_id: str,
        lat: float,
        lon: float,
        elevation: float,
    ) -> Dict[str, Any]:
        """Generate realistic synthetic weather reading using Prompt 2 physics logic."""
        now = datetime.now(timezone.utc)
        doy = now.timetuple().tm_yday

        # Monsoon seasonality factor
        monsoon_factor = float(np.exp(-0.5 * ((doy - 205.0) / 32.0) ** 2))
        orographic = 1.0 + 0.35 * float(np.exp(-0.5 * ((elevation - 1700.0) / 600.0) ** 2))

        # Synthetic current hour rainfall (mm)
        rng = np.random.default_rng(int(time.time() * 100) % 100000)
        prob = 0.05 + 0.40 * monsoon_factor
        is_raining = rng.random() < prob
        precip = round(float(rng.gamma(shape=1.2, scale=3.5 * orographic)) if is_raining else 0.0, 2)

        # Soil moisture estimate [0.15, 0.95]
        soil_moisture = round(float(np.clip(0.30 + 0.50 * monsoon_factor + (0.15 if is_raining else 0.0), 0.15, 0.95)), 3)

        return {
            "village_id": village_id,
            "latitude": lat,
            "longitude": lon,
            "elevation": elevation,
            "fetch_timestamp": time.time(),
            "latency_ms": 1.5,
            "times": [now.isoformat()],
            "precipitation_mm": [precip],
            "soil_moisture": [soil_moisture],
            "current_precipitation_mm": precip,
            "current_soil_moisture": soil_moisture,
            "data_source": "SIMULATED",  # Strictly never claim simulated data is live
        }

    def get_source_status(self) -> Dict[str, Any]:
        """Return status, state, last successful fetch, and latency for all data sources."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": self.source_status,
        }


# Global singleton manager instance
data_manager = DataSourceManager()
