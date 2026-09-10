import os
import sys
import json
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from api.main import app
from src.inference.location_profiler import get_location_profiler
from src.inference.rainfall_provider import get_rainfall_provider

def run_phase8_edge_cases():
    print("==========================================================================")
    print("PHASE 8: API FAILURE / EDGE CASE TESTING (EXACT VERIFICATION)")
    print("==========================================================================")

    client = TestClient(app)
    results = []

    def record_case(num, name, status_code, ok, details):
        results.append({
            "case_id": num,
            "name": name,
            "http_status": status_code,
            "passed": ok,
            "details": details
        })
        status_str = "PASS" if ok else "FAIL"
        print(f"Case {num:02d}: {name:38} | HTTP {status_code} | [{status_str}] - {details}")

    # Case 1: Valid coordinates (Kohima)
    try:
        res = client.post("/api/v1/predict", json={"latitude": 25.6740, "longitude": 94.1120, "auto_refetch": False})
        data = res.json()
        ok = (res.status_code == 200 and "risk" in data and "static_susceptibility" in data)
        record_case(1, "Valid coordinates (Kohima)", res.status_code, ok, f"Risk={data.get('risk', {}).get('risk_level')}")
    except Exception as e:
        record_case(1, "Valid coordinates (Kohima)", 500, False, str(e))

    # Case 2: Coordinates outside NER (New Delhi)
    try:
        res = client.post("/api/v1/predict", json={"latitude": 28.6139, "longitude": 77.2090})
        data = res.json()
        err = data.get("error", {})
        ok = (res.status_code == 400 and err.get("code") == "OUTSIDE_SUPPORTED_DOMAIN")
        record_case(2, "Coordinates outside NER", res.status_code, ok, f"Code={err.get('code')}: {err.get('message')[:50]}")
    except Exception as e:
        record_case(2, "Coordinates outside NER", 500, False, str(e))

    # Case 3: Invalid latitude (lat > 90)
    try:
        res = client.post("/api/v1/predict", json={"latitude": 95.0, "longitude": 92.0})
        data = res.json()
        err = data.get("error", {})
        ok = (res.status_code == 422 and err.get("code") in ["INVALID_COORDINATES", "VALIDATION_ERROR"])
        record_case(3, "Invalid latitude (lat > 90)", res.status_code, ok, f"Rejected by Pydantic: {err.get('message')}")
    except Exception as e:
        record_case(3, "Invalid latitude", 500, False, str(e))

    # Case 4: Invalid longitude (lon > 180)
    try:
        res = client.post("/api/v1/predict", json={"latitude": 25.0, "longitude": 195.0})
        data = res.json()
        err = data.get("error", {})
        ok = (res.status_code == 422 and err.get("code") in ["INVALID_COORDINATES", "VALIDATION_ERROR"])
        record_case(4, "Invalid longitude (lon > 180)", res.status_code, ok, f"Rejected by Pydantic: {err.get('message')}")
    except Exception as e:
        record_case(4, "Invalid longitude", 500, False, str(e))

    # Case 5: Missing parameters (no latitude)
    try:
        res = client.post("/api/v1/predict", json={"longitude": 92.0})
        data = res.json()
        err = data.get("error", {})
        ok = (res.status_code == 422 and err.get("code") == "INVALID_COORDINATES")
        record_case(5, "Missing parameters (no lat)", res.status_code, ok, f"Field required: {err.get('message')}")
    except Exception as e:
        record_case(5, "Missing parameters", 500, False, str(e))

    # Case 6: Null values (lat=None)
    try:
        res = client.post("/api/v1/predict", json={"latitude": None, "longitude": 92.0})
        data = res.json()
        err = data.get("error", {})
        ok = (res.status_code == 422)
        record_case(6, "Null values (lat=None)", res.status_code, ok, f"Rejected cleanly: {err.get('message')}")
    except Exception as e:
        record_case(6, "Null values", 500, False, str(e))

    # Case 7: Extreme coordinates (-89.9, -179.9)
    try:
        res = client.post("/api/v1/predict", json={"latitude": -89.9, "longitude": -179.9})
        data = res.json()
        err = data.get("error", {})
        ok = (res.status_code == 400 and err.get("code") == "OUTSIDE_SUPPORTED_DOMAIN")
        record_case(7, "Extreme coordinates (-89.9, -179.9)", res.status_code, ok, f"Domain check rejected: {err.get('code')}")
    except Exception as e:
        record_case(7, "Extreme coordinates", 500, False, str(e))

    # Case 8: No CWC station within 50 km (Lunglei)
    try:
        res = client.post("/api/v1/predict", json={"latitude": 22.8878, "longitude": 92.7397, "auto_refetch": False})
        data = res.json()
        rf = data.get("rainfall", {})
        trig = data.get("rainfall_trigger", {})
        ok = (res.status_code == 200 and rf.get("status") == "NO_RELIABLE_LOCAL_STATION" and trig.get("trigger_level") == "NO_DATA" and rf.get("rainfall_1h") is None and rf.get("distance_km") > 50.0)
        record_case(8, "No CWC station within 50 km", res.status_code, ok, f"Dist={rf.get('distance_km')}km > 50km cutoff, status={rf.get('status')}")
    except Exception as e:
        record_case(8, "No CWC station within 50 km", 500, False, str(e))

    # Case 9: Stale CWC data (>6h old) (Tezpur)
    try:
        res = client.post("/api/v1/predict", json={"latitude": 26.6528, "longitude": 92.7926, "auto_refetch": False})
        data = res.json()
        rf = data.get("rainfall", {})
        freshness = rf.get("freshness", {})
        ok = (res.status_code == 200 and rf.get("quality") == "STALE" and freshness.get("freshness_status") == "STALE")
        record_case(9, "Stale CWC data (>6h old)", res.status_code, ok, f"Quality={rf.get('quality')}, freshness_status={freshness.get('freshness_status')}, age={freshness.get('age_hours')}h")
    except Exception as e:
        record_case(9, "Stale CWC data", 500, False, str(e))

    # Case 10: Missing rainfall window is None (not zero)
    try:
        res = client.post("/api/v1/predict", json={"latitude": 25.6740, "longitude": 94.1120, "auto_refetch": False})
        data = res.json()
        rf = data.get("rainfall", {})
        ok = (res.status_code == 200 and rf.get("rainfall_1h") is None and rf.get("rainfall_24h") is None)
        record_case(10, "Missing rainfall window is None", res.status_code, ok, f"rf_1h={rf.get('rainfall_1h')} (None != 0.0)")
    except Exception as e:
        record_case(10, "Missing rainfall window", 500, False, str(e))

    # Case 11: IMD unavailable simulation
    try:
        provider = get_rainfall_provider()
        with patch.object(provider, 'get_imd_district_rainfall', return_value=None):
            res = client.post("/api/v1/predict", json={"latitude": 26.6528, "longitude": 92.7926, "auto_refetch": False})
            data = res.json()
            ok = (res.status_code == 200 and "risk" in data)
            record_case(11, "IMD unavailable simulation", res.status_code, ok, "Handled safely without IMD macro context")
    except Exception as e:
        record_case(11, "IMD unavailable", 500, False, str(e))

    # Case 12: CWC unavailable simulation (fallback to NO_LOCAL_DATA)
    try:
        provider = get_rainfall_provider()
        dummy_unavailable = {
            "status": "NO_RELIABLE_LOCAL_STATION",
            "source": "NO_LOCAL_DATA",
            "is_realtime": False,
            "station": None,
            "station_key": None,
            "state": "Assam",
            "district": "Sonitpur",
            "distance_km": 999.0,
            "max_acceptable_distance_km": 50.0,
            "nearest_station": None,
            "nearest_station_distance_km": 999.0,
            "operational_status": "NO_RELIABLE_LOCAL_DATA",
            "timestamp": None,
            "rainfall_1h": None,
            "rainfall_24h": None,
            "rainfall_3d": None,
            "rainfall_7d": None,
            "coverage_24h": None,
            "coverage_3d": None,
            "coverage_7d": None,
            "quality": "NO_RELIABLE_STATION",
            "quality_notes": "CWC telemetry unavailable.",
            "freshness": {
                "observation_timestamp": None,
                "reference_timestamp": None,
                "age_hours": None,
                "freshness_status": "UNAVAILABLE",
                "max_acceptable_age_hours": 6.0,
            },
            "imd_macro_context": None,
        }
        with patch.object(provider, 'get_rainfall_for_location', return_value=dummy_unavailable):
            res = client.post("/api/v1/predict", json={"latitude": 26.6528, "longitude": 92.7926, "auto_refetch": False})
            data = res.json()
            trig = data.get("rainfall_trigger", {})
            ok = (res.status_code == 200 and trig.get("trigger_level") == "NO_DATA")
            record_case(12, "CWC unavailable simulation", res.status_code, ok, f"Trigger={trig.get('trigger_level')} with safe static fallback")
    except Exception as e:
        record_case(12, "CWC unavailable", 500, False, str(e))

    # Case 13: Soil raster unavailable simulation
    try:
        profiler = get_location_profiler()
        mock_soil = {
            "wrb_code": np.nan, "wrb_class": "Unknown", "clay_pct": np.nan,
            "sand_pct": np.nan, "silt_pct": np.nan, "bulk_density_kg_dm3": np.nan,
            "soil_quality": "MISSING_LAYERS", "soil_quality_notes": "Simulated soil unavailability"
        }
        with patch.object(profiler, '_get_soil_features', return_value=mock_soil):
            res = client.post("/api/v1/predict", json={"latitude": 25.6740, "longitude": 94.1120, "auto_refetch": False})
            data = res.json()
            ok = (res.status_code == 200 and "static_susceptibility" in data)
            record_case(13, "Soil raster unavailable simulation", res.status_code, ok, "Imputed robustly by scikit-learn pipeline")
    except Exception as e:
        record_case(13, "Soil raster unavailable", 500, False, str(e))

    # Case 14: DEM raster unavailable simulation
    try:
        profiler = get_location_profiler()
        mock_dem = {
            "elevation_m": np.nan, "slope_deg": np.nan, "aspect_deg": np.nan,
            "relief_std_5x5_m": np.nan, "profile_curvature": np.nan, "plan_curvature": np.nan,
            "curvature_class": None, "terrain_ruggedness_index_m": np.nan, "topographic_position_index_m": np.nan,
            "slope_position": None, "topographic_wetness_index": np.nan, "village_terrain_risk_multiplier": 1.0,
            "dem_tile": None, "dem_quality": "MISSING_TILE"
        }
        with patch.object(profiler, '_get_dem_features', return_value=mock_dem):
            res = client.post("/api/v1/predict", json={"latitude": 25.6740, "longitude": 94.1120, "auto_refetch": False})
            data = res.json()
            ok = (res.status_code == 200 and "static_susceptibility" in data)
            record_case(14, "DEM raster unavailable simulation", res.status_code, ok, "Processed gracefully without server crash")
    except Exception as e:
        record_case(14, "DEM unavailable", 500, False, str(e))

    # Case 15: Malformed JSON request
    try:
        res = client.post("/api/v1/predict", content=b"INVALID_JSON{{{{", headers={"Content-Type": "application/json"})
        ok = (res.status_code in [400, 422])
        record_case(15, "Malformed JSON request", res.status_code, ok, f"Handled with HTTP {res.status_code}")
    except Exception as e:
        record_case(15, "Malformed JSON", 500, False, str(e))

    # Case 16: Upstream API timeout handling
    try:
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
            res = client.post("/api/v1/predict", json={"latitude": 25.6740, "longitude": 94.1120, "auto_refetch": True})
            data = res.json()
            rf = data.get("rainfall", {})
            ok = (res.status_code == 200 and rf.get("fallback_engaged") is True)
            record_case(16, "Upstream API timeout handling", res.status_code, ok, f"Handled with fallback_engaged={rf.get('fallback_engaged')}")
    except Exception as e:
        record_case(16, "API timeout", 500, False, str(e))

    # Case 17: Upstream HTTP failure (500 internal server error from external API)
    try:
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://test", 500, "Internal Server Error", {}, None)):
            res = client.post("/api/v1/predict", json={"latitude": 25.6740, "longitude": 94.1120, "auto_refetch": True})
            data = res.json()
            rf = data.get("rainfall", {})
            ok = (res.status_code == 200 and rf.get("fallback_engaged") is True)
            record_case(17, "Upstream HTTP 500 failure", res.status_code, ok, f"Handled with fallback_engaged={rf.get('fallback_engaged')}")
    except Exception as e:
        record_case(17, "Upstream HTTP failure", 500, False, str(e))

    out_file = PROJECT_ROOT / "docs" / "phase8_edge_cases_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    total_passed = sum(1 for r in results if r["passed"])
    print(f"\nPhase 8 Edge Cases: {total_passed}/{len(results)} PASSED")

if __name__ == "__main__":
    run_phase8_edge_cases()
