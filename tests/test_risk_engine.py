"""
Integration Tests for Landslide Risk Engine (Phase 8H)
======================================================
Tests:
17. Valid NER location (Guwahati & Tawang)
18. Outside NER location (New Delhi rejected cleanly)
19. End-to-end schema verification (all top-level and nested keys present and typed)
20. Score bounds (susceptibility_score, trigger_score, risk_score all in [0.0, 1.0])
21. Reason-code generation (contains structured reason codes)
22. No rainfall values invented (unobserved remains None)
23. Mock rainfall integration (testing HIGH risk trigger on HIGH susceptibility)
"""

import pytest
from src.inference.risk_engine import RiskEngine, evaluate_location_risk


@pytest.fixture(scope="module")
def engine():
    return RiskEngine()


def test_valid_ner_location_guwahati(engine):
    # Guwahati: 26.1445, 91.7362
    res = engine.evaluate_risk(26.1445, 91.7362)

    assert res["status"] == "SUCCESS"
    assert res["location"]["supported_domain"] is True
    assert res["location"]["state"] == "Assam"
    assert res["location"]["country"] == "India"

    # Static susceptibility
    susc = res["static_susceptibility"]
    assert 0.0 <= susc["score"] <= 1.0
    assert susc["category"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]

    # Rainfall
    rf = res["rainfall"]
    assert rf["source"] == "CWC"
    assert rf["station"] is not None
    assert rf["distance_km"] < 20.0  # Station close to Guwahati

    # Risk
    risk = res["risk"]
    assert risk["risk_level"] in ["LOW", "WATCH", "HIGH", "CRITICAL"]
    assert 0.0 <= risk["risk_score"] <= 1.0
    assert len(risk["reasons"]) > 0


def test_valid_ner_location_tawang(engine):
    # Tawang: 27.5925, 91.6087 (station > 50km away)
    res = engine.evaluate_risk(27.5925, 91.6087)

    assert res["status"] == "SUCCESS"
    rf = res["rainfall"]
    assert rf["status"] == "NO_RELIABLE_LOCAL_STATION"
    assert rf["quality"] == "NO_RELIABLE_STATION"
    assert rf["distance_km"] > 50.0
    assert rf["rainfall_1h"] is None
    assert rf["rainfall_24h"] is None

    trig = res["rainfall_trigger"]
    assert trig["trigger_level"] == "NO_DATA"

    risk = res["risk"]
    # Static susceptibility for Tawang is ~0.58 (HIGH); with NO_DATA rainfall, risk should be WATCH
    assert risk["risk_level"] == "WATCH"
    codes = [r["code"] for r in risk["reasons"]]
    assert "STATIC_HIGH_SUSCEPTIBILITY_RAINFALL_UNOBSERVED" in codes


def test_outside_ner_location(engine):
    # New Delhi: 28.6139, 77.2090
    res = engine.evaluate_risk(28.6139, 77.2090)

    assert res["status"] == "OUTSIDE_SUPPORTED_DOMAIN"
    assert res["location"]["supported_domain"] is False
    assert res["risk"] is None
    assert res["static_susceptibility"] is None


def test_schema_structure(engine):
    res = engine.evaluate_risk(26.1445, 91.7362)

    required_top_keys = [
        "status", "location", "static_susceptibility",
        "rainfall", "rainfall_trigger", "risk",
        "model_lineage", "scientific_limitations"
    ]
    for key in required_top_keys:
        assert key in res, f"Missing top-level key: {key}"

    # Verify risk block schema
    risk_keys = [
        "risk_level", "risk_label", "operational_fusion_score", "risk_score",
        "score_semantics", "scoring_mode",
        "susceptibility_score", "susceptibility_category",
        "rainfall_trigger_level", "rainfall_trigger_score",
        "reasons", "operational_action", "matrix_lookup", "scientific_limitations"
    ]
    for r_key in risk_keys:
        assert r_key in res["risk"], f"Missing risk key: {r_key}"

    assert res["risk"]["operational_fusion_score"] == res["risk"]["risk_score"]
    assert "engineering synthesis score used for ordering/visualization" in res["risk"]["score_semantics"]


def test_score_bounds(engine):
    coords = [
        (26.1445, 91.7362),
        (27.5925, 91.6087),
        (27.05, 92.60),
    ]
    for lat, lon in coords:
        res = engine.evaluate_risk(lat, lon)
        if res["status"] == "SUCCESS":
            susc_score = res["static_susceptibility"]["score"]
            fusion_score = res["risk"]["operational_fusion_score"]
            risk_score = res["risk"]["risk_score"]
            assert 0.0 <= susc_score <= 1.0
            assert 0.0 <= fusion_score <= 1.0
            assert fusion_score == risk_score

            trig_score = res["rainfall_trigger"]["trigger_score"]
            if trig_score is not None:
                assert 0.0 <= trig_score <= 1.0


