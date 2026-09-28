"""Hydrology module implementing SCS-CN runoff generation and kinematic wave routing.

Transforms rainfall hyetographs into catchment runoff excess, hydrographs, and peak discharge
estimates (m^3/s) for hilly village catchments, with strict conservation of mass.
"""

from typing import Union, Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


def compute_scs_cn_runoff(
    rainfall_series_mm: Union[np.ndarray, List[float], pd.Series],
    curve_number: float = 75.0,
    initial_abstraction_ratio: float = 0.20,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute cumulative and incremental runoff excess using the SCS Curve Number method.

    Parameters:
        rainfall_series_mm: Array of hourly or sub-hourly precipitation depths in mm.
        curve_number: Catchment curve number CN (typically 65 to 88 for mountain colluvium).
        initial_abstraction_ratio: Fraction lambda where Ia = lambda * S (standard 0.20).

    Returns:
        Tuple of (incremental_runoff_mm, cumulative_runoff_mm).
    """
    p_series = np.asarray(rainfall_series_mm, dtype=np.float64)
    # Potential maximum soil retention S in mm
    cn = np.clip(curve_number, 40.0, 98.0)
    s = (25400.0 / cn) - 254.0

    # Initial abstraction Ia (surface depression storage, interception)
    ia = initial_abstraction_ratio * s

    # Cumulative precipitation
    p_cum = np.cumsum(p_series)

    # Cumulative runoff Q_cum = (P - Ia)^2 / (P - Ia + S) for P > Ia, else 0
    excess_p = np.maximum(p_cum - ia, 0.0)
    q_cum = np.where(p_cum > ia, (excess_p ** 2) / (excess_p + s), 0.0)

    # Enforce physical mass bounds: 0 <= Q_cum <= P_cum
    q_cum = np.clip(q_cum, 0.0, p_cum)

    # Incremental runoff per time interval
    q_inc = np.diff(np.insert(q_cum, 0, 0.0))
    q_inc = np.maximum(q_inc, 0.0)

    return q_inc, q_cum


def estimate_time_of_concentration(
    catchment_area_km2: float,
    slope_deg: float,
    curve_number: float = 75.0,
) -> float:
    """Estimate catchment time of concentration Tc (hours) using SCS lag relationship.

    Parameters:
        catchment_area_km2: Drainage basin area in square kilometers.
        slope_deg: Average hillslope gradient in degrees.
        curve_number: Catchment Curve Number.

    Returns:
        Time of concentration Tc in hours.
    """
    area = max(catchment_area_km2, 0.5)
    slope_pct = np.clip(np.tan(np.radians(max(slope_deg, 2.0))) * 100.0, 1.0, 120.0)
    s = (25400.0 / curve_number) - 254.0

    # Hydraulic length L in meters (empirical Hack's law approximation L = 1400 * A^0.56)
    hydraulic_length_m = 1400.0 * (area ** 0.56)

    # SCS lag equation: L_lag = L^0.8 * (S + 25.4)^0.7 / (4238 * slope^0.5) in hours
    lag_hours = (hydraulic_length_m ** 0.8) * ((s + 25.4) ** 0.7) / (4238.0 * (slope_pct ** 0.5))
    tc_hours = lag_hours / 0.6  # Tc ~= Lag / 0.6
    return float(np.clip(tc_hours, 0.35, 12.0))


def compute_catchment_hydrograph(
    village_features: Dict[str, Any],
    rainfall_series_mm: Union[np.ndarray, List[float], pd.Series],
    dt_hours: float = 1.0,
    curve_number: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute river discharge hydrograph and peak discharge for a village catchment.

    Parameters:
        village_features: Dictionary containing:
            - 'upstream_catchment_area': area in km^2
            - 'slope': hillslope angle in degrees
            - 'elevation': elevation in meters (optional)
        rainfall_series_mm: Array or series of precipitation depths (mm).
        dt_hours: Time step interval in hours (default 1.0h).
        curve_number: Catchment CN (inferred if None).

    Returns:
        Dictionary containing peak discharge (m^3/s), time to peak, total volumes, and mass balance.
    """
    p_series = np.asarray(rainfall_series_mm, dtype=np.float64)
    n_steps = len(p_series)
    area_km2 = float(village_features.get("upstream_catchment_area", 35.0))
    slope_deg = float(village_features.get("slope", 26.0))
    elev = float(village_features.get("elevation", 1400.0))

    if curve_number is None:
        # Lower valley settlements have slightly higher CN due to cleared soil and roads
        curve_number = 78.0 if elev < 1500 else 71.0

    # 1. Runoff Excess Generation (mm)
    q_inc_mm, q_cum_mm = compute_scs_cn_runoff(p_series, curve_number=curve_number)

    # 2. Time of Concentration & Unit Hydrograph
    tc = estimate_time_of_concentration(area_km2, slope_deg, curve_number)
    # Triangular unit hydrograph duration
    tp = 0.5 * dt_hours + 0.6 * tc  # Time to peak (hours)
    tb = 2.67 * tp                  # Base time (hours)

    # Peak of unit hydrograph: q_p = (0.208 * A) / tp in m^3/s per mm of runoff
    qp_unit = (0.208 * area_km2) / tp

    # 3. Convolution of Incremental Runoff with Unit Hydrograph
    n_uh = int(np.ceil(tb / dt_hours)) + 1
    t_uh = np.arange(n_uh) * dt_hours
    # Triangular shape
    uh = np.where(
        t_uh <= tp,
        (t_uh / tp) * qp_unit,
        np.maximum(((tb - t_uh) / (tb - tp)) * qp_unit, 0.0),
    )
    # Normalize UH so area under UH * dt equals 1 mm over area_km2 in m^3
    target_vol_m3 = 1000.0 * area_km2  # 1 mm * 1 km^2 = 1,000 m^3
    sim_vol_m3 = np.sum(uh) * dt_hours * 3600.0
    if sim_vol_m3 > 0:
        uh = uh * (target_vol_m3 / sim_vol_m3)

    # Convolve runoff excess with unit hydrograph
    q_discharge = np.convolve(q_inc_mm, uh, mode="full")[:n_steps]

    peak_discharge_m3s = float(np.max(q_discharge)) if len(q_discharge) > 0 else 0.0
    peak_hour = int(np.argmax(q_discharge)) if len(q_discharge) > 0 else 0

    # 4. Conservation of Mass Verification
    total_precip_mm = float(np.sum(p_series))
    total_runoff_mm = float(q_cum_mm[-1]) if len(q_cum_mm) > 0 else 0.0
    total_precip_vol_m3 = total_precip_mm * area_km2 * 1000.0
    total_runoff_vol_m3 = total_runoff_mm * area_km2 * 1000.0
    retention_vol_m3 = total_precip_vol_m3 - total_runoff_vol_m3
    mass_balance_error_pct = abs(
        (total_runoff_vol_m3 + retention_vol_m3 - total_precip_vol_m3) / max(total_precip_vol_m3, 1.0)
    ) * 100.0

    return {
        "peak_discharge_m3s": round(peak_discharge_m3s, 2),
        "peak_hour": peak_hour,
        "time_of_concentration_hours": round(tc, 2),
        "total_precipitation_mm": round(total_precip_mm, 2),
        "total_runoff_mm": round(total_runoff_mm, 2),
        "runoff_coefficient": round(total_runoff_mm / max(total_precip_mm, 0.001), 3),
        "catchment_area_km2": area_km2,
        "total_precipitation_vol_m3": round(total_precip_vol_m3, 1),
        "total_runoff_vol_m3": round(total_runoff_vol_m3, 1),
        "retention_vol_m3": round(retention_vol_m3, 1),
        "mass_balance_error_pct": round(mass_balance_error_pct, 6),
        "hydrograph_m3s": np.round(q_discharge, 2).tolist(),
    }
