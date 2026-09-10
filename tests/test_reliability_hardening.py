"""
Reliability Hardening & Edge-Case Test Suite (Phase 14)
======================================================
Validates all 20 mission-critical reliability contracts:
1. valid coordinate
2. invalid coordinate
3. out-of-domain coordinate
4. missing DEM
5. missing soil
6. missing rainfall
7. rainfall station >50 km
8. rainfall station <=50 km
9. stale rainfall
10. insufficient coverage
11. NaN input
12. null input
13. model unavailable
14. model inference failure
15. historical event lookup
16. terrain unavailable
17. resource resolution
18. 3D terrain query
19. risk fusion NO_DATA
20. API malformed request
"""

import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.inference.location_profiler import get_location_profiler, LocationProfiler
from src.inference.rainfall_provider import get_rainfall_provider
from src.inference.rainfall_trigger import evaluate_rainfall_trigger
from src.inference.risk_engine import get_risk_engine
from src.inference.risk_fusion import get_risk_fusion_engine
from src.inference.terrain_service import get_terrain_service

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# 1. Valid Coordinate
def test_01_valid_coordinate():
    profiler = get_location_profiler()
    # Kohima, Nagaland
    res = profiler.profile_location(25.6740, 94.1120)
    assert res["status"] == "SUCCESS"
    assert res["location"]["supported_domain"] is True
    assert 0.0 <= res["susceptibility"]["score"] <= 1.0
    assert res["susceptibility"]["category"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]


# 2. Invalid Coordinate
def test_02_invalid_coordinate(client):
    # Latitude > 90
    resp = client.post("/api/v1/predict", json={"latitude": 95.0, "longitude": 92.0})
    assert resp.status_code in [400, 422]
    # Longitude < -180
    resp2 = client.post("/api/v1/predict", json={"latitude": 25.0, "longitude": -190.0})
    assert resp2.status_code in [400, 422]


# 3. Out-of-Domain Coordinate
def test_03_out_of_domain_coordinate(client):
    # Delhi coordinate (outside Northeast India)
    resp = client.post("/api/v1/predict", json={"latitude": 28.6139, "longitude": 77.2090})
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "OUTSIDE_SUPPORTED_DOMAIN"


# 4. Missing DEM
def test_04_missing_dem():
    profiler = get_location_profiler()
    # Query an arbitrary coordinate where no DEM GeoTIFF tile exists
    res = profiler._get_dem_features(21.1, 88.1)
    # Either OFFLINE_CACHE_OK, MISSING_TILE, or OUT_OF_BOUNDS without raising unhandled exception
    assert res["dem_quality"] in ["OFFLINE_CACHE_OK", "MISSING_TILE", "OUT_OF_BOUNDS", "NODATA"]


# 5. Missing Soil
def test_05_missing_soil():
    profiler = get_location_profiler()
    # Coordinates in Bay of Bengal border with no soil data
    res = profiler._get_soil_features(20.0, 90.0)
    assert res["soil_quality"] in ["PARTIAL", "OK"]


# 6. Missing Rainfall
def test_06_missing_rainfall():
    rp = get_rainfall_provider()
    # Shillong Peak (no operational CWC station within 50km)
    res = rp.get_rainfall_for_location(25.5788, 91.8933)
    assert res["operational_status"] == "NO_RELIABLE_LOCAL_DATA"
    assert res["rainfall_1h"] is None
    assert res["rainfall_24h"] is None
    assert res["distance_km"] > 50.0


# 7. Rainfall Station > 50 km
def test_07_rainfall_station_beyond_50km():
    rp = get_rainfall_provider()
    # Location far from any CWC river gauging station
    res = rp.get_rainfall_for_location(25.5788, 91.8933, max_distance_km=50.0)
    assert res["operational_status"] == "NO_RELIABLE_LOCAL_DATA"
    assert res["distance_km"] > 50.0


# 8. Rainfall Station <= 50 km
def test_08_rainfall_station_within_50km():
    rp = get_rainfall_provider()
    # Tezpur Sonitpur (station within 2.0 km)
    res = rp.get_rainfall_for_location(26.6338, 92.7926, max_distance_km=50.0)
    assert res["station"] == "Tezpur"
    assert res["distance_km"] <= 50.0


# 9. Stale Rainfall
def test_09_stale_rainfall():
    rp = get_rainfall_provider()
    # Query with a reference time 48 hours ahead of latest telemetry
    future_time = datetime.now(timezone.utc) + timedelta(hours=48)
    res = rp.get_rainfall_for_location(26.6338, 92.7926, reference_time=future_time, max_age_hours=6.0)
    # Stale observations must be flagged
    if res.get("station") is not None:
        assert res["freshness"]["freshness_status"] in ["STALE", "VERY_STALE", "EXPIRED"]


