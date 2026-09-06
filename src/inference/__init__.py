"""
Inference package for LandslideNEI static susceptibility and dynamic risk fusion.
"""

from .location_profiler import LocationProfiler, profile_location
from .rainfall_provider import (
    RainfallProvider,
    get_rainfall_for_location,
    get_rainfall_provider,
    get_imd_macro_rainfall,
    get_imd_district_rainfall,
)
from .rainfall_trigger import RainfallTriggerEngine, evaluate_rainfall_trigger, get_rainfall_trigger_engine
from .risk_fusion import RiskFusionEngine, fuse_static_and_dynamic_risk, get_risk_fusion_engine
from .risk_engine import RiskEngine, evaluate_location_risk, get_risk_engine

__all__ = [
    "LocationProfiler",
    "profile_location",
    "RainfallProvider",
    "get_rainfall_for_location",
    "get_rainfall_provider",
    "get_imd_macro_rainfall",
    "get_imd_district_rainfall",
    "RainfallTriggerEngine",
    "evaluate_rainfall_trigger",
    "get_rainfall_trigger_engine",
    "RiskFusionEngine",
    "fuse_static_and_dynamic_risk",
    "get_risk_fusion_engine",
    "RiskEngine",
    "evaluate_location_risk",
    "get_risk_engine",
]
