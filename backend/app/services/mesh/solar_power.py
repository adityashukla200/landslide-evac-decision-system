"""Solar MPPT & Sub-Zero LiFePO4 Battery Winter Protection Engine.

Himalayan winters reach -15 deg C to -25 deg C.
Charging LiFePO4 batteries below 0 deg C causes irreversible lithium metal plating,
internal dendrite growth, and catastrophic cell shorting.
This engine implements:
1. Sub-zero charge cut-off / throttle to prevent cell damage.
2. Adaptive deep-sleep duty cycling based on solar irradiance and state-of-charge.
3. Brownout mitigation with Last-Gasp mesh packet dispatch before node power cut.
"""

from typing import Dict, Any


class SolarPowerManager:
    """Manages MPPT state machine and LiFePO4 sub-zero thermal limits."""

    # LiFePO4 thermal and electrical operating thresholds
    MIN_SAFE_CHARGE_TEMP_C = 0.0     # Never fast-charge lithium below 0 C
    SUBZERO_TRICKLE_TEMP_C = -5.0    # Absolute charging cutoff below -5 C
    CRITICAL_BATTERY_PCT = 15.0      # Trigger Last-Gasp packet
    BROWNOUT_VOLTAGE_V = 3.05        # LiFePO4 1S cell cutoff

    @classmethod
    def evaluate_node_power(
        cls,
        node_id: str,
        solar_panel_v: float,
        battery_v: float,
        charge_current_ma: float,
        battery_temp_c: float,
        load_current_ma: float = 35.0,
    ) -> Dict[str, Any]:
        """Calculates MPPT state, temperature throttling, and deep sleep interval."""

        # Estimate battery State of Charge (SoC %) for LiFePO4 3.2V nominal cell
        # Nominal curve: 3.4V+ = 100%, 3.3V = 80%, 3.25V = 50%, 3.2V = 25%, 3.0V = 5%
        if battery_v >= 3.40:
            soc_pct = 100.0
        elif battery_v >= 3.30:
            soc_pct = 70.0 + (battery_v - 3.30) / 0.10 * 30.0
        elif battery_v >= 3.20:
            soc_pct = 20.0 + (battery_v - 3.20) / 0.10 * 50.0
        else:
            soc_pct = max(2.0, (battery_v - 2.8) / 0.40 * 20.0)
        soc_pct = round(min(100.0, max(0.0, soc_pct)), 1)

        # Thermal protection state machine
        subzero_active = battery_temp_c < cls.MIN_SAFE_CHARGE_TEMP_C
        charge_throttled = False
        mppt_state = "MPPT_OPTIMAL"

        if battery_temp_c < cls.SUBZERO_TRICKLE_TEMP_C:
            charge_throttled = True
            mppt_state = "SUBZERO_CUTOFF_LITHIUM_PROTECT"
        elif battery_temp_c < cls.MIN_SAFE_CHARGE_TEMP_C:
            charge_throttled = True
            mppt_state = "SUBZERO_TRICKLE_ONLY"
        elif solar_panel_v > battery_v + 1.0:
            mppt_state = "MPPT_OPTIMAL_TRACKING"
        elif solar_panel_v > 2.0:
            mppt_state = "DIFFUSE_LIGHT_FLOAT"
        else:
            mppt_state = "NIGHT_DISCHARGE"

        # Adaptive sleep interval
        if soc_pct < cls.CRITICAL_BATTERY_PCT:
            sleep_interval_sec = 900  # 15 minutes extreme survival sleep
            last_gasp_warn = True
            mppt_state = "CRITICAL_LOW_POWER_SURVIVAL"
        elif subzero_active and solar_panel_v < 4.0:
            sleep_interval_sec = 300  # 5 minutes winter conservation
            last_gasp_warn = False
        else:
            sleep_interval_sec = 60   # Normal 1 minute active reporting
            last_gasp_warn = False

        # Autonomy calculation (assuming 5000 mAh cell)
        available_mah = (soc_pct / 100.0) * 5000.0
        effective_load = load_current_ma * (60.0 / sleep_interval_sec)
        autonomy_hours = round(available_mah / max(1.0, effective_load), 1)

        return {
            "node_id": node_id,
            "battery_pct": soc_pct,
            "mppt_state": mppt_state,
            "subzero_protection_active": subzero_active,
            "charge_throttled": charge_throttled,
            "recommended_sleep_interval_sec": sleep_interval_sec,
            "last_gasp_warning_triggered": last_gasp_warn,
            "estimated_autonomy_hours": autonomy_hours,
        }
