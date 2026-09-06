"""
FastAPI REST API Service for LandslideNEI (Phase 8I)
=====================================================
Exposes the validated Phase 8G static susceptibility engine and Phase 8H
dynamic rainfall telemetry and deterministic risk fusion engine through
a unified, stable, production-grade JSON API.

Architecture:
- CLIENT -> FASTAPI -> UNIFIED RISK ENGINE -> STABLE JSON CONTRACT
- Thin API Layer: Request validation, error normalization, response formatting.
- Business Logic: Encapsulated exclusively in src.inference.
- Models & Providers: Initialized once per process; zero per-request disk reloading.
- Security: Safe CORS defaults, no stack traces leaked, server-side thresholds.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.schemas import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    InfoResponse,
    LocationBlock,
    PredictRequest,
    PredictResponse,
    ProfileRequest,
    ProfileResponse,
    RequestEcho,
    StaticSusceptibilityBlock,
    TerrainBlock,
    SoilBlock,
    LandcoverBlock,
    FreshnessBlock,
    IMDMacroContextBlock,
    RainfallBlock,
    RainfallTriggerBlock,
    RiskBlock,
    ModelMetadataBlock,
)
from src.inference.location_profiler import LocationProfiler
from src.inference.rainfall_provider import RainfallProvider, get_rainfall_provider
from src.inference.risk_engine import RiskEngine, get_risk_engine

# ==============================================================================
# 1. CONFIGURATION & APP INITIALIZATION
# ==============================================================================

CONFIG_API_FILE = PROJECT_ROOT / "config" / "api.json"
CONFIG_THRESHOLDS_FILE = PROJECT_ROOT / "config" / "risk_thresholds.json"


def _load_api_config() -> Dict[str, Any]:
    if CONFIG_API_FILE.exists():
        try:
            with open(CONFIG_API_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "api_version": "1.0.0",
        "title": "LandslideNEI Operational Landslide Risk Prediction API",
        "description": "Production-style operational landslide susceptibility and dynamic rainfall risk early-warning API for Northeast India.",
        "cors_origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    }


API_CONFIG = _load_api_config()
API_VERSION = API_CONFIG.get("api_version", "1.0.0")

app = FastAPI(
    title=API_CONFIG.get("title", "LandslideNEI Operational Landslide Risk Prediction API"),
    description=API_CONFIG.get("description", "Unified Operational Landslide Prediction API"),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Policy: Safe configuration via config/api.json or environment variable
env_cors = os.environ.get("CORS_ORIGINS")
if env_cors:
    allowed_origins = [o.strip() for o in env_cors.split(",") if o.strip()]
else:
    allowed_origins = API_CONFIG.get("cors_origins", [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=API_CONFIG.get("allow_credentials", True),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ==============================================================================
# 2. ERROR HANDLING & EXCEPTION CLASSES
# ==============================================================================

class APIError(Exception):
    """Structured application error with stable machine-readable code."""
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Check if errors relate to coordinates
    errs = exc.errors()
    is_coord = any(loc in str(err.get("loc", "")) for err in errs for loc in ["latitude", "longitude"])
    code = "INVALID_COORDINATES" if is_coord else "VALIDATION_ERROR"
    first_msg = errs[0].get("msg", "Validation failed") if errs else "Request validation failed"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": code,
                "message": f"Validation error: {first_msg}",
                "details": errs,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never expose Python tracebacks to external API clients
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred while processing the request.",
                "details": None,
            }
        },
    )


# ==============================================================================
# 3. HELPER FUNCTIONS: TIMESTAMP & FORMATTING
# ==============================================================================

def validate_and_parse_timestamp(raw_ts: Optional[str]) -> Tuple[datetime, str]:
    """
    Validate ISO-8601 timestamp with explicit timezone.
    If raw_ts is None, returns current UTC time.
    Rejects ambiguous naive timestamps.
    """
    if raw_ts is None:
        now_utc = datetime.now(timezone.utc)
        return now_utc, now_utc.isoformat()

    if not isinstance(raw_ts, str) or not raw_ts.strip():
        raise APIError(
            code="INVALID_TIMESTAMP",
            message="Timestamp must be a non-empty ISO-8601 string.",
            status_code=400,
            details={"raw_timestamp": raw_ts},
        )

    ts_str = raw_ts.strip()
    # Normalize trailing 'Z' for Python 3.10 fromisoformat compatibility
    parseable = ts_str.replace("Z", "+00:00") if ts_str.endswith("Z") else ts_str

    try:
        dt = datetime.fromisoformat(parseable)
    except Exception as exc:
        raise APIError(
            code="INVALID_TIMESTAMP",
            message="Malformed timestamp format. Must be a valid ISO-8601 datetime (e.g. '2026-09-02T09:00:00Z').",
            status_code=400,
            details={"raw_timestamp": raw_ts, "parse_error": str(exc)},
        )

    if dt.tzinfo is None:
        raise APIError(
            code="INVALID_TIMESTAMP",
            message=(
                "Timestamp must include explicit timezone offset (e.g. 'Z' for UTC or '+05:30'). "
                "Ambiguous local naive timestamps are rejected."
            ),
            status_code=400,
            details={"raw_timestamp": raw_ts},
        )

    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc, raw_ts


# ==============================================================================
# 4. API ENDPOINTS
# ==============================================================================

@app.get("/", tags=["General"])
def root() -> Dict[str, Any]:
    """API identification and operational overview."""
    return {
        "name": API_CONFIG.get("title", "LandslideNEI Operational Landslide Risk Prediction API"),
        "status": "online",
        "api_version": API_VERSION,
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "info_url": "/api/v1/info",
        "predict_url": "/api/v1/predict",
        "profile_url": "/api/v1/profile",
        "architecture": "FastAPI -> Model A Static LSM + CWC/IMD Telemetry Tier -> Deterministic Risk Fusion",
        "scientific_disclaimer": (
            "Operational risk levels and operational fusion scores are an engineering synthesis "
            "for ordering and decision-support. They are not calibrated statistical event probabilities."
        ),
    }


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
)
def health_check() -> HealthResponse:
    """
    Lightweight health probe verifying model and data provider readiness.
    Does NOT invoke full raster inference.
    """
    try:
        engine = get_risk_engine()
        # Verify static model pipeline is loaded in memory
        model_loaded = (
            engine.profiler.pipeline is not None
            and hasattr(engine.profiler.pipeline, "predict_proba")
        )
        rainfall_ready = engine.rainfall_provider.stations_count > 0
        provider_status = "ready" if rainfall_ready else "degraded"
    except Exception as exc:
        raise APIError(
            code="HEALTH_CHECK_FAILED",
            message=f"Inference engines unavailable: {exc}",
            status_code=503,
        )

    return HealthResponse(
        status="ok" if (model_loaded and rainfall_ready) else "degraded",
        api_version=API_VERSION,
        model_loaded=model_loaded,
        static_model="Model A (Environmental Only Random Forest)",
        rainfall_provider=provider_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get(
    "/api/v1/info",
    response_model=InfoResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
)
def get_system_info() -> InfoResponse:
    """Returns safe model metadata, feature contracts, and operational thresholds."""
    rf_cfg = {}
    if CONFIG_THRESHOLDS_FILE.exists():
        try:
            with open(CONFIG_THRESHOLDS_FILE, "r", encoding="utf-8") as f:
                rf_cfg = json.load(f)
        except Exception:
            pass

    return InfoResponse(
        api_version=API_VERSION,
        name="LandslideNEI Operational Landslide Risk Prediction API",
        environment=os.environ.get("ENVIRONMENT", "production"),
        static_model={
            "name": "Model A (Environmental Only)",
            "algorithm": "RandomForestClassifier",
            "version": "1.0.0",
            "feature_count": 10,
            "features": [
                "elevation_m", "slope_deg", "aspect_deg", "relief_std_5x5_m",
                "soil_class", "clay_percent", "sand_percent", "silt_percent",
                "bulk_density_kg_dm3", "landcover_class"
            ],
            "spatial_cv_roc_auc": 0.8062,
            "spatial_cv_pr_auc": 0.7937,
            "score_interpretation": (
                "Uncalibrated static susceptibility score produced by the Phase 8F "
                "environmental-only Random Forest model. Represents terrain failure predisposition, "
                "not an event-time occurrence probability."
            ),
        },
        supported_geography=API_CONFIG.get("supported_geography", {
            "region": "Northeast India (NER)",
            "states": ["Arunachal Pradesh", "Assam", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"],
            "bounds": {"min_latitude": 21.5, "max_latitude": 29.5, "min_longitude": 89.5, "max_longitude": 97.5},
        }),
        susceptibility_categories={
            "LOW": "Score < 0.25 (Low predisposition to slope failure)",
            "MODERATE": "0.25 <= Score < 0.50 (Moderate predisposition)",
            "HIGH": "0.50 <= Score < 0.75 (Significant predisposition)",
            "VERY_HIGH": "Score >= 0.75 (Severe terrain predisposition)",
        },
        rainfall={
            "primary_source": "CWC Telemetry Stations",
            "active_stations": get_rainfall_provider().stations_count,
            "max_station_distance_km": 50.0,
            "max_freshness_age_hours": 6.0,
            "min_coverage_ratio": 0.75,
            "macro_context_source": "IMD Districtwise & Statewise Monitoring",
            "spatial_policy": (
                "Point queries strictly use CWC stations within <=50.0 km. IMD provides "
                "administrative macro context without coordinate fabrication."
            ),
        },
        operational_thresholds=rf_cfg.get("rainfall", {
            "threshold_type": "DEMO_OPERATIONAL_DEFAULT",
            "disclaimer": "Operational demonstration thresholds — not calibrated against historical landslide event rainfall.",
            "1h_mm": {"watch": 20.0, "high": 40.0},
            "24h_mm": {"watch": 50.0, "high": 100.0},
            "3d_mm": {"watch": 100.0, "high": 200.0},
            "7d_mm": {"watch": 150.0, "high": 300.0},
        }),
        risk_fusion={
            "method": "Deterministic Rule-Based Decision Matrix",
            "authoritative_output": "risk_level (LOW, WATCH, HIGH, CRITICAL)",
            "ordering_metric": "operational_fusion_score [0.0, 1.0]",
            "score_semantics": (
                "The operational_fusion_score is an engineering synthesis score used for ordering/visualization. "
                "It is not a probability, calibrated hazard score, or empirically validated landslide risk estimate."
            ),
        },
    )


@app.post(
    "/api/v1/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inference"],
)
def predict_risk(payload: PredictRequest) -> PredictResponse:
    """
    Unified Operational Landslide Risk Prediction Endpoint.
    Executes full pipeline:
    1. Static Susceptibility Profiling (Model A RF over Copernicus DEM + SoilGrids + WorldCover)
    2. Operational Rainfall Telemetry Matching (CWC Station <=50km, freshness <=6h)
    3. Multi-Window Dynamic Trigger Evaluation (1h, 24h, 3d, 7d)
    4. Deterministic Risk Fusion (Decision Matrix -> LOW/WATCH/HIGH/CRITICAL)
    """
    request_id = str(uuid.uuid4())
    dt_utc, effective_ts_str = validate_and_parse_timestamp(payload.timestamp)

    engine = get_risk_engine()

    try:
        eval_res = engine.evaluate_risk(
            latitude=payload.latitude,
            longitude=payload.longitude,
            timestamp=dt_utc,
            reference_time=dt_utc,
        )
    except Exception as exc:
        raise APIError(
            code="INFERENCE_ERROR",
            message=f"Risk evaluation failed unexpectedly: {exc}",
            status_code=500,
        )

    # Domain validation check
    if eval_res.get("status") == "OUTSIDE_SUPPORTED_DOMAIN":
        raise APIError(
            code="OUTSIDE_SUPPORTED_DOMAIN",
            message=eval_res.get("error", "Location lies outside supported Northeast India domain."),
            status_code=400,
            details=eval_res.get("location"),
        )
    elif eval_res.get("status") != "SUCCESS":
        raise APIError(
            code="INFERENCE_FAILED",
            message=eval_res.get("error", "Inference execution failed."),
            status_code=500,
            details={"status": eval_res.get("status")},
        )

    loc = eval_res["location"]
    susc = eval_res["static_susceptibility"]
    rf = eval_res["rainfall"]
    trig = eval_res["rainfall_trigger"]
    risk = eval_res["risk"]

    # Assemble structured Pydantic response
    return PredictResponse(
        api_version=API_VERSION,
        request_id=request_id,
        request=RequestEcho(
            latitude=payload.latitude,
            longitude=payload.longitude,
            timestamp=effective_ts_str,
        ),
        location=LocationBlock(
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            state=loc.get("state"),
            district=loc.get("district") or rf.get("district"),
            country=loc.get("country", "India"),
            supported_domain=loc.get("supported_domain", True),
        ),
        static_susceptibility=StaticSusceptibilityBlock(
            score=susc["score"],
            category=susc["category"],
            category_label=susc["category_label"],
            category_description=susc["category_description"],
            quality_status=susc["quality_status"],
            terrain=TerrainBlock(**susc["terrain"]),
            soil=SoilBlock(**susc["soil"]),
            landcover=LandcoverBlock(**susc["landcover"]),
            reasons=susc["reason_codes"],
        ),
        rainfall=RainfallBlock(
            source=rf.get("source", "CWC"),
            station=rf.get("station"),
            station_key=rf.get("station_key"),
            state=rf.get("state"),
            district=rf.get("district"),
            distance_km=rf.get("distance_km"),
            max_acceptable_distance_km=rf.get("max_acceptable_distance_km", 50.0),
            timestamp=rf.get("timestamp"),
            rainfall_1h=rf.get("rainfall_1h"),
            rainfall_24h=rf.get("rainfall_24h"),
            rainfall_3d=rf.get("rainfall_3d"),
            rainfall_7d=rf.get("rainfall_7d"),
            coverage_24h=rf.get("coverage_24h"),
            coverage_3d=rf.get("coverage_3d"),
            coverage_7d=rf.get("coverage_7d"),
            quality=rf.get("quality", "UNKNOWN"),
            status=rf.get("status", "UNKNOWN"),
            quality_notes=rf.get("quality_notes", ""),
            freshness=FreshnessBlock(**rf.get("freshness", {
                "freshness_status": "UNKNOWN",
                "max_acceptable_age_hours": 6.0,
            })),
            imd_macro_context=IMDMacroContextBlock(**rf["imd_macro_context"]) if rf.get("imd_macro_context") else None,
        ),
        rainfall_trigger=RainfallTriggerBlock(
            level=trig.get("trigger_level", "NO_DATA"),
            trigger_level=trig.get("trigger_level", "NO_DATA"),
            trigger_score=trig.get("trigger_score"),
            reasons=trig.get("trigger_reasons", []),
            trigger_reasons=trig.get("trigger_reasons", []),
            thresholds_breached=trig.get("thresholds_breached", []),
            multi_window_summary=trig.get("multi_window_summary", {}),
            data_quality=trig.get("data_quality", {}),
        ),
        risk=RiskBlock(
            level=risk.get("risk_level", "LOW"),
            risk_level=risk.get("risk_level", "LOW"),
            risk_label=risk.get("risk_label", "Low Operational Risk"),
            operational_fusion_score=risk.get("operational_fusion_score", 0.0),
            risk_score=risk.get("risk_score", 0.0),
            score_semantics=risk.get("score_semantics", ""),
            scoring_mode=risk.get("scoring_mode", "UNKNOWN"),
            susceptibility_score=risk.get("susceptibility_score", 0.0),
            susceptibility_category=risk.get("susceptibility_category", "LOW"),
            rainfall_trigger_level=risk.get("rainfall_trigger_level", "NO_DATA"),
            rainfall_trigger_score=risk.get("rainfall_trigger_score"),
            reasons=risk.get("reasons", []),
            operational_action=risk.get("operational_action", ""),
            matrix_lookup=risk.get("matrix_lookup", {}),
        ),
        model=ModelMetadataBlock(
            name="LandslideNEI Operational Risk Engine",
            version=API_VERSION,
            static_model="Model A (Environmental Only Random Forest)",
            threshold_profile="DEMO_OPERATIONAL_DEFAULT",
            rainfall_architecture="Decoupled Operational Telemetry Tier",
            fusion_method="Deterministic Rule-Based Decision Matrix",
        ),
        limitations=eval_res.get("scientific_limitations", []),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/api/v1/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inference"],
)
def profile_location_endpoint(payload: ProfileRequest) -> ProfileResponse:
    """
    Static-Only Susceptibility Profile Endpoint.
    Uses Phase 8G LocationProfiler directly without rainfall telemetry fusion.
    """
    request_id = str(uuid.uuid4())
    engine = get_risk_engine()

    try:
        profile = engine.profiler.profile_location(payload.latitude, payload.longitude)
    except Exception as exc:
        raise APIError(
            code="INFERENCE_ERROR",
            message=f"Location profiling failed unexpectedly: {exc}",
            status_code=500,
        )

    if profile.get("status") == "OUTSIDE_SUPPORTED_DOMAIN":
        raise APIError(
            code="OUTSIDE_SUPPORTED_DOMAIN",
            message=profile.get("error", "Location lies outside supported Northeast India domain."),
            status_code=400,
            details=profile.get("location"),
        )
    elif profile.get("status") != "SUCCESS":
        raise APIError(
            code="INFERENCE_FAILED",
            message=profile.get("error", "Profiling failed."),
            status_code=500,
        )

    loc = profile["location"]
    susc = profile["susceptibility"]

    return ProfileResponse(
        api_version=API_VERSION,
        request_id=request_id,
        location=LocationBlock(
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            state=loc.get("state"),
            district=loc.get("district"),
            country=loc.get("country", "India"),
            supported_domain=loc.get("supported_domain", True),
        ),
        static_susceptibility=StaticSusceptibilityBlock(
            score=susc["score"],
            category=susc["category"],
            category_label=susc["category_label"],
            category_description=susc["category_description"],
            quality_status=profile["quality"]["status"],
            terrain=TerrainBlock(**profile["terrain"]),
            soil=SoilBlock(**profile["soil"]),
            landcover=LandcoverBlock(**profile["landcover"]),
            reasons=profile["explainability"]["reason_codes"],
        ),
        model={
            "name": "Model A (Environmental Only)",
            "type": "STATIC_SUSCEPTIBILITY_ONLY",
            "version": API_VERSION,
        },
        limitations=profile.get("metadata", {}).get("notes", []),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ==============================================================================
# 5. BACKWARD-COMPATIBILITY ALIASES
# ==============================================================================

@app.get("/health", tags=["General"], include_in_schema=False)
def legacy_health_check():
    """Alias for /api/v1/health."""
    return health_check()


@app.get("/model-info", tags=["Metadata"], include_in_schema=False)
def legacy_model_info():
    """Alias for /api/v1/info."""
    return get_system_info()


if __name__ == "__main__":
    import uvicorn
    host = API_CONFIG.get("host", "127.0.0.1")
    port = int(API_CONFIG.get("port", 8000))
    uvicorn.run("api.main:app", host=host, port=port, reload=True)
