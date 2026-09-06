"""
Pydantic Schemas for LandslideNEI Operational API (Phase 8I)
===========================================================
Defines stable, strongly-typed request and response contracts for:
- POST /api/v1/predict (Unified Risk Prediction Contract)
- POST /api/v1/profile (Static Susceptibility Profile Contract)
- GET  /api/v1/health  (Operational Health Probe Contract)
- GET  /api/v1/info    (Model & System Metadata Contract)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# 1. ERROR SCHEMAS
# ==============================================================================

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable stable error code", example="OUTSIDE_SUPPORTED_DOMAIN")
    message: str = Field(..., description="Human-readable explanation of the error condition")
    details: Optional[Any] = Field(None, description="Optional structured contextual metadata")


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ==============================================================================
# 2. REQUEST SCHEMAS
# ==============================================================================

class PredictRequest(BaseModel):
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Target latitude in decimal degrees (-90.0 to 90.0)",
        example=27.5925,
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Target longitude in decimal degrees (-180.0 to 180.0)",
        example=91.6087,
    )
    timestamp: Optional[str] = Field(
        None,
        description="Optional observation timestamp in ISO-8601 format with explicit timezone (e.g. '2026-09-02T09:00:00Z' or '+05:30'). If omitted, current operational UTC time is used.",
        example="2026-09-02T09:00:00Z",
    )


class ProfileRequest(BaseModel):
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Target latitude in decimal degrees (-90.0 to 90.0)",
        example=27.5925,
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Target longitude in decimal degrees (-180.0 to 180.0)",
        example=91.6087,
    )


# ==============================================================================
# 3. RESPONSE SUB-BLOCKS
# ==============================================================================

class RequestEcho(BaseModel):
    latitude: float
    longitude: float
    timestamp: str


class LocationBlock(BaseModel):
    latitude: float
    longitude: float
    state: Optional[str] = None
    district: Optional[str] = None
    country: str = "India"
    supported_domain: bool


class TerrainBlock(BaseModel):
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    aspect_deg: Optional[float] = None
    relief_std_5x5_m: Optional[float] = None


class SoilBlock(BaseModel):
    soil_class: Optional[str] = None
    clay_percent: Optional[float] = None
    sand_percent: Optional[float] = None
    silt_percent: Optional[float] = None
    bulk_density_kg_dm3: Optional[float] = None


class LandcoverBlock(BaseModel):
    landcover_code: Optional[int] = None
    landcover_class: Optional[str] = None


class StaticSusceptibilityBlock(BaseModel):
    score: float = Field(..., description="Uncalibrated static susceptibility score [0.0, 1.0] from Phase 8F Model A")
    category: str = Field(..., description="Operational susceptibility tier (LOW, MODERATE, HIGH, VERY_HIGH)")
    category_label: str
    category_description: str
    quality_status: str
    terrain: TerrainBlock
    soil: SoilBlock
    landcover: LandcoverBlock
    reasons: List[Dict[str, str]]


class FreshnessBlock(BaseModel):
    observation_timestamp: Optional[str] = None
    reference_timestamp: Optional[str] = None
    age_hours: Optional[float] = None
    freshness_status: str
    max_acceptable_age_hours: float = 6.0


class IMDMacroContextBlock(BaseModel):
    source: str = "IMD"
    scope: str = Field(..., description="Macro aggregation level: 'STATE' or 'DISTRICT'")
    state: str
    district: Optional[str] = None
    date: str
    daily_actual_mm: Optional[float] = None
    daily_normal_mm: Optional[float] = None
    daily_departure_pct: Optional[float] = None
    category: Optional[str] = None
    integration_level: str


class RainfallBlock(BaseModel):
    source: str = Field("CWC", description="Primary operational telemetry source")
    station: Optional[str] = None
    station_key: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    distance_km: Optional[float] = None
    max_acceptable_distance_km: float = 50.0
    timestamp: Optional[str] = None
    rainfall_1h: Optional[float] = None
    rainfall_24h: Optional[float] = None
    rainfall_3d: Optional[float] = None
    rainfall_7d: Optional[float] = None
    coverage_24h: Optional[float] = None
    coverage_3d: Optional[float] = None
    coverage_7d: Optional[float] = None
    quality: str = Field(..., description="Data quality tier: GOOD, PARTIAL, MISSING, STALE, NO_RELIABLE_STATION")
    status: str = Field(..., description="Operational availability status: OK, STALE, MISSING, NO_RELIABLE_LOCAL_STATION")
    quality_notes: str
    freshness: FreshnessBlock
    imd_macro_context: Optional[IMDMacroContextBlock] = None


class RainfallTriggerBlock(BaseModel):
    level: str = Field(..., description="Trigger level: NORMAL, WATCH, HIGH, NO_DATA")
    trigger_level: str
    trigger_score: Optional[float] = Field(None, description="Continuous engineering metric [0.0, 1.0]; null if unobserved")
    reasons: List[Dict[str, str]]
    trigger_reasons: List[Dict[str, str]]
    thresholds_breached: List[Dict[str, Any]]
    multi_window_summary: Dict[str, Any]
    data_quality: Dict[str, Any]


class RiskBlock(BaseModel):
    level: str = Field(..., description="Authoritative operational risk tier: LOW, WATCH, HIGH, CRITICAL")
    risk_level: str
    risk_label: str
    operational_fusion_score: float = Field(..., description="Engineering synthesis score for ordering/visualization [0.0, 1.0]")
    risk_score: float = Field(..., description="Backwards-compatible alias for operational_fusion_score")
    score_semantics: str = Field(..., description="Explicit non-probabilistic synthesis disclaimer")
    scoring_mode: str
    susceptibility_score: float
    susceptibility_category: str
    rainfall_trigger_level: str
    rainfall_trigger_score: Optional[float] = None
    reasons: List[Dict[str, str]]
    operational_action: str
    matrix_lookup: Dict[str, str]


class ModelMetadataBlock(BaseModel):
    name: str = "LandslideNEI Operational Risk Engine"
    version: str = "1.0.0"
    static_model: str = "Model A (Environmental Only Random Forest)"
    threshold_profile: str = "DEMO_OPERATIONAL_DEFAULT"
    rainfall_architecture: str = "Decoupled Operational Telemetry Tier"
    fusion_method: str = "Deterministic Rule-Based Decision Matrix"


# ==============================================================================
# 4. PRIMARY TOP-LEVEL API RESPONSES
# ==============================================================================

class PredictResponse(BaseModel):
    api_version: str = "1.0.0"
    request_id: str
    request: RequestEcho
    location: LocationBlock
    static_susceptibility: StaticSusceptibilityBlock
    rainfall: RainfallBlock
    rainfall_trigger: RainfallTriggerBlock
    risk: RiskBlock
    model: ModelMetadataBlock
    limitations: List[str]
    generated_at: str


class ProfileResponse(BaseModel):
    api_version: str = "1.0.0"
    request_id: str
    location: LocationBlock
    static_susceptibility: StaticSusceptibilityBlock
    model: Dict[str, str]
    limitations: List[str]
    generated_at: str


class HealthResponse(BaseModel):
    status: str = "ok"
    api_version: str = "1.0.0"
    model_loaded: bool = True
    static_model: str
    rainfall_provider: str = "ready"
    timestamp: str


class InfoResponse(BaseModel):
    api_version: str = "1.0.0"
    name: str
    environment: str
    static_model: Dict[str, Any]
    supported_geography: Dict[str, Any]
    susceptibility_categories: Dict[str, str]
    rainfall: Dict[str, Any]
    operational_thresholds: Dict[str, Any]
    risk_fusion: Dict[str, Any]
