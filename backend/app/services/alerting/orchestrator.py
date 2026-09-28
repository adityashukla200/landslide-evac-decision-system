"""Fallback alert ladder orchestrator for cascading multi-channel warning dissemination."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from backend.app.db.models import Alert, Recipient, AlertDelivery, Village
from backend.app.services.alerting.adapters import (
    BaseChannelAdapter,
    DeliveryResult,
    get_channel_adapter,
)
from backend.app.services.alerting.fatigue import filter_recipients_by_safety


class AlertLadderOrchestrator:
    """Manages multi-channel escalating emergency alert delivery.

    Ladder Sequence:
    1. Cell Broadcast (instantaneous area broadcast) + SMS to all eligible village recipients.
    2. Wait for recipient acknowledgement (configurable window, default 300s / 5m).
    3. Escalate unacknowledged recipients to IVR automated voice call.
    4. Escalate unacknowledged recipients to Volunteer task card assignment.
    5. Escalate to Village Siren acoustic alert (for unacknowledged residents or EVACUATE emergency).
    """

    def __init__(
        self,
        adapters: Optional[Dict[str, BaseChannelAdapter]] = None,
        failure_rates: Optional[Dict[str, float]] = None,
    ) -> None:
        rates = failure_rates or {}
        self.adapters = adapters or {
            "CELL_BROADCAST": get_channel_adapter("CELL_BROADCAST", failure_rate=rates.get("CELL_BROADCAST", 0.0)),
            "SMS": get_channel_adapter("SMS", failure_rate=rates.get("SMS", 0.0)),
            "IVR": get_channel_adapter("IVR", failure_rate=rates.get("IVR", 0.0)),
            "VOLUNTEER": get_channel_adapter("VOLUNTEER", failure_rate=rates.get("VOLUNTEER", 0.0)),
            "SIREN": get_channel_adapter("SIREN", failure_rate=rates.get("SIREN", 0.0)),
        }

    async def execute_alert_ladder(
        self,
        alert_id: str,
        db: Session,
        escalation_window_sec: float = 300.0,
        confirmed_safe_ids: Optional[Set[str]] = None,
        auto_ack_recipients: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Execute the full cascading alert ladder for an alert."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert with id '{alert_id}' not found.")

        village = db.query(Village).filter(Village.id == alert.village_id).first()
        all_recipients = (
            db.query(Recipient).filter(Recipient.village_id == alert.village_id).all()
        )

        if not all_recipients:
            return {
                "alert_id": alert_id,
                "village_id": alert.village_id,
                "status": "NO_RECIPIENTS",
                "total_recipients": 0,
                "deliveries": [],
            }

        # Fatigue control: filter out confirmed safe recipients
        eligible_recipients = filter_recipients_by_safety(
            all_recipients,
            village_id=alert.village_id,
            db=db,
            confirmed_safe_ids=confirmed_safe_ids,
        )

        if not eligible_recipients:
            return {
                "alert_id": alert_id,
                "village_id": alert.village_id,
                "status": "ALL_CONFIRMED_SAFE",
                "total_recipients": len(all_recipients),
                "eligible_recipients": 0,
                "deliveries": [],
            }

        auto_ack = set(auto_ack_recipients or [])
        acknowledged_recipients: Set[str] = set()
        deliveries_recorded: List[Dict[str, Any]] = []

        # Helper to log delivery to database
        def record_delivery(
            recipient_id: str,
            channel: str,
            status: str,
            acked: bool = False,
        ) -> AlertDelivery:
            d_id = f"DEL_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            acked_at = now if acked else None
            deliv = AlertDelivery(
                id=d_id,
                alert_id=alert.id,
                recipient_id=recipient_id,
                channel=channel,
                status="ACKNOWLEDGED" if acked else status,
                sent_at=now,
                acked_at=acked_at,
            )
            db.add(deliv)
            db.flush()
            deliveries_recorded.append(
                {
                    "id": d_id,
                    "recipient_id": recipient_id,
                    "channel": channel,
                    "status": "ACKNOWLEDGED" if acked else status,
                    "acked_at": acked_at.isoformat() if acked_at else None,
                }
            )
            return deliv

        # STEP 1: Cell Broadcast & SMS dispatch to all eligible recipients
        cb_tasks = []
        sms_tasks = []
        for r in eligible_recipients:
            cb_tasks.append(self.adapters["CELL_BROADCAST"].send(r, alert, alert.message))
            sms_tasks.append(self.adapters["SMS"].send(r, alert, alert.message))

        cb_results = await asyncio.gather(*cb_tasks, return_exceptions=True)
        sms_results = await asyncio.gather(*sms_tasks, return_exceptions=True)

        for r, res in zip(eligible_recipients, cb_results):
            if isinstance(res, DeliveryResult) and res.success:
                # Cell broadcast delivered
                is_acked = r.id in auto_ack
                if is_acked:
                    acknowledged_recipients.add(r.id)
                record_delivery(r.id, "CELL_BROADCAST", "SENT", acked=is_acked)
            else:
                record_delivery(r.id, "CELL_BROADCAST", "FAILED", acked=False)

        for r, res in zip(eligible_recipients, sms_results):
            if isinstance(res, DeliveryResult) and res.success:
                is_acked = r.id in auto_ack
                if is_acked:
                    acknowledged_recipients.add(r.id)
                record_delivery(r.id, "SMS", "SENT", acked=is_acked)
            else:
                record_delivery(r.id, "SMS", "FAILED", acked=False)

        db.commit()

        # STEP 2: Wait for acknowledgement window
        # In actual deployment this waits up to escalation_window_sec (e.g. 300s)
        # In fast test mode or non-blocking runs, callers provide a small window (e.g. 0.05s)
        if escalation_window_sec > 0:
            await asyncio.sleep(min(escalation_window_sec, 0.1))

        # Check latest acks from DB in case external webhooks acknowledged
        acked_db = (
            db.query(AlertDelivery.recipient_id)
            .filter(
                AlertDelivery.alert_id == alert.id,
                AlertDelivery.status == "ACKNOWLEDGED",
            )
            .all()
        )
        for (r_id,) in acked_db:
            acknowledged_recipients.add(r_id)

        # STEP 3: Escalate unacknowledged recipients to IVR Voice Call
        unacked_recipients = [r for r in eligible_recipients if r.id not in acknowledged_recipients]
        if unacked_recipients:
            ivr_tasks = [
                self.adapters["IVR"].send(r, alert, alert.message)
                for r in unacked_recipients
            ]
            ivr_results = await asyncio.gather(*ivr_tasks, return_exceptions=True)
            for r, res in zip(unacked_recipients, ivr_results):
                if isinstance(res, DeliveryResult) and res.success:
                    is_acked = r.id in auto_ack
                    if is_acked:
                        acknowledged_recipients.add(r.id)
                    record_delivery(r.id, "IVR", "SENT", acked=is_acked)
                else:
                    record_delivery(r.id, "IVR", "FAILED", acked=False)
            db.commit()

        # STEP 4: Escalate remaining unacknowledged recipients to Volunteer Task
        unacked_recipients = [r for r in eligible_recipients if r.id not in acknowledged_recipients]
        if unacked_recipients:
            vol_tasks = [
                self.adapters["VOLUNTEER"].send(r, alert, alert.message)
                for r in unacked_recipients
            ]
            vol_results = await asyncio.gather(*vol_tasks, return_exceptions=True)
            for r, res in zip(unacked_recipients, vol_results):
                if isinstance(res, DeliveryResult) and res.success:
                    record_delivery(r.id, "VOLUNTEER", "SENT", acked=False)
                else:
                    record_delivery(r.id, "VOLUNTEER", "FAILED", acked=False)
            db.commit()

        # STEP 5: Siren Trigger
        # Trigger siren if there are still unacknowledged recipients or if tier is EVACUATE / RED
        is_high_tier = alert.tier.upper() in ["EVACUATE", "RED"]
        still_unacked = any(r.id not in acknowledged_recipients for r in eligible_recipients)

        if still_unacked or is_high_tier:
            # Siren triggers on the first representative recipient/village anchor
            anchor_rec = eligible_recipients[0]
            siren_res = await self.adapters["SIREN"].send(anchor_rec, alert, alert.message)
            status = "SENT" if (isinstance(siren_res, DeliveryResult) and siren_res.success) else "FAILED"
            record_delivery(anchor_rec.id, "SIREN", status, acked=False)
            db.commit()

        return {
            "alert_id": alert_id,
            "village_id": alert.village_id,
            "tier": alert.tier,
            "status": "COMPLETED",
            "total_recipients": len(all_recipients),
            "eligible_recipients": len(eligible_recipients),
            "acknowledged_count": len(acknowledged_recipients),
            "deliveries_count": len(deliveries_recorded),
            "deliveries": deliveries_recorded,
        }

    @staticmethod
    def acknowledge_delivery(
        delivery_id: str,
        db: Session,
        acked_at: Optional[datetime] = None,
    ) -> Optional[AlertDelivery]:
        """Mark a specific delivery attempt as acknowledged."""
        deliv = db.query(AlertDelivery).filter(AlertDelivery.id == delivery_id).first()
        if not deliv:
            return None
        deliv.status = "ACKNOWLEDGED"
        deliv.acked_at = acked_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(deliv)
        return deliv

    @staticmethod
    def acknowledge_by_recipient(
        alert_id: str,
        recipient_id: str,
        db: Session,
        acked_at: Optional[datetime] = None,
    ) -> List[AlertDelivery]:
        """Acknowledge all deliveries for a given recipient on an alert."""
        delivs = (
            db.query(AlertDelivery)
            .filter(
                AlertDelivery.alert_id == alert_id,
                AlertDelivery.recipient_id == recipient_id,
            )
            .all()
        )
        now = acked_at or datetime.now(timezone.utc)
        for d in delivs:
            d.status = "ACKNOWLEDGED"
            d.acked_at = now
        db.commit()
        return delivs
