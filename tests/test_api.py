"""
Comprehensive API Contract Test Suite (Phase 8I)
=================================================
Validates the unified FastAPI prediction contract according to all
Phase 8I operational and scientific requirements:
1.  GET /api/v1/health
2.  GET /api/v1/info
3.  POST /api/v1/predict with valid NER coordinate (Guwahati)
4.  POST /api/v1/predict with Tawang (>50km CWC)
5.  POST /api/v1/predict outside NER (New Delhi)
6.  Invalid latitude validation
7.  Invalid longitude validation
8.  Malformed timestamp rejection
9.  Timezone-aware timestamp acceptance
10. Ambiguous naive timestamp rejection
11. Omitted timestamp handling (UTC default)
12. Stable response schema verification
13. Request ID UUID4 presence & traceability
14. API version consistency ("1.0.0")
15. Static susceptibility contract & non-probability semantics
16. Rainfall telemetry contract & unobserved nulls
17. Dynamic rainfall trigger contract
18. Risk block contract & operational_fusion_score bounds
19. Missing rainfall is not converted to 0.0
20. Stale rainfall remains explicitly flagged
21. No-reliable-station remains explicitly flagged
22. IMD macro context does not become point rainfall
23. Standardized error structure {error: {code, message, details}}
24. Zero Python tracebacks leaked to client
25. Health probe does not execute full raster inference
26. POST /api/v1/profile static-only endpoint
27. Configurable safe CORS headers
"""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.inference.risk_engine import get_risk_engine


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# 1. SYSTEM ENDPOINTS
# ==============================================================================

