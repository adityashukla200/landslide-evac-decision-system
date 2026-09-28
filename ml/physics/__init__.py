"""Physics simulation package for geotechnical slope stability and catchment hydrology."""

from ml.physics.slope_stability import compute_infinite_slope_fs, factor_of_safety
from ml.physics.scenario_generator import generate_physics_scenarios, save_physics_dataset
from ml.physics.hydrology import (
    compute_scs_cn_runoff,
    estimate_time_of_concentration,
    compute_catchment_hydrograph,
)

__all__ = [
    "compute_infinite_slope_fs",
    "factor_of_safety",
    "generate_physics_scenarios",
    "save_physics_dataset",
    "compute_scs_cn_runoff",
    "estimate_time_of_concentration",
    "compute_catchment_hydrograph",
]
