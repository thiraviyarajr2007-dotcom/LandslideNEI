# Phase 8I — Unified Risk API & Operational Prediction Contract

**Project**: SIH Landslide AI Early-Warning & Decision-Support System  
**Repository**: `thiraviyarajr2007-dotcom/LandslideNEI`  
**Base Checkpoint**: `df1a09d` (`feat: add dynamic rainfall and risk fusion layer`)  
**API Version**: `1.0.0`

---

## 1. Architectural Overview & Design Principles

The LandslideNEI Risk API provides a stable, production-grade operational prediction contract that synthesizes the static landslide susceptibility model (Phase 8F/8G) with real-time dynamic rainfall telemetry and heuristic risk fusion (Phase 8H).

```
CLIENT APPLICATION (Dashboard / CLI / Alerting System)
                     │
                     ▼
          FastAPI Layer (api/main.py)
   ┌──────────────────────────────────────────────┐
   │ • Safe CORS & Error Sanitization (No Leaks)  │
   │ • ISO-8601 Strict Timezone Enforcement       │
   │ • Fast Health Probe (Zero Raster I/O)        │
   └──────────────────────┬───────────────────────┘
                          │
                          ▼
            Inference Layer (src/inference/)
   ┌──────────────────────────────────────────────┐
   │ 1. Domain Validator (NER Bounding Box)       │
   │ 2. LocationProfiler (Phase 8G Static LSM)    │
   │    - 5x5 DEM (Elevation, Horn Slope, Aspect) │
   │    - SoilGrids (Clay, Sand, Silt, Density)   │
   │    - ESA WorldCover 2021 (11 classes)        │
   │    - Frozen Model A Pipeline                 │
   │ 3. RainfallTelemetryProvider (Phase 8H)      │
   │    - CWC Station Telemetry (<= 50 km Cap)    │
   │    - Freshness Tracking (<= 6 h SLA)         │
   │    - IMD Macro Context (State/District Only) │
   │ 4. Deterministic Risk Fusion (Phase 8H)      │
   │    - Decision Matrix (Static x Rainfall)     │
   │    - Operational Risk Tier (Authoritative)   │
   │    - Non-Probabilistic Ordering Synthesis    │
   └──────────────────────────────────────────────┘
```

### Core Invariants & Guardrails
1. **Thin API Layer**: The API layer (`api/main.py`, `api/schemas.py`) strictly handles serialization, validation, CORS, and error sanitization. All domain logic resides in `src/inference/`.
2. **Frozen Model A Contract**: Model A (`model/static_lsm_pipeline.joblib`) is treated as a read-only artifact. Static features are identical to Phase 8F/8G.
3. **Decoupled Rainfall Tier**: Rainfall telemetry is handled independently. Unobserved rainfall is returned as explicit `null` and never converted to `0.0 mm`.
4. **Spatial & Freshness Boundaries**: CWC telemetry is strictly capped at a 50 km radius. Observations older than 6 hours are flagged as `STALE`.
5. **Macro Context Honesty**: IMD rainfall data provides administrative context only and is never fabricated as localized point rainfall.
6. **Authoritative Discrete Tier**: `risk_level` (`LOW`, `WATCH`, `HIGH`, `CRITICAL`) is the authoritative operational decision. `operational_fusion_score` is a heuristic ordering metric for visualization, not a calibrated event probability.
7. **Secure Error Handling**: Internal stack traces and local server paths are intercepted and sanitized before returning to the client.

---

## 2. Centralized Configuration (`config/api.json`)

```json
{
  "api_version": "1.0.0",
  "host": "0.0.0.0",
  "port": 8000,
  "cors_origins": [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
  ],
  "allow_credentials": true,
  "supported_geography": {
    "region": "Northeast India (NER)",
    "min_latitude": 21.5,
    "max_latitude": 29.5,
    "min_longitude": 89.5,
    "max_longitude": 97.5
  }
}
```

---

## 3. Endpoints Specification

### 3.1. Health Check Probe
- **Endpoint**: `GET /api/v1/health`
- **Description**: Lightweight liveness and readiness probe for load balancers. Validates that the static LSM model pipeline is loaded in memory without triggering expensive raster I/O.
- **Status Code**: `200 OK`

#### Response Schema (`HealthResponse`):
```json
{
  "status": "ok",
  "api_version": "1.0.0",
  "model_loaded": true,
  "static_model": "Model A (Environmental Only)",
  "rainfall_provider": "ready",
  "timestamp": "2026-09-06T07:53:00.000000+00:00"
}
```

