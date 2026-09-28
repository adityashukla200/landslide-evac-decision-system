"""Sensor subsystem: MQTT simulator, trust layer, virtual interpolation."""
from .simulator import SensorSimulator, VILLAGE_REGISTRY
from .trust import SensorTrustLayer, SensorReading, TrustResult
from .virtual import VirtualSensorInterpolator

__all__ = [
    "SensorSimulator",
    "VILLAGE_REGISTRY",
    "SensorTrustLayer",
    "SensorReading",
    "TrustResult",
    "VirtualSensorInterpolator",
]
