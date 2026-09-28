"""Bridge module exposing evacuation services from backend.app.services.evacuation."""

from backend.app.services.evacuation import (
    estimate_time_to_impact,
    compute_walking_time,
    EvacuationNetworkRouter,
    determine_margin_alert_stage,
    generate_alert_messages,
    generate_volunteer_task_cards,
    assess_evacuation_readiness,
    translate_bhashini,
    MESSAGE_TEMPLATES,
    BASE_WALKING_SPEED_M_PER_MIN,
    VULNERABLE_WALKING_SPEED_M_PER_MIN,
    NIGHT_TIME_FACTOR,
)

__all__ = [
    "estimate_time_to_impact",
    "compute_walking_time",
    "EvacuationNetworkRouter",
    "determine_margin_alert_stage",
    "generate_alert_messages",
    "generate_volunteer_task_cards",
    "assess_evacuation_readiness",
    "translate_bhashini",
    "MESSAGE_TEMPLATES",
    "BASE_WALKING_SPEED_M_PER_MIN",
    "VULNERABLE_WALKING_SPEED_M_PER_MIN",
    "NIGHT_TIME_FACTOR",
]