---

### 3.2. System Capabilities & Metadata
- **Endpoint**: `GET /api/v1/info`
- **Description**: Exposes model metadata, feature contracts, supported geographic bounds, operational thresholds, and non-probabilistic disclaimers.
- **Status Code**: `200 OK`

#### Response Schema (`InfoResponse`):
```json
{
  "api_version": "1.0.0",
  "name": "LandslideNEI Operational Early Warning System API",
  "environment": "production",
  "static_model": {
    "name": "Model A (Environmental Only)",
    "algorithm": "RandomForestClassifier",
    "artifact": "model/static_lsm_pipeline.joblib",
    "features": [
      "elevation_m", "slope_deg", "aspect_deg", "relief_std_5x5_m",
      "clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3",
      "landcover_code"
    ]
  },
  "supported_geography": {
    "region": "Northeast India (NER)",
    "bounds": {
      "min_latitude": 21.5,
      "max_latitude": 29.5,
      "min_longitude": 89.5,
      "max_longitude": 97.5
    }
  },
  "susceptibility_categories": {
    "LOW": "0.00 - 0.25",
    "MODERATE": "0.25 - 0.50",
    "HIGH": "0.50 - 0.75",
    "VERY_HIGH": "0.75 - 1.00"
  },
  "rainfall": {
    "primary_source": "Central Water Commission (CWC) Telemetry",
    "macro_context_source": "India Meteorological Department (IMD) Administrative Bulletins",
    "max_acceptable_distance_km": 50.0,
    "max_acceptable_age_hours": 6.0,
    "threshold_profile": "DEMO_OPERATIONAL_DEFAULT"
  },
  "disclaimers": [
    "Operational decision-support synthesis, not a certified event-time warning or probabilistic guarantee.",
    "Static susceptibility score is an uncalibrated terrain predisposition estimate from Model A.",
    "Rainfall thresholds are heuristic operational defaults (DEMO_OPERATIONAL_DEFAULT), not historically calibrated landslide trigger thresholds."
  ]
}
```

---

### 3.3. Unified Operational Prediction
- **Endpoint**: `POST /api/v1/predict`
- **Description**: Evaluates static terrain predisposition and fuses it with real-time rainfall telemetry from nearby CWC stations and IMD macro context.
- **Status Code**: `200 OK`

#### Request Schema (`PredictRequest`):
```json
{
  "latitude": 26.1445,
  "longitude": 91.7362,
  "timestamp": "2026-09-02T09:00:00Z"
}
```
*Note: If `timestamp` is omitted, the API defaults to the current UTC time. Timezone-naive timestamp strings are rejected with HTTP 422.*

