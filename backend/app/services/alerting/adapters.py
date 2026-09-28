"""Multi-channel alert delivery adapters with unified async interface and simulated failure/latency modeling."""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

from backend.app.db.models import Alert, Recipient


class DeliveryResult(BaseModel):
    """Result of an alert delivery attempt."""

    success: bool
    delivery_id: str
    channel: str
    recipient_id: str
    status: str  # SENT, FAILED
    latency_ms: float
    error: Optional[str] = None
    simulated: bool = True
    details: Dict[str, Any] = {}


class BaseChannelAdapter(ABC):
    """Abstract base class for all emergency communication channel adapters."""

    def __init__(self, failure_rate: float = 0.0, base_latency_ms: float = 100.0) -> None:
        self.failure_rate = failure_rate
        self.base_latency_ms = base_latency_ms

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Channel identifier string."""
        pass

    @abstractmethod
    async def send(
        self,
        recipient: Recipient,
        alert: Alert,
        message_text: str,
        delivery_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DeliveryResult:
        """Dispatch alert payload to recipient over channel."""
        pass


class CellBroadcastMock(BaseChannelAdapter):
    """Simulates geo-fenced cell tower cellular broadcast (instantaneous tower flood)."""

    def __init__(self, failure_rate: float = 0.03, base_latency_ms: float = 80.0) -> None:
        super().__init__(failure_rate=failure_rate, base_latency_ms=base_latency_ms)

    @property
    def channel_name(self) -> str:
        return "CELL_BROADCAST"

    async def send(
        self,
        recipient: Recipient,
        alert: Alert,
        message_text: str,
        delivery_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DeliveryResult:
        t0 = time.perf_counter()
        # Simulate quick tower broadcast propagation
        simulated_delay = random.uniform(0.02, 0.09)
        await asyncio.sleep(simulated_delay)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        did_fail = random.random() < self.failure_rate
        did_id = delivery_id or f"DEL_CB_{alert.id}_{recipient.id}"

        if did_fail:
            return DeliveryResult(
                success=False,
                delivery_id=did_id,
                channel=self.channel_name,
                recipient_id=recipient.id,
                status="FAILED",
                latency_ms=latency_ms,
                error="Cell tower base-station congestion or RF shadowing in mountain gorge.",
            )

        return DeliveryResult(
            success=True,
            delivery_id=did_id,
            channel=self.channel_name,
            recipient_id=recipient.id,
            status="SENT",
            latency_ms=latency_ms,
            details={"broadcast_area": alert.village_id, "bts_cluster": "BTS_UTK_HIGH_POWER"},
        )


class SMSMock(BaseChannelAdapter):
    """Simulates telecom SMS gateway delivery."""

    def __init__(self, failure_rate: float = 0.05, base_latency_ms: float = 250.0) -> None:
        super().__init__(failure_rate=failure_rate, base_latency_ms=base_latency_ms)

    @property
    def channel_name(self) -> str:
        return "SMS"

    async def send(
        self,
        recipient: Recipient,
        alert: Alert,
        message_text: str,
        delivery_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DeliveryResult:
        t0 = time.perf_counter()
        simulated_delay = random.uniform(0.05, 0.20)
        await asyncio.sleep(simulated_delay)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        did_fail = random.random() < self.failure_rate
        did_id = delivery_id or f"DEL_SMS_{alert.id}_{recipient.id}"

        if did_fail:
            return DeliveryResult(
                success=False,
                delivery_id=did_id,
                channel=self.channel_name,
                recipient_id=recipient.id,
                status="FAILED",
                latency_ms=latency_ms,
                error="SMSC timeout or subscriber out of coverage.",
            )

        return DeliveryResult(
            success=True,
            delivery_id=did_id,
            channel=self.channel_name,
            recipient_id=recipient.id,
            status="SENT",
            latency_ms=latency_ms,
            details={"phone": recipient.phone, "char_count": len(message_text)},
        )


class WhatsAppMock(BaseChannelAdapter):
    """Simulates WhatsApp Business API template dispatch with read-receipt capability."""

    def __init__(self, failure_rate: float = 0.04, base_latency_ms: float = 150.0) -> None:
        super().__init__(failure_rate=failure_rate, base_latency_ms=base_latency_ms)

    @property
    def channel_name(self) -> str:
        return "WHATSAPP"

    async def send(
        self,
        recipient: Recipient,
        alert: Alert,
        message_text: str,
        delivery_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DeliveryResult:
        t0 = time.perf_counter()
        await asyncio.sleep(random.uniform(0.04, 0.15))
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        did_fail = random.random() < self.failure_rate
        did_id = delivery_id or f"DEL_WA_{alert.id}_{recipient.id}"

        if did_fail:
            return DeliveryResult(
                success=False,
                delivery_id=did_id,
                channel=self.channel_name,
                recipient_id=recipient.id,
                status="FAILED",
                latency_ms=latency_ms,
                error="Data connectivity unavailable or unverified recipient number.",
            )

        return DeliveryResult(
            success=True,
            delivery_id=did_id,
            channel=self.channel_name,
            recipient_id=recipient.id,
            status="SENT",
            latency_ms=latency_ms,
            details={"phone": recipient.phone, "template": "emergency_evacuation_v1"},
        )


class IVRMock(BaseChannelAdapter):
    """Simulates automated interactive voice response (IVR) phone call with audio synthesis."""

    def __init__(self, failure_rate: float = 0.06, base_latency_ms: float = 400.0) -> None:
        super().__init__(failure_rate=failure_rate, base_latency_ms=base_latency_ms)

    @property
    def channel_name(self) -> str:
        return "IVR"

    async def send(
        self,
        recipient: Recipient,
        alert: Alert,
        message_text: str,
        delivery_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DeliveryResult:
        t0 = time.perf_counter()
        await asyncio.sleep(random.uniform(0.08, 0.25))
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        did_fail = random.random() < self.failure_rate
        did_id = delivery_id or f"DEL_IVR_{alert.id}_{recipient.id}"

        if did_fail:
            return DeliveryResult(
                success=False,
                delivery_id=did_id,
                channel=self.channel_name,
                recipient_id=recipient.id,
                status="FAILED",
                latency_ms=latency_ms,
                error="Call rejected, line busy, or no answer after ring timeout.",
            )

        return DeliveryResult(
            success=True,
            delivery_id=did_id,
            channel=self.channel_name,
            recipient_id=recipient.id,
            status="SENT",
            latency_ms=latency_ms,
            details={"phone": recipient.phone, "audio_prompt": "tts_hindi_urgent_evac", "dtmf_prompt": "press_1_to_ack"},
        )


class VolunteerTaskAdapter(BaseChannelAdapter):
    """Dispatches high-urgency task card push to registered community volunteer for physical door-to-door assist."""

    def __init__(self, failure_rate: float = 0.02, base_latency_ms: float = 120.0) -> None:
        super().__init__(failure_rate=failure_rate, base_latency_ms=base_latency_ms)

    @property
    def channel_name(self) -> str:
        return "VOLUNTEER"

    async def send(
        self,
        recipient: Recipient,
        alert: Alert,
        message_text: str,
        delivery_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DeliveryResult:
        t0 = time.perf_counter()
        await asyncio.sleep(random.uniform(0.03, 0.10))
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        did_fail = random.random() < self.failure_rate
        did_id = delivery_id or f"DEL_VOL_{alert.id}_{recipient.id}"

        if did_fail:
            return DeliveryResult(
                success=False,
                delivery_id=did_id,
                channel=self.channel_name,
                recipient_id=recipient.id,
                status="FAILED",
                latency_ms=latency_ms,
                error="Assigned volunteer unreachable or offline.",
            )

        return DeliveryResult(
            success=True,
            delivery_id=did_id,
            channel=self.channel_name,
            recipient_id=recipient.id,
            status="SENT",
            latency_ms=latency_ms,
            details={
                "volunteer_id": recipient.volunteer_id or "VOL_GENERAL",
                "assigned_resident": recipient.id,
                "dispatch_mode": "DOOR_TO_DOOR_ASSIST",
            },
        )


class SirenMock(BaseChannelAdapter):
    """Simulates remote acoustic siren tower trigger in village square."""

    def __init__(self, failure_rate: float = 0.01, base_latency_ms: float = 50.0) -> None:
        super().__init__(failure_rate=failure_rate, base_latency_ms=base_latency_ms)

    @property
    def channel_name(self) -> str:
        return "SIREN"

    async def send(
        self,
        recipient: Recipient,
        alert: Alert,
        message_text: str,
        delivery_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DeliveryResult:
        t0 = time.perf_counter()
        await asyncio.sleep(random.uniform(0.02, 0.06))
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        did_fail = random.random() < self.failure_rate
        did_id = delivery_id or f"DEL_SIR_{alert.id}_{recipient.id}"

        if did_fail:
            return DeliveryResult(
                success=False,
                delivery_id=did_id,
                channel=self.channel_name,
                recipient_id=recipient.id,
                status="FAILED",
                latency_ms=latency_ms,
                error="Siren tower actuator power failure or relay fault.",
            )

        return DeliveryResult(
            success=True,
            delivery_id=did_id,
            channel=self.channel_name,
            recipient_id=recipient.id,
            status="SENT",
            latency_ms=latency_ms,
            details={"siren_id": f"SIR_{alert.village_id}", "decibel_level": 120, "pattern": "CONTINUOUS_WARBLE"},
        )


def get_channel_adapter(channel: str, failure_rate: Optional[float] = None) -> BaseChannelAdapter:
    """Factory retrieving channel adapter instance, configurable for live provider substitution."""
    channel_clean = channel.upper()
    kwargs = {"failure_rate": failure_rate} if failure_rate is not None else {}

    if channel_clean == "CELL_BROADCAST":
        return CellBroadcastMock(**kwargs)
    elif channel_clean == "SMS":
        return SMSMock(**kwargs)
    elif channel_clean == "WHATSAPP":
        return WhatsAppMock(**kwargs)
    elif channel_clean == "IVR":
        return IVRMock(**kwargs)
    elif channel_clean == "VOLUNTEER":
        return VolunteerTaskAdapter(**kwargs)
    elif channel_clean == "SIREN":
        return SirenMock(**kwargs)
    else:
        raise ValueError(f"Unknown channel adapter '{channel}'.")
