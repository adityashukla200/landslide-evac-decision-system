"""Public bridge: backend.services.sensors → backend.app.services.sensors"""
from backend.app.services.sensors import (
    SensorSimulator,
    VILLAGE_REGISTRY,
    SensorTrustLayer,
    SensorReading,
    TrustResult,
    VirtualSensorInterpolator,
)

__all__ = [
    "SensorSimulator",
    "VILLAGE_REGISTRY",
    "SensorTrustLayer",
    "SensorReading",
    "TrustResult",
    "VirtualSensorInterpolator",
]