#### Response Schema (`PredictResponse`):
```json
{
  "api_version": "1.0.0",
  "request_id": "c71a3962-e923-41c0-a7d5-e9db98e72304",
  "request": {
    "latitude": 26.1445,
    "longitude": 91.7362,
    "timestamp": "2026-09-02T09:00:00+00:00"
  },
  "location": {
    "latitude": 26.1445,
    "longitude": 91.7362,
    "state": "Assam",
    "district": "Kamrup Metropolitan",
    "country": "India",
    "supported_domain": true
  },
  "static_susceptibility": {
    "score": 0.0467,
    "category": "LOW",
    "category_label": "Low Static Susceptibility",
    "category_description": "Static terrain susceptibility estimate (uncalibrated Random Forest score; not an event-time warning or percentage probability of occurrence).",
    "quality_status": "COMPLETE",
    "terrain": {
      "elevation_m": 54.0,
      "slope_deg": 1.24,
      "aspect_deg": 142.1,
      "relief_std_5x5_m": 1.8
    },
    "soil": {
      "soil_class": "Cambisols",
      "clay_percent": 21.4,
      "sand_percent": 45.2,
      "silt_percent": 33.4,
      "bulk_density_kg_dm3": 1.38
    },
    "landcover": {
      "landcover_code": 50,
      "landcover_class": "Built-up"
    },
    "reasons": [
      {
        "factor": "slope",
        "description": "Gentle slope (< 10 deg) provides low gravitational driving stress."
      }
    ]
  },
  "rainfall": {
    "source": "CWC",
    "station": "Guwahati",
    "station_key": "CWC_GUWAHATI",
    "state": "Assam",
    "district": "Kamrup Metropolitan",
    "distance_km": 4.21,
    "max_acceptable_distance_km": 50.0,
    "timestamp": "2022-06-18T00:00:00",
    "rainfall_1h": null,
    "rainfall_24h": 42.0,
    "rainfall_3d": 115.0,
    "rainfall_7d": 210.0,
    "coverage_24h": 1.0,
    "coverage_3d": 1.0,
    "coverage_7d": 1.0,
    "quality": "STALE",
    "status": "STALE",
    "freshness": {
      "observation_timestamp": "2022-06-18T00:00:00",
      "reference_timestamp": "2026-09-02T09:00:00+00:00",
      "age_hours": 36873.0,
      "freshness_status": "STALE",
      "max_acceptable_age_hours": 6.0
    },
    "imd_context": {
      "source": "IMD",
      "scope": "DISTRICT",
      "state": "Assam",
      "district": "Kamrup Metropolitan",
      "date": "2026-09-02",
      "daily_actual_mm": 12.5,
      "daily_normal_mm": 9.8,
      "departure_percent": 27.55,
      "status": "NORMAL",
      "disclaimer": "Macro-level district context only; not point rainfall telemetry."
    }
  },
  "rainfall_trigger": {
    "level": "NORMAL",
    "trigger_level": "NORMAL",
    "trigger_score": 0.25,
    "reasons": [
      {
        "code": "RAINFALL_NORMAL",
        "description": "Rainfall accumulations are within normal operational limits."
      }
    ],
    "trigger_reasons": [
      {
        "code": "RAINFALL_NORMAL",
        "description": "Rainfall accumulations are within normal operational limits."
      }
    ],
    "thresholds_breached": [],
    "multi_window_summary": {
      "1h": {"observed_mm": null, "status": "NO_DATA"},
      "24h": {"observed_mm": 42.0, "status": "WATCH_BREACHED"},
      "3d": {"observed_mm": 115.0, "status": "NORMAL"},
      "7d": {"observed_mm": 210.0, "status": "NORMAL"}
    },
    "data_quality": {
      "stale": true,
      "sparse": false
    }
  },
  "risk": {
    "level": "LOW",
    "risk_level": "LOW",
    "risk_label": "Low Operational Risk",
    "operational_fusion_score": 0.1483,
    "risk_score": 0.1483,
    "score_semantics": "Continuous engineering synthesis score for spatial prioritization and ranking; not a calibrated event probability. The discrete risk_level is the authoritative operational decision.",
    "scoring_mode": "FUSION_FULL",
    "susceptibility_score": 0.0467,
    "susceptibility_category": "LOW",
    "rainfall_trigger_level": "NORMAL",
    "rainfall_trigger_score": 0.25,
    "reasons": [
      {
        "code": "SUSC_LOW",
        "description": "Static terrain susceptibility is LOW."
      }
    ],
    "operational_action": "Routine operational monitoring.",
    "matrix_lookup": {
      "susceptibility": "LOW",
      "rainfall_trigger": "NORMAL",
      "resulting_risk": "LOW"
    }
  },
  "model": {
    "name": "LandslideNEI Operational Risk Engine",
    "version": "1.0.0",
    "static_model": "Model A (Environmental Only Random Forest)",
    "threshold_profile": "DEMO_OPERATIONAL_DEFAULT",
    "rainfall_architecture": "Decoupled Operational Telemetry Tier",
    "fusion_method": "Deterministic Rule-Based Decision Matrix"
  },
  "limitations": [
    "Static susceptibility is an uncalibrated terrain predisposition score, not a probability.",
    "Rainfall trigger thresholds are heuristic operational defaults (DEMO_OPERATIONAL_DEFAULT).",
    "Operational fusion score represents an engineering ordering synthesis, not an event likelihood."
  ],
  "generated_at": "2026-09-06T07:53:01.123456+00:00"
}
```

---

### 3.4. Static-Only Susceptibility Profiling
- **Endpoint**: `POST /api/v1/profile`
- **Description**: Fast profiling endpoint executing Phase 8G static LSM feature extraction and model scoring without calling rainfall providers or fusion matrix.
- **Status Code**: `200 OK`

#### Request Schema (`ProfileRequest`):
```json
{
  "latitude": 27.5925,
  "longitude": 91.6087
}
```

