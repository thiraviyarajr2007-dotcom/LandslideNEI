"""
Comprehensive Landslide Risk Engine (Phase 8H)
==============================================
Fuses Phase 8G static terrain susceptibility with dynamic operational
meteorological telemetry to deliver real-time operational risk assessments.

Architecture:
1. Static Layer: Phase 8G LocationProfiler (Copernicus DEM + SoilGrids + WorldCover -> Model A RF)
2. Dynamic Layer: RainfallProvider (CWC telemetry within <=50 km)
3. Trigger Engine: RainfallTriggerEngine (1h, 24h, 3d, 7d threshold checks)
4. Risk Fusion: RiskFusionEngine (Deterministic decision matrix -> LOW/WATCH/HIGH/CRITICAL)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .location_profiler import LocationProfiler
from .rainfall_provider import RainfallProvider, get_rainfall_provider
from .rainfall_trigger import RainfallTriggerEngine, get_rainfall_trigger_engine
from .risk_fusion import RiskFusionEngine, get_risk_fusion_engine


class RiskEngine:
    """Master high-level risk evaluation engine."""

    def __init__(
        self,
        profiler: Optional[LocationProfiler] = None,
        rainfall_provider: Optional[RainfallProvider] = None,
        trigger_engine: Optional[RainfallTriggerEngine] = None,
        fusion_engine: Optional[RiskFusionEngine] = None,
    ):
        self.profiler = profiler if profiler is not None else LocationProfiler()
        self.rainfall_provider = rainfall_provider or get_rainfall_provider()
        self.trigger_engine = trigger_engine or get_rainfall_trigger_engine()
        self.fusion_engine = fusion_engine or get_risk_fusion_engine()

    def evaluate_risk(
        self,
        latitude: float,
        longitude: float,
        timestamp: Optional[Any] = None,
        max_distance_km: Optional[float] = None,
        max_age_hours: Optional[float] = None,
        reference_time: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate full operational landslide risk for a geographic location.

        Parameters
        ----------
        latitude : float
            Query latitude in decimal degrees.
        longitude : float
            Query longitude in decimal degrees.
        timestamp : Optional[str or datetime]
            Specific observation timestamp. If None, queries latest available.
        max_distance_km : Optional[float]
            Maximum acceptable telemetry station distance. Defaults to 50 km.
        max_age_hours : Optional[float]
            Maximum acceptable telemetry age. Defaults to 6h.
        reference_time : Optional[str or datetime]
            Reference time for freshness calculation.
        """
        # 1. Evaluate Static Susceptibility Profile
        static_profile = self.profiler.profile_location(latitude, longitude)

        # Domain boundary rejection handling
        if static_profile.get("status") != "SUCCESS":
            return {
                "status": static_profile.get("status", "ERROR"),
                "location": static_profile.get("location", {
                    "latitude": latitude,
                    "longitude": longitude,
                    "supported_domain": False,
                }),
                "error": static_profile.get("error", "Location lies outside supported operational domain."),
                "static_susceptibility": None,
                "rainfall": None,
                "rainfall_trigger": None,
                "risk": None,
                "model_lineage": {
                    "static_model": "Model A (Environmental Only)",
                    "architecture": "Static Susceptibility + Dynamic Rainfall Fusion",
                },
                "scientific_limitations": static_profile.get("metadata", {}).get("notes", []),
            }

        # 2. Retrieve Operational Rainfall
        rainfall_data = self.rainfall_provider.get_rainfall_for_location(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            max_distance_km=max_distance_km,
            max_age_hours=max_age_hours,
            reference_time=reference_time,
        )

        # 3. Evaluate Dynamic Rainfall Trigger
        rainfall_trigger = self.trigger_engine.evaluate_rainfall(rainfall_data)

        # 4. Fuse Static Susceptibility and Dynamic Trigger
        fusion_result = self.fusion_engine.fuse_risk(static_profile, rainfall_trigger)

        # 5. Compile Master Risk Evaluation
        return {
            "status": "SUCCESS",
            "location": static_profile["location"],
            "static_susceptibility": {
                "score": static_profile["susceptibility"]["score"],
                "category": static_profile["susceptibility"]["category"],
                "category_label": static_profile["susceptibility"]["category_label"],
                "category_description": static_profile["susceptibility"]["category_description"],
                "quality_status": static_profile["quality"]["status"],
                "terrain": static_profile["terrain"],
                "soil": static_profile["soil"],
                "landcover": static_profile["landcover"],
                "reason_codes": static_profile["explainability"]["reason_codes"],
            },
            "rainfall": rainfall_data,
            "rainfall_trigger": rainfall_trigger,
            "risk": fusion_result,
            "model_lineage": {
                "static_model": "Model A (Environmental Only)",
                "pipeline_artifact": "model/static_lsm_pipeline.joblib",
                "metadata_artifact": "model/static_lsm_metadata.json",
                "rainfall_architecture": "Decoupled Operational Telemetry Tier",
                "fusion_method": "Deterministic Rule-Based Decision Matrix",
            },
            "scientific_limitations": fusion_result["scientific_limitations"],
        }


# Module level singleton
_ENGINE_INSTANCE: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = RiskEngine()
    return _ENGINE_INSTANCE


def evaluate_location_risk(
    latitude: float,
    longitude: float,
    timestamp: Optional[Any] = None,
    max_distance_km: Optional[float] = None,
    max_age_hours: Optional[float] = None,
    reference_time: Optional[Any] = None,
) -> Dict[str, Any]:
    """Module-level convenience function for end-to-end operational risk evaluation."""
    engine = get_risk_engine()
    return engine.evaluate_risk(
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        max_distance_km=max_distance_km,
        max_age_hours=max_age_hours,
        reference_time=reference_time,
    )
