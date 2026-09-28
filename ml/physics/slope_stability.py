"""Infinite-slope geotechnical factor of safety model for slope stability assessment.

Implements the classical infinite-slope limit-equilibrium formulation:
    FS = (c' + (gamma*z - m*gamma_w*z) * cos^2(theta) * tan(phi)) / (gamma*z * sin(theta) * cos(theta))
with full NumPy vectorization and parameter uncertainty modeling.
"""

from typing import Union, Dict, Any, Optional
import numpy as np
import pandas as pd


def compute_infinite_slope_fs(
    slope_deg: Union[float, np.ndarray],
    cohesion_kpa: Union[float, np.ndarray] = 12.0,
    friction_angle_deg: Union[float, np.ndarray] = 32.0,
    soil_depth_m: Union[float, np.ndarray] = 1.8,
    saturation_ratio: Union[float, np.ndarray] = 0.5,
    gamma_kn_m3: Union[float, np.ndarray] = 18.5,
    gamma_w_kn_m3: float = 9.81,
) -> Union[float, np.ndarray]:
    """Compute the geotechnical Factor of Safety (FS) for an infinite slope.

    Parameters:
        slope_deg: Slope angle in degrees (theta).
        cohesion_kpa: Effective soil cohesion c' in kPa (kN/m^2).
        friction_angle_deg: Internal friction angle phi' in degrees.
        soil_depth_m: Soil mantle thickness z in meters.
        saturation_ratio: Fraction of soil column saturated m (0.0 to 1.0).
        gamma_kn_m3: Total unit weight of moist soil in kN/m^3.
        gamma_w_kn_m3: Unit weight of water in kN/m^3 (default 9.81).

    Returns:
        Factor of Safety (FS). FS < 1.0 indicates slope failure.
    """
    # Convert angles to radians
    theta = np.radians(np.maximum(slope_deg, 0.5))  # prevent division by zero on flat ground
    phi = np.radians(friction_angle_deg)
    m = np.clip(saturation_ratio, 0.0, 1.0)
    z = np.maximum(soil_depth_m, 0.1)

    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    tan_phi = np.tan(phi)

    # Effective normal stress on slip plane: sigma'_n = (gamma - m * gamma_w) * z * cos^2(theta)
    effective_stress = (gamma_kn_m3 * z - m * gamma_w_kn_m3 * z) * (cos_theta ** 2)
    effective_stress = np.maximum(effective_stress, 0.0)

    # Resisting shear strength: tau_f = c' + sigma'_n * tan(phi)
    resisting = cohesion_kpa + effective_stress * tan_phi

    # Driving shear stress: tau_d = gamma * z * sin(theta) * cos(theta)
    driving = gamma_kn_m3 * z * sin_theta * cos_theta
    driving = np.maximum(driving, 1e-4)

    fs = resisting / driving
    return fs


def factor_of_safety(
    village_features: Dict[str, Any],
    rainfall_series: Union[float, np.ndarray, pd.Series, list],
    cohesion_kpa: Optional[float] = None,
    friction_angle_deg: Optional[float] = None,
    soil_depth_m: Optional[float] = None,
    porosity: float = 0.38,
) -> Dict[str, Any]:
    """Operational explainability function computing physical FS for a village under rainfall.

    Parameters:
        village_features: Dictionary containing village attributes:
            - 'slope': terrain slope in degrees
            - 'elevation': elevation in meters (optional)
            - 'antecedent_moisture': initial saturation ratio [0, 1] (optional, default 0.35)
        rainfall_series: Recent cumulative rainfall in mm (float) or array of hourly rainfall.
        cohesion_kpa: Soil cohesion (inferred from elevation if None).
        friction_angle_deg: Internal friction angle (default 32.0 deg).
        soil_depth_m: Soil regolith depth (default 1.8 m).
        porosity: Effective soil porosity (default 0.38).

    Returns:
        Dictionary containing FS value, saturation ratio, shear stresses, and stability diagnosis.
    """
    slope = float(village_features.get("slope", 28.0))
    elev = float(village_features.get("elevation", 1500.0))
    m0 = float(village_features.get("antecedent_moisture", 0.35))

    # Geotechnical parameter estimation if not explicitly provided
    if cohesion_kpa is None:
        cohesion_kpa = float(village_features.get("cohesion_kpa", 8.0 if elev < 1800 else 5.5))
    if friction_angle_deg is None:
        friction_angle_deg = float(village_features.get("friction_angle_deg", 31.0))
    if soil_depth_m is None:
        soil_depth_m = float(village_features.get("soil_depth_m", 2.0 if elev < 1800 else 1.8))

    # Calculate cumulative infiltration rainfall
    if isinstance(rainfall_series, (int, float)):
        p_cum = float(rainfall_series)
    else:
        p_cum = float(np.sum(rainfall_series))

    # Saturation response: soil water storage capacity = z * porosity * 1000 mm
    soil_capacity_mm = soil_depth_m * porosity * 1000.0
    added_saturation = p_cum / soil_capacity_mm
    m_final = float(np.clip(m0 + added_saturation, 0.0, 1.0))

    # Compute Factor of Safety
    fs_val = float(compute_infinite_slope_fs(
        slope_deg=slope,
        cohesion_kpa=cohesion_kpa,
        friction_angle_deg=friction_angle_deg,
        soil_depth_m=soil_depth_m,
        saturation_ratio=m_final,
    ))

    # Classify stability state
    if fs_val >= 1.30:
        diagnosis = "STABLE"
    elif fs_val >= 1.0:
        diagnosis = "MARGINAL"
    else:
        diagnosis = "CRITICAL_FAILURE"

    theta = np.radians(slope)
    gamma = 18.5
    tau_d = gamma * soil_depth_m * np.sin(theta) * np.cos(theta)
    tau_f = fs_val * tau_d

    return {
        "factor_of_safety": round(fs_val, 3),
        "saturation_ratio": round(m_final, 3),
        "cumulative_rainfall_mm": round(p_cum, 1),
        "slope_deg": round(slope, 1),
        "diagnosis": diagnosis,
        "driving_stress_kpa": round(float(tau_d), 2),
        "resisting_strength_kpa": round(float(tau_f), 2),
        "cohesion_kpa": cohesion_kpa,
        "friction_angle_deg": friction_angle_deg,
        "soil_depth_m": soil_depth_m,
    }