#### Response Schema (`ProfileResponse`):
```json
{
  "api_version": "1.0.0",
  "request_id": "84310d7a-cfb3-4f9e-9d29-02caef5db811",
  "location": {
    "latitude": 27.5925,
    "longitude": 91.6087,
    "state": "Arunachal Pradesh",
    "district": "Tawang",
    "country": "India",
    "supported_domain": true
  },
  "static_susceptibility": {
    "score": 0.6842,
    "category": "HIGH",
    "category_label": "High Static Susceptibility",
    "category_description": "Static terrain susceptibility estimate (uncalibrated Random Forest score; not an event-time warning or percentage probability of occurrence).",
    "quality_status": "COMPLETE",
    "terrain": {
      "elevation_m": 3025.0,
      "slope_deg": 31.4,
      "aspect_deg": 215.8,
      "relief_std_5x5_m": 48.2
    },
    "soil": {
      "soil_class": "Podzols",
      "clay_percent": 15.2,
      "sand_percent": 62.1,
      "silt_percent": 22.7,
      "bulk_density_kg_dm3": 1.15
    },
    "landcover": {
      "landcover_code": 10,
      "landcover_class": "Tree cover"
    },
    "reasons": [
      {
        "factor": "slope",
        "description": "Steep terrain (> 30 deg) significantly elevates gravitational shear stress."
      }
    ]
  },
  "model": {
    "name": "Model A (Environmental Only)",
    "version": "1.0.0",
    "pipeline_artifact": "model/static_lsm_pipeline.joblib"
  },
  "limitations": [
    "Static susceptibility represents long-term terrain predisposition only.",
    "Dynamic triggers (rainfall, seismic activity) are not accounted for in this profile."
  ],
  "generated_at": "2026-09-06T07:53:02.000000+00:00"
}
```

---

## 4. Error Handling Contract

All error responses adhere to a standardized, machine-readable JSON structure.

### Error Response Schema (`ErrorResponse`):
```json
{
  "error": {
    "code": "OUTSIDE_NER_DOMAIN",
    "message": "Coordinates (28.6139, 77.209) are outside supported Northeast India domain.",
    "details": {
      "supported_bounds": {
        "min_latitude": 21.5,
        "max_latitude": 29.5,
        "min_longitude": 89.5,
        "max_longitude": 97.5
      }
    }
  }
}
```

### Standard Error Codes:
| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `OUTSIDE_NER_DOMAIN` | Requested location falls outside the 8 NER states bounding box. |
| `422 Unprocessable` | `INVALID_COORDINATES` | Latitude not in `[-90, 90]` or longitude not in `[-180, 180]`. |
| `422 Unprocessable` | `INVALID_TIMESTAMP_FORMAT` | Timestamp string cannot be parsed as valid ISO-8601. |
| `422 Unprocessable` | `NAIVE_TIMESTAMP_REJECTED` | Timestamp string lacks explicit UTC timezone offset (e.g. `Z` or `+05:30`). |
| `422 Unprocessable` | `VALIDATION_ERROR` | Schema failure on request body fields. |
| `500 Internal Error` | `INFERENCE_FAILED` | Pipeline failure during feature extraction or model prediction. |
| `500 Internal Error` | `INTERNAL_ERROR` | Unexpected unhandled exception (sanitized; no stack traces leaked). |
| `503 Service Unavailable`| `SERVICE_UNAVAILABLE` | Static model artifact or raster data files cannot be loaded. |

---

## 5. Scientific Limitations & Disclaimers

1. **Non-Probabilistic Semantics**:
   - The static susceptibility score is an uncalibrated Random Forest classification score reflecting terrain predisposition.
   - The operational fusion score is an engineering synthesis for relative spatial ranking across sites. Neither metric represents a frequentist or Bayesian event probability.
2. **Authoritative Discrete Tier**:
   - Downstream emergency decision-makers must act on `risk_level` (`LOW`, `WATCH`, `HIGH`, `CRITICAL`) and not attempt to interpret decimals as confidence levels.
3. **Rainfall Trigger Status**:
   - The thresholds defined in `config/risk_thresholds.json` are operational heuristics (`DEMO_OPERATIONAL_DEFAULT`). They have not been empirically calibrated via historical landslide-rainfall trigger modeling.
4. **Spatial Representativeness**:
   - Point rainfall from CWC stations is valid only within a 50 km radius.
   - Stations beyond 50 km are discarded (`NO_DATA`).
   - IMD macro context is aggregated at the district or state level and must never be treated as local point telemetry.
