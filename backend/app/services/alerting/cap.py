"""Common Alerting Protocol (CAP v1.2) OASIS standard XML generation."""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from backend.app.db.models import Alert, Village

CAP_NAMESPACE = "urn:oasis:names:tc:emergency:cap:1.2"

URGENCY_MAP = {
    "EVACUATE": "Immediate",
    "WARNING": "Expected",
    "WATCH": "Future",
    "NONE": "Past",
}

SEVERITY_MAP = {
    "EVACUATE": "Extreme",
    "WARNING": "Severe",
    "WATCH": "Moderate",
    "NONE": "Minor",
}

CERTAINTY_MAP = {
    "EVACUATE": "Observed",
    "WARNING": "Likely",
    "WATCH": "Possible",
    "NONE": "Unlikely",
}


def generate_cap_12_xml(
    alert: Alert,
    village: Village,
    language: str = "en-IN",
    is_drill: bool = False,
    sender_id: str = "deoc.uttarkashi@uk.gov.in",
) -> str:
    """Generate official OASIS CAP v1.2 XML document for an emergency alert."""
    sent_iso = (alert.created_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    status_val = "Test" if (is_drill or getattr(alert, "drill_flag", False)) else "Actual"
    tier_upper = alert.tier.upper()

    urgency = URGENCY_MAP.get(tier_upper, "Expected")
    severity = SEVERITY_MAP.get(tier_upper, "Severe")
    certainty = CERTAINTY_MAP.get(tier_upper, "Likely")

    root = ET.Element("alert", xmlns=CAP_NAMESPACE)

    # Core CAP Header
    ET.SubElement(root, "identifier").text = f"IN-UK-UTK-{alert.id}"
    ET.SubElement(root, "sender").text = sender_id
    ET.SubElement(root, "sent").text = sent_iso
    ET.SubElement(root, "status").text = status_val
    ET.SubElement(root, "msgType").text = "Alert"
    ET.SubElement(root, "scope").text = "Public"

    # Info Block
    info = ET.SubElement(root, "info")
    ET.SubElement(info, "language").text = language
    ET.SubElement(info, "category").text = "Geo"
    ET.SubElement(info, "event").text = "Landslide / Flash Flood Directive"
    ET.SubElement(info, "urgency").text = urgency
    ET.SubElement(info, "severity").text = severity
    ET.SubElement(info, "certainty").text = certainty

    # Headline and Description
    prefix = "[EXERCISE / DRILL] " if status_val == "Test" else ""
    headline_text = f"{prefix}{tier_upper} DIRECTIVE: {village.name}, {village.district}"
    ET.SubElement(info, "headline").text = headline_text
    ET.SubElement(info, "description").text = alert.message
    ET.SubElement(info, "instruction").text = (
        "Follow designated evacuation trails to safe high-ground shelters. "
        "Avoid river banks, debris chutes, and swollen bridges."
    )

    # Area Block
    area = ET.SubElement(info, "area")
    ET.SubElement(area, "areaDesc").text = f"{village.name} Village Ward, {village.district} District, Uttarakhand"

    # Coordinates polygon (~600m boundary box around village center)
    lat, lon = village.lat, village.lon
    d = 0.003
    polygon_coords = (
        f"{lat - d:.4f},{lon - d:.4f} "
        f"{lat + d:.4f},{lon - d:.4f} "
        f"{lat + d:.4f},{lon + d:.4f} "
        f"{lat - d:.4f},{lon + d:.4f} "
        f"{lat - d:.4f},{lon - d:.4f}"
    )
    ET.SubElement(area, "polygon").text = polygon_coords

    # Format pretty XML
    rough_string = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(rough_string)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
