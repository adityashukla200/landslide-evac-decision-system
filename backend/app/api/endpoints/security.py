"""Security and identity verification endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from backend.app.core.security import get_current_role, require_role, UserRole, mask_phone_number

router = APIRouter(prefix="/security", tags=["Security & RBAC"])


@router.get("/whoami")
def whoami(role: UserRole = Depends(get_current_role)) -> Dict[str, Any]:
    """Inspect current role and access privileges."""
    privileges = {
        UserRole.OFFICER: [
            "trigger_emergency_alert",
            "modify_operational_thresholds",
            "initiate_evacuation_order",
            "dispatch_ndrf_teams",
            "view_unmasked_pii",
            "view_command_center",
        ],
        UserRole.VOLUNTEER: [
            "view_volunteer_tasks",
            "update_task_status",
            "submit_field_damage_report",
            "view_shelter_capacity",
            "view_masked_evacuee_list",
        ],
        UserRole.CITIZEN: [
            "view_public_alerts",
            "view_evacuation_routes",
            "view_safe_shelters",
            "submit_hazard_report",
            "access_tourist_portal",
        ],
    }
    return {
        "role": role.value,
        "privileges": privileges.get(role, []),
        "status": "authenticated",
        "privacy_policy": "Compliant with DPDP Act 2023. PII is masked by default on all public endpoints.",
    }


@router.post("/officer-only-action", dependencies=[Depends(require_role(["officer"]))])
def officer_only_action() -> Dict[str, str]:
    """Sample protected endpoint requiring District Officer or NDRF Commander privileges."""
    return {"status": "success", "message": "Authorized officer action executed successfully."}


@router.post("/volunteer-action", dependencies=[Depends(require_role(["officer", "volunteer"]))])
def volunteer_action() -> Dict[str, str]:
    """Sample endpoint for field volunteers or overseeing officers."""
    return {"status": "success", "message": "Volunteer field task action executed."}
