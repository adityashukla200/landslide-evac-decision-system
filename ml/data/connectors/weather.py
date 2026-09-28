"""Open-Meteo live weather connector for hourly rainfall forecast and antecedent soil moisture.

Connects to the Open-Meteo public API (no key required), fetches 7-day historical + forecast
precipitation and soil moisture, with 5s timeouts, exponential backoff retries, and rate limit handling.
"""

import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class OpenMeteoConnector:
    """Live weather telemetry and forecast connector using Open-Meteo API."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        timeout: float = 5.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        """Initialize Open-Meteo connector with retry and timeout configuration."""
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def fetch_village_weather_sync(
        self,
        village_id: str,
        lat: float,
        lon: float,
        client: Optional[httpx.Client] = None,
    ) -> Dict[str, Any]:
        """Synchronously fetch weather data for a single village with retries and exponential backoff."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,soil_moisture_0_to_1cm",
            "past_days": 7,
            "forecast_days": 2,
            "timezone": "UTC",
        }

        should_close = False
        if client is None:
            client = httpx.Client(timeout=self.timeout)
            should_close = True

        start_time = time.perf_counter()
        last_error: Optional[Exception] = None

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = client.get(self.BASE_URL, params=params)

                    # Handle Rate Limiting (HTTP 429)
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else (self.backoff_factor * (2 ** (attempt - 1)))
                        logger.warning(
                            f"[OpenMeteo] Rate limited (429) for village {village_id}. "
                            f"Retrying in {delay:.2f}s (Attempt {attempt}/{self.max_retries})"
                        )
                        if attempt < self.max_retries:
                            time.sleep(delay)
                            continue
                        response.raise_for_status()

                    response.raise_for_status()
                    data = response.json()
                    latency_ms = (time.perf_counter() - start_time) * 1000.0

                    return self._parse_response(village_id, data, latency_ms)

                except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                    last_error = exc
                    delay = self.backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        f"[OpenMeteo] Attempt {attempt}/{self.max_retries} failed for village {village_id}: {exc}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    if attempt < self.max_retries:
                        time.sleep(delay)

            raise RuntimeError(
                f"Failed to fetch live weather from Open-Meteo for village {village_id} "
                f"after {self.max_retries} attempts: {last_error}"
            )

        finally:
            if should_close:
                client.close()

    async def fetch_village_weather_async(
        self,
        village_id: str,
        lat: float,
        lon: float,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:
        """Asynchronously fetch weather data for a single village with retries and exponential backoff."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,soil_moisture_0_to_1cm",
            "past_days": 7,
            "forecast_days": 2,
            "timezone": "UTC",
        }

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            should_close = True

        start_time = time.perf_counter()
        last_error: Optional[Exception] = None

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.get(self.BASE_URL, params=params)

                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else (self.backoff_factor * (2 ** (attempt - 1)))
                        logger.warning(
                            f"[OpenMeteo Async] Rate limited (429) for village {village_id}. "
                            f"Retrying in {delay:.2f}s (Attempt {attempt}/{self.max_retries})"
                        )
                        if attempt < self.max_retries:
                            await asyncio.sleep(delay)
                            continue
                        response.raise_for_status()

                    response.raise_for_status()
                    data = response.json()
                    latency_ms = (time.perf_counter() - start_time) * 1000.0

                    return self._parse_response(village_id, data, latency_ms)

                except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                    last_error = exc
                    delay = self.backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        f"[OpenMeteo Async] Attempt {attempt}/{self.max_retries} failed for village {village_id}: {exc}."
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(delay)

            raise RuntimeError(
                f"Failed to fetch live weather from Open-Meteo for village {village_id} "
                f"after {self.max_retries} attempts: {last_error}"
            )

        finally:
            if should_close:
                await client.aclose()

    async def fetch_batch_weather_async(
        self,
        villages: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fetch weather data for multiple villages concurrently with bounded concurrency."""
        semaphore = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async def _fetch(v: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    return await self.fetch_village_weather_async(
                        v["id"], v["lat"], v["lon"], client=client
                    )

            tasks = [_fetch(v) for v in villages]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = []
            for v, res in zip(villages, results):
                if isinstance(res, Exception):
                    logger.error(f"[OpenMeteo Batch] Error fetching for {v['id']}: {res}")
                    raise res
                valid_results.append(res)
            return valid_results

    def _parse_response(
        self,
        village_id: str,
        data: Dict[str, Any],
        latency_ms: float,
    ) -> Dict[str, Any]:
        """Validate and parse raw Open-Meteo response into unified schema."""
        if "hourly" not in data or "time" not in data["hourly"]:
            raise ValueError(f"Malformed Open-Meteo response: missing 'hourly' section in {data}")

        hourly = data["hourly"]
        times = hourly.get("time", [])
        precip = hourly.get("precipitation", [])
        soil_m = hourly.get("soil_moisture_0_to_1cm", [])

        if not times or not precip:
            raise ValueError("Malformed Open-Meteo response: empty precipitation series")

        # Current reading (closest to now or last historical hour)
        current_precip = float(precip[-1] if precip else 0.0)
        current_soil = float(soil_m[-1] if soil_m and soil_m[-1] is not None else 0.45)

        return {
            "village_id": village_id,
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "elevation": data.get("elevation"),
            "fetch_timestamp": time.time(),
            "latency_ms": round(latency_ms, 2),
            "times": times,
            "precipitation_mm": precip,
            "soil_moisture": soil_m,
            "current_precipitation_mm": current_precip,
            "current_soil_moisture": current_soil,
            "data_source": "LIVE",
        }
