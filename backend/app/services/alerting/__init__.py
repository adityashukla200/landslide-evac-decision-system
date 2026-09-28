"""Multi-channel emergency alerting, CAP 1.2 XML generation, ladder orchestration, and fatigue control."""

from backend.app.services.alerting.adapters import (
    BaseChannelAdapter,
    DeliveryResult,
    CellBroadcastMock,
    SMSMock,
    WhatsAppMock,
    IVRMock,
    VolunteerTaskAdapter,
    SirenMock,
    get_channel_adapter,
)
from backend.app.services.alerting.cap import generate_cap_12_xml
from backend.app.services.alerting.fatigue import (
    check_alert_suppression,
    filter_recipients_by_safety,
    get_tier_level,
)
from backend.app.services.alerting.orchestrator import AlertLadderOrchestrator
from backend.app.services.alerting.metrics import (
    calculate_alert_reach,
    calculate_drill_report,
)

__all__ = [
    "BaseChannelAdapter",
    "DeliveryResult",
    "CellBroadcastMock",
    "SMSMock",
    "WhatsAppMock",
    "IVRMock",
    "VolunteerTaskAdapter",
    "SirenMock",
    "get_channel_adapter",
    "generate_cap_12_xml",
    "check_alert_suppression",
    "filter_recipients_by_safety",
    "get_tier_level",
    "AlertLadderOrchestrator",
    "calculate_alert_reach",
    "calculate_drill_report",
]
