"""Live delivery reach, channel breakdown, and drill participation metrics."""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.models import Alert, Recipient, AlertDelivery, Village


def calculate_alert_reach(alert_id: str, db: Session) -> Dict[str, Any]:
    """Compute live multi-channel reach and acknowledgment metrics for an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError(f"Alert '{alert_id}' not found.")

    village = db.query(Village).filter(Village.id == alert.village_id).first()
    recipients = db.query(Recipient).filter(Recipient.village_id == alert.village_id).all()
    deliveries = db.query(AlertDelivery).filter(AlertDelivery.alert_id == alert_id).all()

    total_recipients = len(recipients)
    vulnerable_total = sum(1 for r in recipients if r.vulnerable_flag)

    # Track distinct reached and acknowledged recipients
    reached_recipient_ids = set()
    acked_recipient_ids = set()
    reached_vulnerable_ids = set()
    acked_vulnerable_ids = set()

    recipient_vuln_map = {r.id: r.vulnerable_flag for r in recipients}

    # Channel stats breakdown
    channel_stats: Dict[str, Dict[str, int]] = {}

    for d in deliveries:
        ch = d.channel
        if ch not in channel_stats:
            channel_stats[ch] = {"SENT": 0, "ACKNOWLEDGED": 0, "FAILED": 0, "TOTAL": 0}

        channel_stats[ch]["TOTAL"] += 1
        status_key = d.status if d.status in ["SENT", "ACKNOWLEDGED", "FAILED"] else "SENT"
        channel_stats[ch][status_key] += 1

        if d.status in ["SENT", "ACKNOWLEDGED"]:
            reached_recipient_ids.add(d.recipient_id)
            if recipient_vuln_map.get(d.recipient_id, False):
                reached_vulnerable_ids.add(d.recipient_id)

        if d.status == "ACKNOWLEDGED":
            acked_recipient_ids.add(d.recipient_id)
            if recipient_vuln_map.get(d.recipient_id, False):
                acked_vulnerable_ids.add(d.recipient_id)

    total_reached = len(reached_recipient_ids)
    total_acked = len(acked_recipient_ids)

    reach_pct = round((total_reached / total_recipients * 100.0), 1) if total_recipients > 0 else 0.0
    ack_pct = round((total_acked / total_recipients * 100.0), 1) if total_recipients > 0 else 0.0

    vuln_reach_pct = (
        round((len(reached_vulnerable_ids) / vulnerable_total * 100.0), 1)
        if vulnerable_total > 0
        else 0.0
    )
    vuln_ack_pct = (
        round((len(acked_vulnerable_ids) / vulnerable_total * 100.0), 1)
        if vulnerable_total > 0
        else 0.0
    )

    return {
        "alert_id": alert.id,
        "village_id": alert.village_id,
        "village_name": village.name if village else "Unknown",
        "tier": alert.tier,
        "is_drill": bool(getattr(alert, "drill_flag", False)),
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "summary": {
            "total_recipients": total_recipients,
            "total_reached": total_reached,
            "total_acknowledged": total_acked,
            "reach_percentage": reach_pct,
            "ack_percentage": ack_pct,
        },
        "vulnerable_population": {
            "total_vulnerable": vulnerable_total,
            "reached_vulnerable": len(reached_vulnerable_ids),
            "acknowledged_vulnerable": len(acked_vulnerable_ids),
            "reach_percentage": vuln_reach_pct,
            "ack_percentage": vuln_ack_pct,
        },
        "channels": channel_stats,
    }


def calculate_drill_report(drill_id: str, db: Session) -> Dict[str, Any]:
    """Calculate community exercise participation and response metrics for a drill alert."""
    metrics = calculate_alert_reach(drill_id, db)
    metrics["exercise_type"] = "COMMUNITY_EVACUATION_DRILL"
    metrics["compliance_rating"] = (
        "HIGH"
        if metrics["summary"]["ack_percentage"] >= 75.0
        else "MODERATE"
        if metrics["summary"]["ack_percentage"] >= 40.0
        else "LOW"
    )
    return metrics
