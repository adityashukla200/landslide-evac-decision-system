"""Asynchronous background scheduler for periodic telemetry ingestion."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.db.models import Village, Sensor, Observation
from backend.app.services.ingestion.manager import data_manager

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """Non-blocking background worker periodically refreshing village weather observations."""

    def __init__(self, interval_seconds: int = 1800) -> None:  # 30 minutes default
        """Initialize scheduler."""
        self.interval_seconds = interval_seconds
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the background ingestion loop."""
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_loop())
            logger.info(f"[IngestionScheduler] Started background worker (interval: {self.interval_seconds}s).")

    def stop(self) -> None:
        """Signal worker to stop and cancel task."""
        if self._task and not self._task.done():
            self._stop_event.set()
            self._task.cancel()
            logger.info("[IngestionScheduler] Stopped background worker.")

    async def _run_loop(self) -> None:
        """Internal asynchronous polling loop."""
        while not self._stop_event.is_set():
            try:
                logger.info("[IngestionScheduler] Starting scheduled telemetry refresh cycle...")
                # Run the ingestion in a separate thread so database and network do not block event loop
                await asyncio.to_thread(self.ingest_once)
                logger.info("[IngestionScheduler] Completed telemetry refresh cycle.")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[IngestionScheduler] Error during ingestion cycle: {exc}", exc_info=True)

            try:
                # Wait for next cycle or cancellation
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    def ingest_once(self) -> int:
        """Execute a single ingestion run across all seeded villages, writing to observations table."""
        db: Session = SessionLocal()
        records_written = 0

        try:
            villages = db.query(Village).all()
            if not villages:
                logger.warning("[IngestionScheduler] No villages found in database to ingest for.")
                return 0

            now = datetime.now(timezone.utc)

            for v in villages:
                try:
                    weather = data_manager.get_village_weather(
                        village_id=v.id,
                        lat=v.lat,
                        lon=v.lon,
                        elevation=v.elevation,
                    )

                    rain_val = weather.get("current_precipitation_mm", 0.0)
                    soil_val = weather.get("current_soil_moisture", 0.40)

                    # Retrieve rain and soil sensors
                    rain_sensor = (
                        db.query(Sensor)
                        .filter_by(village_id=v.id, type="rainfall")
                        .first()
                    )
                    soil_sensor = (
                        db.query(Sensor)
                        .filter_by(village_id=v.id, type="soil_moisture")
                        .first()
                    )

                    if rain_sensor:
                        obs_rain = Observation(
                            time=now,
                            sensor_id=rain_sensor.id,
                            variable="rainfall_rate_mm_hr",
                            value=rain_val,
                        )
                        db.add(obs_rain)
                        rain_sensor.last_seen = now
                        records_written += 1

                    if soil_sensor:
                        obs_soil = Observation(
                            time=now,
                            sensor_id=soil_sensor.id,
                            variable="soil_saturation_ratio",
                            value=soil_val,
                        )
                        db.add(obs_soil)
                        soil_sensor.last_seen = now
                        records_written += 1

                except Exception as v_exc:
                    logger.error(f"[IngestionScheduler] Failed to ingest for village {v.id}: {v_exc}")

            db.commit()
            logger.info(f"[IngestionScheduler] Successfully wrote {records_written} new observations to DB.")
            return records_written

        except Exception as exc:
            db.rollback()
            logger.error(f"[IngestionScheduler] Ingest transaction failed: {exc}")
            return 0
        finally:
            db.close()


# Global scheduler instance
ingestion_scheduler = IngestionScheduler(interval_seconds=1800)
