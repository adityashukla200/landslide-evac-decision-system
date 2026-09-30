"""Community Disaster Resilience Index (CDRI) Computation Service.

Calculates composite village resilience scores (0-100) across 5 core dimensions:
1. Physical / Infrastructure Resilience (roads, masonry quality, helipad access, backup power)
2. Social Vulnerability (elderly/child dependency ratio, literacy, warning comprehension)
3. Economic Coping Capacity (income diversity, insurance penetration, self-help groups)
4. Institutional Readiness (Aapda Mitra volunteers trained, mock drill frequency, edge sirens)
5. Hazard Exposure Penalty (slope steepness, distance to river toe, historical breach count)
"""

from typing import Dict, Any, List


class CommunityResilienceIndexCalculator:
    """Calculates multi-dimensional CDRI scores for Himalayan villages."""

    # Pre-calculated village attributes for Uttarkashi district
    VILLAGE_ATTRIBUTES: Dict[str, Dict[str, Any]] = {
        "VIL_UTK_01": {
            "name": "Harsil",
            "infra": 78.0,
            "social": 72.0,
            "economic": 84.0,  # Apple economy & army presence
            "institutional": 85.0,
            "hazard_penalty": 35.0,  # High slope & river proximity
        },
        "VIL_UTK_02": {
            "name": "Dharali",
            "infra": 62.0,
            "social": 68.0,
            "economic": 70.0,
            "institutional": 74.0,
            "hazard_penalty": 42.0,
        },
        "VIL_UTK_03": {
            "name": "Jhala",
            "infra": 54.0,
            "social": 60.0,
            "economic": 58.0,
            "institutional": 65.0,
            "hazard_penalty": 48.0,
        },
        "VIL_UTK_04": {
            "name": "Sukhi",
            "infra": 70.0,
            "social": 75.0,
            "economic": 68.0,
            "institutional": 80.0,
            "hazard_penalty": 28.0,  # High ridge location, lower flood risk
        },
        "VIL_UTK_05": {
            "name": "Gangotri",
            "infra": 65.0,
            "social": 60.0,
            "economic": 72.0,
            "institutional": 78.0,
            "hazard_penalty": 52.0,  # High glacial runoff exposure
        },
        "VIL_UTK_10": {
            "name": "Uttarkashi Town",
            "infra": 88.0,
            "social": 82.0,
            "economic": 86.0,
            "institutional": 92.0,
            "hazard_penalty": 30.0,
        },
    }

    @classmethod
    def calculate_cdri(cls, village_id: str) -> Dict[str, Any]:
        data = cls.VILLAGE_ATTRIBUTES.get(
            village_id,
            {
                "name": f"Village {village_id}",
                "infra": 60.0,
                "social": 65.0,
                "economic": 60.0,
                "institutional": 70.0,
                "hazard_penalty": 35.0,
            },
        )

        # Weighted composite score:
        # CDRI = 0.25*Infra + 0.20*Social + 0.20*Econ + 0.25*Inst - 0.15*HazardPenalty
        raw_score = (
            0.25 * data["infra"]
            + 0.20 * data["social"]
            + 0.20 * data["economic"]
            + 0.25 * data["institutional"]
            - 0.15 * data["hazard_penalty"]
        )
        # Normalize to 0-100
        cdri_score = round(max(5.0, min(98.0, raw_score * 1.15)), 1)

        if cdri_score >= 80.0:
            tier = "TIER_1_ROBUST"
        elif cdri_score >= 65.0:
            tier = "TIER_2_MODERATE"
        elif cdri_score >= 50.0:
            tier = "TIER_3_VULNERABLE"
        else:
            tier = "TIER_4_CRITICAL"

        return {
            "village_id": village_id,
            "village_name": data["name"],
            "overall_cdri_score": cdri_score,
            "infrastructure_score": data["infra"],
            "social_vulnerability_score": data["social"],
            "economic_coping_score": data["economic"],
            "institutional_readiness_score": data["institutional"],
            "hazard_exposure_score": data["hazard_penalty"],
            "resilience_tier": tier,
        }

    @classmethod
    def calculate_all(cls) -> List[Dict[str, Any]]:
        return [cls.calculate_cdri(vid) for vid in cls.VILLAGE_ATTRIBUTES.keys()]