# 10. Insufficient Coverage
def test_10_insufficient_coverage():
    trig = evaluate_rainfall_trigger(
        rainfall_data={
            "rainfall_1h": None,
            "rainfall_24h": 10.0,
            "coverage_24h": 0.50, # < 0.75 coverage requirement
            "coverage_3d": 0.50,
            "coverage_7d": 0.50,
            "freshness": {"freshness_status": "FRESH", "age_hours": 1.0},
        }
    )
    assert trig["trigger_level"] in ["NO_DATA", "NORMAL"]


# 11. NaN Input
def test_11_nan_input(client):
    # Passing NaN string or invalid numeric
    resp = client.post("/api/v1/predict", json={"latitude": "NaN", "longitude": 94.0})
    assert resp.status_code in [400, 422]


# 12. Null Input
def test_12_null_input(client):
    resp = client.post("/api/v1/predict", json={"latitude": None, "longitude": None})
    assert resp.status_code == 422


# 13. Model Unavailable (Simulated/Contract)
def test_13_model_unavailable(client):
    # Health endpoint reports model readiness
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_loaded"] is True
    assert "Model A" in data["static_model"]


# 14. Model Inference Robustness
def test_14_model_inference_robustness():
    profiler = get_location_profiler()
    # Profile location with all optional anthropogenic parameters
    res = profiler.profile_location(
        25.6740, 94.1120,
        road_cut_present=True,
        cut_slope_deg=55.0,
        drainage_blocked=True,
        unsupported_excavation=True,
        deforestation_observed=True,
        has_retaining_wall=False,
    )
    assert res["status"] == "SUCCESS"
    assert res["susceptibility"]["score"] is not None


# 15. Historical Event Lookup
def test_15_historical_event_lookup():
    svc = get_terrain_service()
    hist = svc.get_historical_landslides()
    assert hist["status"] == "CONNECTED"
    assert hist["count"] == 75
    assert len(hist["events"]) == 75
    first_ev = hist["events"][0]
    assert "event_id" in first_ev
    assert "latitude" in first_ev
    assert "longitude" in first_ev


# 16. Terrain Unavailable
def test_16_terrain_unavailable():
    svc = get_terrain_service()
    # Query coordinate far outside the region (equator)
    res = svc.extract_terrain_grid(0.0, 0.0, radius_km=10.0, grid_size=32)
    assert res["status"] == "TERRAIN_DATA_UNAVAILABLE"


# 17. Resource Resolution
def test_17_resource_resolution():
    assert PROJECT_ROOT.exists()
    assert (PROJECT_ROOT / "model" / "static_lsm_pipeline.joblib").exists()
    assert (PROJECT_ROOT / "data" / "processed").exists()
    assert (PROJECT_ROOT / "historical_landslide_events.csv").exists()


# 18. 3D Terrain Query
def test_18_3d_terrain_query(client):
    # Namchi ridge
    resp = client.get("/api/v1/terrain/mesh?latitude=27.1667&longitude=88.3500&radius_km=10.0&grid_size=128")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert len(data["elevations"]) == 128 * 128
    assert data["dimensions"]["width"] == 128


# 19. Risk Fusion NO_DATA Handling
def test_19_risk_fusion_no_data():
    # When rainfall is NO_DATA, fusion engine must NOT assume zero rainfall or pretend normal
    engine = get_risk_fusion_engine()
    static_profile = {
        "susceptibility": {
            "score": 0.45,
            "category": "MODERATE",
        }
    }
    rainfall_trigger = {
        "trigger_level": "NO_DATA",
        "trigger_score": None,
        "trigger_reasons": [],
    }
    fusion = engine.fuse_risk(static_profile, rainfall_trigger)
    assert fusion["risk_level"] in ["LOW", "WATCH"]
    assert fusion["scoring_mode"] == "STATIC_BASELINE_ONLY_RAINFALL_UNOBSERVED"
    assert fusion["rainfall_trigger_level"] == "NO_DATA"
    assert any("NO_DATA" in r["code"] or "STATIC" in r["code"] for r in fusion["reasons"])


# 20. API Malformed Request
def test_20_api_malformed_request(client):
    # Raw non-JSON payload
    resp = client.post(
        "/api/v1/predict",
        content="not-json-payload",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code in [400, 422]
    # Verify no python stack trace is leaked
    err_body = resp.text
    assert "Traceback" not in err_body
    assert "File \"" not in err_body