def test_no_rainfall_invented_or_zeroed(engine):
    # Where rainfall is unobserved, ensure None is preserved rather than 0.0
    res = engine.evaluate_risk(27.5925, 91.6087)
    rf = res["rainfall"]
    assert rf["rainfall_1h"] is None
    assert rf["rainfall_24h"] is None
    assert rf["rainfall_3d"] is None
    assert rf["rainfall_7d"] is None

    # Quality notes must explain CWC 50km policy and IMD macro policy transparently
    assert "50.0 km" in rf["quality_notes"]
    assert "IMD district/state observations are retained as an available macro operational source" in rf["quality_notes"]
    assert "no unvalidated station-to-IMD spatial mapping is assumed" in rf["quality_notes"]

    # When unobserved, operational_fusion_score must match static baseline
    susc_score = res["static_susceptibility"]["score"]
    assert res["risk"]["operational_fusion_score"] == round(susc_score, 4)


def test_imd_macro_integration(engine):
    from src.inference.rainfall_provider import get_imd_macro_rainfall, get_imd_district_rainfall

    # 1. State-level IMD query
    st_res = get_imd_macro_rainfall("Assam", "2026-08-20")
    assert st_res is not None
    assert st_res["source"] == "IMD"
    assert st_res["state"] == "ASSAM"
    assert st_res["date"] == "2026-08-20"
    assert st_res["daily_actual_mm"] == 10.8
    assert st_res["integration_level"] == "STATE_DATE"

    # Non-existent date returns None
    st_none = get_imd_macro_rainfall("Assam", "2010-01-01")
    assert st_none is None

    # 2. District-level IMD query
    dt_res = get_imd_district_rainfall("Assam", "Cachar", "2026-08-20")
    assert dt_res is not None
    assert dt_res["source"] == "IMD"
    assert dt_res["state"] == "ASSAM"
    assert dt_res["district"] == "CACHAR"
    assert dt_res["daily_actual_mm"] == 16.7
    assert dt_res["integration_level"] == "DISTRICT_DATE"

    # Non-existent district returns None
    dt_none = get_imd_district_rainfall("Assam", "NonExistentDistrict", "2026-08-20")
    assert dt_none is None


def test_mock_severe_rainfall_scenario():
    # Test end-to-end fusion with mock provider delivering 120 mm rain near a high-susceptibility point
    class MockRainfallProvider:
        def get_rainfall_for_location(self, **kwargs):
            return {
                "status": "OK",
                "source": "CWC",
                "station": "MockStation",
                "distance_km": 4.2,
                "timestamp": "2026-09-02 09:00:00",
                "rainfall_1h": 22.0,
                "rainfall_24h": 120.0,
                "rainfall_3d": 220.0,
                "rainfall_7d": 350.0,
                "coverage_24h": 1.0,
                "quality": "GOOD",
                "freshness": {"age_hours": 1.0, "freshness_status": "FRESH"},
            }

    custom_engine = RiskEngine(rainfall_provider=MockRainfallProvider())
    # Tawang is HIGH susceptibility (0.5848)
    res = custom_engine.evaluate_risk(27.5925, 91.6087)
    assert res["status"] == "SUCCESS"
    assert res["rainfall_trigger"]["trigger_level"] == "HIGH"
    assert res["risk"]["risk_level"] == "CRITICAL"
    codes = [r["code"] for r in res["risk"]["reasons"]]
    assert "RAINFALL_24H_HIGH_THRESHOLD" in codes
    assert "RAINFALL_HIGH_TRIGGER" in codes
    assert res["risk"]["operational_fusion_score"] > 0.60
    assert res["risk"]["risk_score"] > 0.60


def test_cwc_source_precedence_and_50km_boundary(engine):
    # Within 50km: CWC is primary operational telemetry source
    res_near = engine.evaluate_risk(26.1445, 91.7362)
    assert res_near["status"] == "SUCCESS"
    assert res_near["rainfall"]["source"] == "CWC"
    assert res_near["rainfall"]["distance_km"] <= 50.0

    # Beyond 50km: Returns NO_RELIABLE_LOCAL_STATION, never silently assumed local
    res_far = engine.evaluate_risk(28.5, 96.5)
    if res_far["status"] == "SUCCESS":
        assert res_far["rainfall"]["status"] == "NO_RELIABLE_LOCAL_STATION"
        assert res_far["rainfall"]["quality"] == "NO_RELIABLE_STATION"
        assert res_far["rainfall"]["distance_km"] > 50.0
        assert res_far["rainfall"]["rainfall_24h"] is None
        assert "no unvalidated station-to-IMD spatial mapping is assumed" in res_far["rainfall"]["quality_notes"]


