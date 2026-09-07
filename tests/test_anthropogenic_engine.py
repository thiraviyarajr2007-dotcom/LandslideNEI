"""
Unit Tests for Anthropogenic & Human Factors Engine (Phase 8K - Pillar ④)
==========================================================================
Tests:
1. Natural forested slope: root cohesion, normal drainage, baseline multiplier 1.0
2. Road toe cut: cut-slope steepening, severe cut classification, shear driving increase
3. Blocked drainage: perched hydrostatic surcharge (3.5 kPa)
4. Deforestation: loss of root tensile cohesion (0.0 kPa)
5. Engineered retaining wall: structural resistance buttress, hazard reduction, FoS restoration
6. API endpoint integration: POST /api/v1/predict with anthropogenic payload and reason codes
"""

import pytest
from fastapi.testclient import TestClient

from src.inference.anthropogenic_engine import compute_anthropogenic_impact
from api.main import app


def test_natural_forested_slope_baseline():
    """Verify that an undisturbed natural forested slope retains full root cohesion and unit multiplier."""
    res = compute_anthropogenic_impact(
        natural_slope_deg=25.0,
        landcover_class="Tree cover",
        base_cohesion_kpa=10.0,
        friction_angle_deg=28.0,
        pore_water_pressure_kpa=0.0,
        slope_position="Mid-Slope",
        road_cut_present=False,
        drainage_blocked=False,
        deforestation_observed=False,
    )
    assert res["road_cut_present"] is False
    assert res["effective_slope_deg"] == 25.0
    assert res["root_cohesion_kpa"] == 10.0
    assert res["drainage_condition"] == "NORMAL_SURFACE_DRAINAGE"
    assert res["hydrostatic_surcharge_kpa"] == 0.0
    assert res["anthropogenic_hazard_multiplier"] == 1.0
    assert res["modified_factor_of_safety"] >= 1.50
    assert res["stability_verdict"] == "STABLE"


def test_road_toe_cut_geometry_and_severity():
    """Verify that an unsupported road cut steepens slope and increases shear driving multiplier."""
    res = compute_anthropogenic_impact(
        natural_slope_deg=28.0,
        landcover_class="Tree cover",
        road_cut_present=True,
        cut_slope_deg=65.0,
    )
    assert res["road_cut_present"] is True
    assert res["effective_slope_deg"] == 65.0
    assert res["road_cut_severity"] == "SEVERE"
    assert res["retaining_wall_status"] == "UNSUPPORTED_EXCAVATION"
    assert res["anthropogenic_hazard_multiplier"] >= 1.40
    assert any("retaining wall" in m.lower() for m in res["recommended_mitigations"])


def test_drainage_blockage_hydrostatic_surcharge():
    """Verify that clogged culverts and unlined drains add perched hydrostatic surcharge."""
    res = compute_anthropogenic_impact(
        natural_slope_deg=25.0,
        drainage_blocked=True,
    )
    assert res["drainage_condition"] == "BLOCKED_CONCENTRATED_RUNOFF"
    assert res["hydrostatic_surcharge_kpa"] == 3.5
    assert res["anthropogenic_hazard_multiplier"] >= 1.30
    assert any("interceptor drain" in m.lower() for m in res["recommended_mitigations"])


def test_deforestation_root_cohesion_depletion():
    """Verify that forest clearing or slash-and-burn depletes root cohesion to zero."""
    res = compute_anthropogenic_impact(
        natural_slope_deg=25.0,
        landcover_class="Tree cover",
        deforestation_observed=True,
    )
    assert res["deforestation_observed"] is True
    assert res["root_cohesion_kpa"] == 0.0
    assert res["anthropogenic_hazard_multiplier"] >= 1.20
    assert any("vetiver" in m.lower() for m in res["recommended_mitigations"])


def test_engineered_retaining_wall_mitigation():
    """Verify that constructing an engineered retaining wall restores stability and lowers hazard."""
    unmitigated = compute_anthropogenic_impact(
        natural_slope_deg=28.0,
        road_cut_present=True,
        cut_slope_deg=60.0,
        has_retaining_wall=False,
    )
    mitigated = compute_anthropogenic_impact(
        natural_slope_deg=28.0,
        road_cut_present=True,
        cut_slope_deg=60.0,
        has_retaining_wall=True,
    )
    assert mitigated["retaining_wall_status"] == "ENGINEERED_RETAINING_WALL"
    assert mitigated["anthropogenic_hazard_multiplier"] < unmitigated["anthropogenic_hazard_multiplier"]
    assert mitigated["modified_factor_of_safety"] > unmitigated["modified_factor_of_safety"]


def test_predict_api_anthropogenic_payload():
    """Verify that the FastAPI /predict endpoint accepts and reflects anthropogenic parameters."""
    client = TestClient(app)
    payload = {
        "latitude": 27.5925,
        "longitude": 91.6087,
        "road_cut_present": True,
        "cut_slope_deg": 65.0,
        "drainage_blocked": True,
        "deforestation_observed": True,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "anthropogenic" in data
    anthro = data["anthropogenic"]
    assert anthro["road_cut_present"] is True
    assert anthro["cut_slope_deg"] == 65.0
    assert anthro["drainage_condition"] == "BLOCKED_CONCENTRATED_RUNOFF"
    assert anthro["deforestation_observed"] is True
    assert len(anthro["recommended_mitigations"]) > 0

    # Verify explainability codes in reasons
    reasons = data["static_susceptibility"]["reasons"]
    codes = [r["code"] for r in reasons]
    assert "ANTHROPOGENIC_ROAD_TOE_CUT" in codes
    assert "BLOCKED_DRAINAGE_SURCHARGE" in codes
    assert "ROOT_COHESION_DEPLETED" in codes
