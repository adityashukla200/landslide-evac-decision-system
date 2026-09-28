"""Alert fatigue control, suppression rules, and safe-zone recipient filtering."""

from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, List, Set
from sqlalchemy.orm import Session

from backend.app.db.models import Alert, Recipient, AlertDelivery

TIER_HIERARCHY = {
    "NONE": 0,
    "GREEN": 0,
    "WATCH": 1,
    "YELLOW": 1,
    "WARNING": 2,
    "ORANGE": 2,
    "EVACUATE": 3,
    "RED": 3,
}


def get_tier_level(tier: str) -> int:
    """Map alert tier to severity hierarchy level (0 to 3)."""
    return TIER_HIERARCHY.get(tier.upper(), 1)


def check_alert_suppression(
    village_id: str,
    new_tier: str,
    db: Session,
    cooldown_minutes: int = 60,
    current_time: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """Check if an alert should be suppressed due to fatigue control cooldown.

    Rules:
    1. If a previous alert for the same village is within its cooldown window:
       - Suppress if new alert is of equal or lower tier.
       - Allow through if new alert is of STRICTLY HIGHER tier (escalation override).
    2. If no active cooldown or cooldown expired, allow through.

    Returns:
        (is_suppressed, reason)
    """
    now = current_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Find the most recent active alert for this village
    recent_alerts = (
        db.query(Alert)
        .filter(Alert.village_id == village_id)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )

    if not recent_alerts:
        return False, None

    new_tier_level = get_tier_level(new_tier)

    for prev in recent_alerts:
        prev_time = prev.created_at
        if prev_time.tzinfo is None:
            prev_time = prev_time.replace(tzinfo=timezone.utc)

        # Check explicit cooldown_until or fallback to cooldown_minutes from created_at
        cooldown_deadline = prev.cooldown_until
        if cooldown_deadline is None:
            cooldown_deadline = prev_time + timedelta(minutes=cooldown_minutes)
        elif cooldown_deadline.tzinfo is None:
            cooldown_deadline = cooldown_deadline.replace(tzinfo=timezone.utc)

        if now < cooldown_deadline:
            prev_tier_level = get_tier_level(prev.tier)
            if new_tier_level <= prev_tier_level:
                remaining_min = int((cooldown_deadline - now).total_seconds() / 60)
                reason = (
                    f"Suppressed by alert fatigue cooldown: Active '{prev.tier}' alert exists "
                    f"until {cooldown_deadline.isoformat()} (~{remaining_min}m remaining). "
                    f"New tier '{new_tier}' is not a higher escalation."
                )
                return True, reason
            else:
                # Higher tier overrides cooldown
                return False, None

    return False, None


def filter_recipients_by_safety(
    recipients: List[Recipient],
    village_id: str,
    db: Session,
    confirmed_safe_ids: Optional[Set[str]] = None,
) -> List[Recipient]:
    """Filter out recipients who are confirmed in safe zones or safely evacuated.

    Ensures people already confirmed safe at shelters or designated refuge zones
    do not receive repeated panic alerts.
    """
    safe_ids = set(confirmed_safe_ids or [])
    eligible = [r for r in recipients if r.id not in safe_ids]
    return eligible
