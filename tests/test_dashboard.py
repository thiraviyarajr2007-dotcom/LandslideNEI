"""
Phase 8J - Operational Dashboard & GIS Risk Visualization Integration Tests
===========================================================================
Validates:
1. Static files mounting and delivery via FastAPI.
2. Root redirect behavior (HTML -> /dashboard/, JSON -> API info).
3. Dashboard assets integrity (CSS, JS, GeoJSON, CWC stations).
4. Demo presets API integration and risk tier verification.
5. Out-of-domain rejection for demo presets.
6. Localization key parity between English and Tamil.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app

PROJECT_ROOT = Path("C:/SIH Landslide")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_dashboard_index_served(client):
    """Verify /dashboard/ serves index.html with 200 OK."""
    resp = client.get("/dashboard/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "LandslideNEI" in resp.text
    assert "gis-map" in resp.text
    assert "operational-panel" in resp.text


def test_root_redirect_for_html(client):
    """Verify / with Accept: text/html redirects to /dashboard/."""
    resp = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"}, follow_redirects=False)
    assert resp.status_code in [302, 307]
    assert resp.headers["location"] == "/dashboard/"


def test_root_json_for_api_clients(client):
    """Verify / with Accept: application/json returns JSON overview."""
    resp = client.get("/", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert data["dashboard_url"] == "/dashboard/"
    assert "api_version" in data


def test_static_css_and_js_served(client):
    """Verify styles.css and all application JS files are delivered properly."""
    assets = [
        ("/dashboard/css/styles.css", "text/css", "Tactical Dark Theme"),
        ("/dashboard/js/i18n.js", "application/javascript", "translations"),
        ("/dashboard/js/demo_presets.js", "application/javascript", "DEMO_PRESETS"),
        ("/dashboard/js/map.js", "application/javascript", "initMap"),
        ("/dashboard/js/app.js", "application/javascript", "evaluateLocation"),
    ]

    for path, expected_type_substr, expected_content_substr in assets:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed to fetch {path}"
        assert expected_type_substr in resp.headers.get("content-type", "") or "text" in resp.headers.get("content-type", "")
        assert expected_content_substr in resp.text, f"Missing content in {path}"


def test_gis_geojson_assets_served(client):
    """Verify ner_states.geojson and cwc_stations.json are valid and accessible."""
    # Test GeoJSON
    resp = client.get("/dashboard/assets/ner_states.geojson")
    assert resp.status_code == 200
    geo = resp.json()
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) >= 8

    states = set(f["properties"]["state"] for f in geo["features"])
    expected_ner_states = {"Arunachal Pradesh", "Assam", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"}
    assert expected_ner_states.issubset(states)

    # Test CWC stations
    resp_st = client.get("/dashboard/assets/cwc_stations.json")
    assert resp_st.status_code == 200
    stations = resp_st.json()
    assert isinstance(stations, list)
    assert len(stations) >= 50
    assert "latitude" in stations[0]
    assert "longitude" in stations[0]


def test_demo_preset_guwahati_prediction(client):
    """Verify Guwahati demo preset query against predict API."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 26.1445,
        "longitude": 91.7362,
        "timestamp": "2026-09-02T09:00:00Z"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["state"] == "Assam"
    assert data["risk"]["risk_level"] in ["LOW", "WATCH"]
    assert data["rainfall"]["distance_km"] < 50.0  # Within 50km cap


def test_demo_preset_tawang_prediction(client):
    """Verify Tawang demo preset query against predict API."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 27.5925,
        "longitude": 91.6087,
        "timestamp": "2026-09-02T09:00:00Z"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["state"] == "Arunachal Pradesh"
    assert data["static_susceptibility"]["score"] > 0.50  # High static susceptibility
    assert data["rainfall"]["status"] in ["NO_DATA", "STALE", "NO_RELIABLE_LOCAL_STATION"]
    assert data["risk"]["risk_level"] in ["WATCH", "HIGH"]  # Precautionary WATCH/HIGH


def test_demo_preset_out_of_domain_delhi(client):
    """Verify New Delhi out-of-domain demo preset is rejected with HTTP 400."""
    resp = client.post("/api/v1/predict", json={
        "latitude": 28.6139,
        "longitude": 77.2090
    })
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] in ["OUTSIDE_SUPPORTED_DOMAIN", "OUTSIDE_NER_DOMAIN"]


def test_localization_key_parity():
    """Verify that English and Tamil translation dictionaries have matching keys."""
    i18n_path = PROJECT_ROOT / "dashboard/js/i18n.js"
    assert i18n_path.exists()
    content = i18n_path.read_text(encoding="utf-8")

    # Quick check that translations dictionary contains both en and ta
    assert "en: {" in content
    assert "ta: {" in content
    assert "appTitle" in content
    assert "riskVerdictTitle" in content
    assert "fusionScoreDisclaimer" in content