def test_health_endpoint(client):
    """1 & 25: Health check probe returns 200 without running full raster inference."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert data["api_version"] == "1.0.0"
    assert data["model_loaded"] is True
    assert "Model A" in data["static_model"]
    assert data["rainfall_provider"] == "ready"
    assert "timestamp" in data


def test_health_does_not_invoke_full_inference(client, monkeypatch):
    """25: Verify health check probe does not call profile_location."""
    called = False

    def mock_profile(*args, **kwargs):
        nonlocal called
        called = True
        raise RuntimeError("profile_location should not be called in health check!")

    engine = get_risk_engine()
    monkeypatch.setattr(engine.profiler, "profile_location", mock_profile)

    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert called is False


def test_info_endpoint(client):
    """2: System info endpoint returns safe, unprivileged operational metadata."""
    resp = client.get("/api/v1/info")
    assert resp.status_code == 200
    data = resp.json()

    assert data["api_version"] == "1.0.0"
    assert "LandslideNEI" in data["name"]

    # Static model metadata
    model_meta = data["static_model"]
    assert model_meta["name"] == "Model A (Environmental Only)"
    assert model_meta["feature_count"] == 10
    assert len(model_meta["features"]) == 10
    assert "aspect_deg" in model_meta["features"]
    assert model_meta["spatial_cv_roc_auc"] == 0.8062
    assert "Uncalibrated static susceptibility score" in model_meta["score_interpretation"]

    # Supported geography
    geo = data["supported_geography"]
    assert geo["region"] == "Northeast India (NER)"
    assert len(geo["states"]) == 8

    # Rainfall and thresholds
    rf = data["rainfall"]
    assert rf["primary_source"] == "CWC Telemetry Stations"
    assert rf["max_station_distance_km"] == 50.0
    assert rf["max_freshness_age_hours"] == 6.0

    thresholds = data["operational_thresholds"]
    assert thresholds["threshold_type"] == "DEMO_OPERATIONAL_DEFAULT"
    assert "not calibrated against historical" in thresholds["disclaimer"].lower()

    # Risk fusion info
    fusion = data["risk_fusion"]
    assert fusion["authoritative_output"] == "risk_level (LOW, WATCH, HIGH, CRITICAL)"
    assert "engineering synthesis score" in fusion["score_semantics"].lower()


# ==============================================================================
# 2. UNIFIED PREDICTION ENDPOINT (/api/v1/predict)
# ==============================================================================

def test_predict_valid_ner_guwahati(client):
    """3 & 12-18: Valid NER location returns full compliant PredictResponse."""
    payload = {
        "latitude": 26.1445,
        "longitude": 91.7362,
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Top-level schema compliance
    assert data["api_version"] == "1.0.0"
    assert "request_id" in data
    assert uuid.UUID(data["request_id"])  # Valid UUID4

    # Request echo
    assert data["request"]["latitude"] == 26.1445
    assert data["request"]["longitude"] == 91.7362
    assert "timestamp" in data["request"]

    # Location block
    assert data["location"]["state"] == "Assam"
    assert data["location"]["country"] == "India"
    assert data["location"]["supported_domain"] is True

    # Static susceptibility block
    susc = data["static_susceptibility"]
    assert 0.0 <= susc["score"] <= 1.0
    assert susc["category"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    assert "elevation_m" in susc["terrain"]
    assert "soil_class" in susc["soil"]
    assert "landcover_class" in susc["landcover"]
    assert len(susc["reasons"]) > 0

    # Rainfall block
    rf = data["rainfall"]
    assert rf["source"] == "CWC"
    assert rf["station"] is not None
    assert rf["distance_km"] <= 50.0
    assert rf["quality"] in ["GOOD", "PARTIAL", "MISSING", "STALE", "NO_RELIABLE_STATION"]

    # Trigger block
    trig = data["rainfall_trigger"]
    assert trig["level"] in ["NORMAL", "WATCH", "HIGH", "NO_DATA"]
    if trig["trigger_score"] is not None:
        assert 0.0 <= trig["trigger_score"] <= 1.0

    # Risk block
    risk = data["risk"]
    assert risk["level"] in ["LOW", "WATCH", "HIGH", "CRITICAL"]
    assert risk["risk_level"] == risk["level"]
    assert 0.0 <= risk["operational_fusion_score"] <= 1.0
    assert risk["risk_score"] == risk["operational_fusion_score"]
    assert "engineering synthesis score" in risk["score_semantics"].lower()
    assert len(risk["reasons"]) > 0

    # Limitations
    assert len(data["limitations"]) >= 5


def test_predict_tawang_distant_cwc(client):
    """4, 19, 21: Tawang coordinate (>50km from CWC) flags NO_RELIABLE_LOCAL_STATION."""
    payload = {
        "latitude": 27.5925,
        "longitude": 91.6087,
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    rf = data["rainfall"]
    assert rf["distance_km"] > 50.0
    assert rf["quality"] == "NO_RELIABLE_STATION"
    assert rf["status"] == "NO_RELIABLE_LOCAL_STATION"
    # Rainfall must NOT be zeroed
    assert rf["rainfall_1h"] is None
    assert rf["rainfall_24h"] is None
    assert rf["rainfall_3d"] is None
    assert rf["rainfall_7d"] is None

    # Trigger should be NO_DATA
    assert data["rainfall_trigger"]["level"] == "NO_DATA"
    assert data["rainfall_trigger"]["trigger_score"] is None

    # Static baseline only score
    assert data["risk"]["scoring_mode"] == "STATIC_BASELINE_ONLY_RAINFALL_UNOBSERVED"
    assert data["risk"]["operational_fusion_score"] == data["static_susceptibility"]["score"]


def test_predict_outside_ner(client):
    """5: Coordinates outside Northeast India (New Delhi) return HTTP 400 OUTSIDE_SUPPORTED_DOMAIN."""
    payload = {
        "latitude": 28.6139,
        "longitude": 77.2090,
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 400
    data = resp.json()

    assert "error" in data
    err = data["error"]
    assert err["code"] == "OUTSIDE_SUPPORTED_DOMAIN"
    assert "outside" in err["message"].lower()
    assert err["details"]["supported_domain"] is False


def test_invalid_latitude_validation(client):
    """6: Latitude > 90.0 or < -90.0 rejected with HTTP 422."""
    resp = client.post("/api/v1/predict", json={"latitude": 95.0, "longitude": 91.7})
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_COORDINATES"


def test_invalid_longitude_validation(client):
    """7: Longitude > 180.0 or < -180.0 rejected with HTTP 422."""
    resp = client.post("/api/v1/predict", json={"latitude": 26.0, "longitude": 195.0})
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_COORDINATES"


def test_malformed_timestamp_rejected(client):
    """8: Malformed timestamp rejected with HTTP 400 INVALID_TIMESTAMP."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
        "timestamp": "not-a-valid-datetime"
    })
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "INVALID_TIMESTAMP"
    assert "malformed" in data["error"]["message"].lower()


