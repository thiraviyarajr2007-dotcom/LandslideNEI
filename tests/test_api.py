"""
Integration and Unit Tests for the FastAPI REST API Service (api/main.py).
"""

import io
import os
import sys
import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from scripts.evaluate_model import SEVERITY_ORDER


@pytest.fixture(scope="module")
def client():
    """
    FastAPI TestClient fixture.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_low_risk_payload():
    return {
        "rainfall_24h": 15.0,
        "rainfall_3d": 35.0,
        "rainfall_7d": 60.0,
        "slope": 10.0,
        "elevation": 350.0,
        "historical_landslide": 0,
        "distance_to_landslide": 10.0,
        "soil_risk": 0.15,
    }


@pytest.fixture
def valid_high_risk_payload():
    return {
        "rainfall_24h": 182.0,
        "rainfall_3d": 420.0,
        "rainfall_7d": 650.0,
        "slope": 38.0,
        "elevation": 850.0,
        "historical_landslide": 1,
        "distance_to_landslide": 0.8,
        "soil_risk": 0.70,
    }


def create_in_memory_pdf(text_content: str) -> bytes:
    """
    Creates an in-memory PDF binary stream with the specified text content.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text_content, fontsize=11)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# ==============================================================================
# 1. GENERAL & HEALTH ENDPOINTS
# ==============================================================================

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["version"] == "1.0.0"
    assert "docs_url" in data
    assert "disclaimer" in data
    assert "demonstration" in data["disclaimer"].lower() or "synthetic" in data["disclaimer"].lower()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_version"] == "1.2.0"
    assert "timestamp" in data


def test_model_info_endpoint(client):
    response = client.get("/model-info")
    assert response.status_code == 200
    data = response.json()
    assert "model_version" in data
    assert data["model_version"] == "1.2.0"
    assert "features" in data
    assert len(data["features"]) == 8
    assert "classes" in data
    assert set(data["classes"]) == set(SEVERITY_ORDER)


def test_docs_and_openapi_spec(client):
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    spec = openapi_resp.json()
    assert "/predict" in spec["paths"]
    assert "/predict/pdf" in spec["paths"]
    assert "/demo" in spec["paths"]


# ==============================================================================
# 2. TABULAR PREDICTION ENDPOINT (/predict)
# ==============================================================================

