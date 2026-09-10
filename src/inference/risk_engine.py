"""
Comprehensive Landslide Risk Engine (Phase 8H)
==============================================
Fuses Phase 8G static terrain susceptibility with dynamic operational
meteorological telemetry to deliver real-time operational risk assessments.

Architecture:
1. Static Layer: Phase 8G LocationProfiler (Copernicus DEM + SoilGrids + WorldCover -> Model A RF)
2. Dynamic Layer: RainfallProvider (CWC telemetry within <=50 km)
3. Trigger Engine: RainfallTriggerEngine (1h, 24h, 3d, 7d threshold checks)
4. Geotechnical Layer: SoilPorePressureEngine (Saturation ratio, Pore pressure, Factor of Safety)
5. Risk Fusion: RiskFusionEngine (Deterministic decision matrix -> LOW/WATCH/HIGH/CRITICAL)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .location_profiler import LocationProfiler, get_location_profiler
from .rainfall_provider import RainfallProvider, get_rainfall_provider
from .rainfall_trigger import RainfallTriggerEngine, get_rainfall_trigger_engine
from .risk_fusion import RiskFusionEngine, get_risk_fusion_engine
from .soil_pore_pressure import compute_soil_saturation_and_pore_pressure
from .micro_climate_rainfall import compute_micro_climate_rainfall
from .anthropogenic_engine import compute_anthropogenic_impact


class RiskEngine:
    """Master high-level risk evaluation engine."""

    def __init__(
        self,
        profiler: Optional[LocationProfiler] = None,
        rainfall_provider: Optional[RainfallProvider] = None,
        trigger_engine: Optional[RainfallTriggerEngine] = None,
        fusion_engine: Optional[RiskFusionEngine] = None,
    ):
        self.profiler = profiler or get_location_profiler()
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
        auto_refetch: bool = False,
        road_cut_present: bool = False,
        cut_slope_deg: Optional[float] = None,
        drainage_blocked: bool = False,
        unsupported_excavation: bool = False,
        deforestation_observed: bool = False,
        has_retaining_wall: bool = False,
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
        auto_refetch : bool
            If True, enables secondary Open-Meteo REST API re-fetch when local CWC telemetry is missing/distant.
        road_cut_present : bool
            Whether road toe cut or excavation is present at the slope base.
        cut_slope_deg : Optional[float]
            Cut slope angle in degrees.
        drainage_blocked : bool
            Whether roadside culverts or slope drainage ditches are blocked.
        unsupported_excavation : bool
            Whether excavation lacks retaining structure.
        deforestation_observed : bool
            Whether recent vegetation clearing or burning occurred.
        has_retaining_wall : bool
            Whether engineered gabion or retaining wall is installed.
        """
        # 1. Evaluate Static Susceptibility Profile
        static_profile = self.profiler.profile_location(
            lat=latitude,
            lon=longitude,
            road_cut_present=road_cut_present,
            cut_slope_deg=cut_slope_deg,
            drainage_blocked=drainage_blocked,
            unsupported_excavation=unsupported_excavation,
            deforestation_observed=deforestation_observed,
            has_retaining_wall=has_retaining_wall,
        )

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
            auto_refetch=auto_refetch,
        )

        # 2b. Hyper-Local Micro-Climate & Doppler Weather Radar Modeling
        micro_rain = compute_micro_climate_rainfall(
            rainfall_1h=rainfall_data.get("rainfall_1h"),
            rainfall_24h=rainfall_data.get("rainfall_24h"),
            rainfall_7d=rainfall_data.get("rainfall_7d"),
            latitude=latitude,
            longitude=longitude,
            slope_deg=static_profile["terrain"].get("slope_deg"),
            aspect_deg=static_profile["terrain"].get("aspect_deg"),
            elevation_m=static_profile["terrain"].get("elevation_m"),
            plan_curvature=static_profile["terrain"].get("plan_curvature"),
            twi=static_profile["terrain"].get("topographic_wetness_index"),
        )
        rainfall_data.update(micro_rain)

        # Dynamic cloudburst / orographic explainability
        if micro_rain.get("cloudburst_detected"):
            static_profile["explainability"]["reason_codes"].append({
                "code": "DWR_CLOUDBURST_DETECTED",
                "description": (
                    f"Doppler Weather Radar reflectivity ({micro_rain.get('doppler_reflectivity_dbz')} dBZ from "
                    f"{micro_rain.get('doppler_radar_name')}) indicates extreme convective cloudburst cell (>40 mm/hr) "
                    f"over mountain catchment, creating immediate flash debris flow danger."
                ),
            })
        elif micro_rain.get("orographic_amplification_factor", 1.0) >= 1.15:
            static_profile["explainability"]["reason_codes"].append({
                "code": "OROGRAPHIC_PRECIPITATION_AMPLIFICATION",
                "description": (
                    f"Windward slope orientation ({static_profile['terrain'].get('aspect_deg')}°) forces orographic uplift, "
                    f"amplifying effective localized rainfall by {micro_rain['orographic_amplification_factor']:.2f}x."
                ),
            })

        # 3. Dynamic Soil Saturation & Pore-Water Pressure Mechanics
        dynamic_soil = compute_soil_saturation_and_pore_pressure(
            clay_percent=static_profile["soil"].get("clay_percent"),
            sand_percent=static_profile["soil"].get("sand_percent"),
            silt_percent=static_profile["soil"].get("silt_percent"),
            bulk_density_kg_dm3=static_profile["soil"].get("bulk_density_kg_dm3"),
            slope_deg=static_profile["terrain"].get("slope_deg"),
            rainfall_24h=rainfall_data.get("rainfall_24h"),
            rainfall_3d=rainfall_data.get("rainfall_3d"),
            rainfall_7d=rainfall_data.get("rainfall_7d"),
            twi=static_profile["terrain"].get("topographic_wetness_index"),
        )
        static_profile["soil"].update(dynamic_soil)

        # Dynamic geotechnical explainability reason codes
        if dynamic_soil.get("pore_water_pressure_kpa", 0.0) > 1.0:
            static_profile["explainability"]["reason_codes"].append({
                "code": "DYNAMIC_PORE_PRESSURE_ACCUMULATION",
                "description": (
                    f"Antecedent precipitation generated positive pore-water pressure "
                    f"({dynamic_soil['pore_water_pressure_kpa']:.1f} kPa), reducing effective "
                    f"normal stress and slope shear strength."
                ),
            })
        if dynamic_soil.get("factor_of_safety", 2.0) <= 1.20:
            static_profile["explainability"]["reason_codes"].append({
                "code": "LIMIT_EQUILIBRIUM_SLOPE_INSTABILITY",
                "description": (
                    f"Geotechnical Factor of Safety ({dynamic_soil['factor_of_safety']:.2f}) "
                    f"is approaching or below failure equilibrium (FoS <= 1.0)."
                ),
            })

        # 3b. Dynamic Anthropogenic & Human Factors Analysis (Pillar ④)
        anthropogenic = compute_anthropogenic_impact(
            natural_slope_deg=static_profile["terrain"].get("slope_deg"),
            landcover_class=static_profile["landcover"].get("landcover_class"),
            base_cohesion_kpa=dynamic_soil.get("effective_cohesion_kpa"),
            friction_angle_deg=dynamic_soil.get("friction_angle_deg"),
            pore_water_pressure_kpa=dynamic_soil.get("pore_water_pressure_kpa", 0.0),
            slope_position=static_profile["terrain"].get("slope_position"),
            road_cut_present=road_cut_present,
            cut_slope_deg=cut_slope_deg,
            drainage_blocked=drainage_blocked,
            unsupported_excavation=unsupported_excavation,
            deforestation_observed=deforestation_observed,
            has_retaining_wall=has_retaining_wall,
        )
        static_profile["anthropogenic"] = anthropogenic

        # 4. Evaluate Dynamic Rainfall Trigger
        rainfall_trigger = self.trigger_engine.evaluate_rainfall(rainfall_data)

        # 5. Fuse Static Susceptibility and Dynamic Trigger
        fusion_result = self.fusion_engine.fuse_risk(
            static_profile=static_profile,
            rainfall_trigger=rainfall_trigger,
        )

        # 6. Assemble Integrated Contract Response
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
                "anthropogenic": anthropogenic,
                "reason_codes": static_profile["explainability"]["reason_codes"],
            },
            "rainfall": rainfall_data,
            "rainfall_trigger": rainfall_trigger,
            "risk": fusion_result,
            "anthropogenic": anthropogenic,
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
    auto_refetch: bool = False,
    road_cut_present: bool = False,
    cut_slope_deg: Optional[float] = None,
    drainage_blocked: bool = False,
    unsupported_excavation: bool = False,
    deforestation_observed: bool = False,
    has_retaining_wall: bool = False,
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
        auto_refetch=auto_refetch,
        road_cut_present=road_cut_present,
        cut_slope_deg=cut_slope_deg,
        drainage_blocked=drainage_blocked,
        unsupported_excavation=unsupported_excavation,
        deforestation_observed=deforestation_observed,
        has_retaining_wall=has_retaining_wall,
    )