def test_naive_timestamp_rejected(client):
    """10: Ambiguous naive timestamp without timezone offset rejected with HTTP 400."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
        "timestamp": "2026-09-02 09:00:00"
    })
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "INVALID_TIMESTAMP"
    assert "timezone" in data["error"]["message"].lower()


def test_timezone_aware_timestamp_accepted(client):
    """9: Valid ISO-8601 with timezone accepted cleanly."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
        "timestamp": "2026-09-02T09:00:00Z"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["request"]["timestamp"] == "2026-09-02T09:00:00Z"

    # Also test positive offset +05:30 (IST)
    resp_ist = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
        "timestamp": "2026-09-02T14:30:00+05:30"
    })
    assert resp_ist.status_code == 200


def test_omitted_timestamp_generates_utc(client):
    """11: Omitted timestamp defaults to current UTC time."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
    })
    assert resp.status_code == 200
    data = resp.json()
    ts = data["request"]["timestamp"]
    assert ts is not None
    # Parse to verify timezone-awareness
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert dt.tzinfo is not None


def test_static_susceptibility_semantics(client):
    """15: Static susceptibility score is explicitly uncalibrated terrain predisposition."""
    resp = client.post("/api/v1/predict", json={"latitude": 26.1445, "longitude": 91.7362})
    data = resp.json()
    susc = data["static_susceptibility"]

    # Verify field completeness
    assert 0.0 <= susc["score"] <= 1.0
    assert susc["category"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    assert "uncalibrated" in susc["category_description"].lower()
    assert "not an event" in susc["category_description"].lower()
    assert any("probability" in lim.lower() for lim in data["limitations"])
    assert "probability" in data["risk"]["score_semantics"].lower()


def test_stale_rainfall_explicitly_flagged(client):
    """20: Stale observation is explicitly flagged STALE, not silently treated as fresh."""
    # Guwahati latest observation is from 2022 -> compared against 2026-09-02, it is STALE
    resp = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
        "timestamp": "2026-09-02T09:00:00Z"
    })
    assert resp.status_code == 200
    data = resp.json()

    rf = data["rainfall"]
    assert rf["quality"] == "STALE"
    assert rf["status"] == "STALE"
    assert rf["freshness"]["freshness_status"] == "STALE"
    assert rf["freshness"]["age_hours"] > 6.0


def test_imd_macro_context_not_point_rainfall(client):
    """22: IMD observations are exposed strictly as macro context, not fabricated point rain."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
    })
    data = resp.json()
    rf = data["rainfall"]

    assert rf["source"] == "CWC"
    # Even if imd_macro_context is present or null, source is never IMD for exact location
    if rf["imd_macro_context"] is not None:
        assert rf["imd_macro_context"]["source"] == "IMD"
        assert rf["imd_macro_context"]["scope"] in ["STATE", "DISTRICT"]


def test_no_stack_traces_leaked(client):
    """24: Error responses never expose Python stack traces or internal exception dumps."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 28.6139,
        "longitude": 77.2090
    })
    raw_text = resp.text
    assert "Traceback (most recent call last)" not in raw_text
    assert 'File "' not in raw_text
    assert "line " not in raw_text or "lines outside" in raw_text


# ==============================================================================
# 3. STATIC PROFILE ENDPOINT (/api/v1/profile)
# ==============================================================================

def test_profile_endpoint_valid_tawang(client):
    """26: POST /api/v1/profile returns static susceptibility profile without rainfall."""
    resp = client.post("/api/v1/profile", json={
        "latitude": 27.5925,
        "longitude": 91.6087
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["api_version"] == "1.0.0"
    assert "request_id" in data
    assert data["location"]["state"] == "Arunachal Pradesh"
    assert "rainfall" not in data  # No rainfall in profile endpoint!
    assert "risk" not in data      # No dynamic risk fusion!

    susc = data["static_susceptibility"]
    assert 0.0 <= susc["score"] <= 1.0
    assert susc["category"] == "HIGH"
    assert data["model"]["type"] == "STATIC_SUSCEPTIBILITY_ONLY"


def test_profile_endpoint_outside_ner(client):
    """Profile endpoint rejects coordinates outside supported domain."""
    resp = client.post("/api/v1/profile", json={
        "latitude": 19.0760,
        "longitude": 72.8777  # Mumbai
    })
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "OUTSIDE_SUPPORTED_DOMAIN"


# ==============================================================================
# 4. CORS HEADERS
# ==============================================================================

def test_cors_headers(client):
    """27: Configurable safe CORS origin headers are returned on preflight."""
    resp = client.options(
        "/api/v1/predict",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        }
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