def test_predict_valid_low_risk(client, valid_low_risk_payload):
    response = client.post("/predict", json=valid_low_risk_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["risk"] in SEVERITY_ORDER
    assert 0.0 <= data["confidence"] <= 1.0
    assert set(data["probabilities"].keys()) == set(SEVERITY_ORDER)
    assert sum(data["probabilities"].values()) == pytest.approx(1.0, abs=1e-3)
    assert data["confidence"] == pytest.approx(data["probabilities"][data["risk"]], abs=1e-4)
    assert data["model_version"] == "1.2.0"
    assert "prediction_timestamp" in data
    assert isinstance(data["contributing_factors"], list)
    assert len(data["contributing_factors"]) <= 5


def test_predict_valid_high_risk(client, valid_high_risk_payload):
    response = client.post("/predict", json=valid_high_risk_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["risk"] in ["High", "Critical"]
    assert data["confidence"] > 0.0
    assert len(data["contributing_factors"]) > 0

    # Validate factor schema and non-causal language
    for factor in data["contributing_factors"]:
        assert "code" in factor
        assert "feature" in factor
        assert "value" in factor
        assert "importance" in factor
        assert "message" in factor
        msg_lower = factor["message"].lower()
        assert "causes" not in msg_lower
        assert "caused by" not in msg_lower
        assert "causing" not in msg_lower
        assert "guarantees" not in msg_lower
        assert "proves" not in msg_lower


def test_predict_negative_rainfall_rejected(client, valid_low_risk_payload):
    bad_payload = valid_low_risk_payload.copy()
    bad_payload["rainfall_24h"] = -15.0
    response = client.post("/predict", json=bad_payload)
    assert response.status_code == 422
    assert "rainfall_24h" in response.json()["detail"]


def test_predict_invalid_slope_rejected(client, valid_low_risk_payload):
    bad_payload = valid_low_risk_payload.copy()
    bad_payload["slope"] = 105.0
    response = client.post("/predict", json=bad_payload)
    assert response.status_code == 422
    assert "slope" in response.json()["detail"]


def test_predict_invalid_elevation_rejected(client, valid_low_risk_payload):
    bad_payload = valid_low_risk_payload.copy()
    bad_payload["elevation"] = 15000.0
    response = client.post("/predict", json=bad_payload)
    assert response.status_code == 422
    assert "elevation" in response.json()["detail"]


def test_predict_invalid_historical_landslide_rejected(client, valid_low_risk_payload):
    bad_payload = valid_low_risk_payload.copy()
    bad_payload["historical_landslide"] = 5
    response = client.post("/predict", json=bad_payload)
    assert response.status_code == 422
    assert "historical_landslide" in response.json()["detail"]


def test_predict_invalid_soil_risk_rejected(client, valid_low_risk_payload):
    bad_payload = valid_low_risk_payload.copy()
    bad_payload["soil_risk"] = 2.5
    response = client.post("/predict", json=bad_payload)
    assert response.status_code == 422
    assert "soil_risk" in response.json()["detail"]


def test_predict_missing_field_rejected(client):
    incomplete_payload = {
        "rainfall_24h": 182.0,
        "rainfall_3d": 420.0,
        # missing rainfall_7d, slope, etc.
    }
    response = client.post("/predict", json=incomplete_payload)
    assert response.status_code == 422


def test_predict_wrong_datatype_rejected(client, valid_low_risk_payload):
    bad_payload = valid_low_risk_payload.copy()
    bad_payload["rainfall_24h"] = "one hundred mm"
    response = client.post("/predict", json=bad_payload)
    assert response.status_code == 422


# ==============================================================================
# 3. PDF DOCUMENT PREDICTION ENDPOINT (/predict/pdf)
# ==============================================================================

def test_predict_pdf_non_pdf_file_rejected(client):
    file_bytes = b"Hello, this is a plain text file."
    files = {"file": ("report.txt", io.BytesIO(file_bytes), "text/plain")}
    response = client.post("/predict/pdf", files=files)
    assert response.status_code == 400
    assert "not a valid PDF" in response.json()["detail"]


def test_predict_pdf_empty_file_rejected(client):
    empty_bytes = b""
    files = {"file": ("empty.pdf", io.BytesIO(empty_bytes), "application/pdf")}
    response = client.post("/predict/pdf", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_predict_pdf_incomplete_report(client):
    # Incomplete text: missing 3d/7d rainfall, distance, soil risk, etc.
    pdf_text = (
        "GEOTECHNICAL PRELIMINARY NOTICE\n"
        "Location: East Khasi Hills, Meghalaya\n"
        "24-hour rainfall measured: 182 mm.\n"
        "Terrain slope angle: 38 degrees.\n"
        "Elevation: 850 metres above sea level.\n"
    )
    pdf_bytes = create_in_memory_pdf(pdf_text)
    files = {"file": ("incomplete_report.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/predict/pdf", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction_ready"] is False
    assert data["prediction_status"] == "UNAVAILABLE_MISSING_FEATURES"
    assert data["prediction"] is None
    assert len(data["missing_features"]) > 0
    assert "Data was not fabricated" in data["message"]


# ==============================================================================
# 4. DEMONSTRATION SCENARIOS ENDPOINT (/demo)
# ==============================================================================

def test_demo_endpoint(client):
    response = client.get("/demo")
    assert response.status_code == 200
    data = response.json()

    assert data["dataset_type"] == "DEMO / PIPELINE VALIDATION DATA"
    assert "demo_notice" in data
    assert "18-row" in data["demo_notice"]

    scenarios = data["scenarios"]
    assert "low_risk_scenario" in scenarios
    assert "high_critical_risk_scenario" in scenarios
    assert "incomplete_document_scenario" in scenarios

    # Low risk check
    low_out = scenarios["low_risk_scenario"]["output"]
    assert low_out["risk"] in SEVERITY_ORDER
    assert 0.0 <= low_out["confidence"] <= 1.0

    # High risk check
    high_out = scenarios["high_critical_risk_scenario"]["output"]
    assert high_out["risk"] in ["High", "Critical"]
    assert high_out["confidence"] > 0.0

    # Incomplete check (Zero-Fabrication verification)
    inc_out = scenarios["incomplete_document_scenario"]["output"]
    assert inc_out["prediction_ready"] is False
    assert inc_out["prediction"] is None
    assert len(inc_out["missing_features"]) > 0
