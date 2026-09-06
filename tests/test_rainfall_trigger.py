"""
Unit Tests for Rainfall Trigger Engine (Phase 8H)
=================================================
Tests:
1. Valid normal rainfall (thresholds not exceeded -> NORMAL)
2. Missing rainfall observation (quality=MISSING -> NO_DATA)
3. Station too far away (quality=NO_RELIABLE_STATION -> NO_DATA)
4. Stale rainfall observation (quality=STALE -> flagged STALE reason)
5. Partial coverage observation (quality=PARTIAL -> flagged PARTIAL reason)
6. 1H threshold exceeded (WATCH and HIGH)
7. 24H threshold exceeded (WATCH and HIGH)
8. Multi-window threshold exceeded (24h + 3d + 7d)
9. Continuous trigger score bounds [0.0, 1.0]
"""

import pytest
from src.inference.rainfall_trigger import RainfallTriggerEngine, evaluate_rainfall_trigger


@pytest.fixture
def trigger_engine():
    return RainfallTriggerEngine()


def test_normal_rainfall(trigger_engine):
    data = {
        "status": "OK",
        "quality": "GOOD",
        "station": "TestStation",
        "distance_km": 12.5,
        "rainfall_1h": 5.0,
        "rainfall_24h": 15.0,
        "rainfall_3d": 30.0,
        "rainfall_7d": 50.0,
        "freshness": {"age_hours": 1.0, "freshness_status": "FRESH"},
    }
    res = trigger_engine.evaluate_rainfall(data)

    assert res["trigger_level"] == "NORMAL"
    assert res["trigger_score"] is not None
    assert 0.0 <= res["trigger_score"] < 0.40
    assert len(res["trigger_reasons"]) == 0


def test_missing_rainfall(trigger_engine):
    data = {
        "status": "MISSING",
        "quality": "MISSING",
        "station": "TestStation",
        "distance_km": 15.0,
        "rainfall_1h": None,
        "rainfall_24h": None,
        "rainfall_3d": None,
        "rainfall_7d": None,
        "freshness": {"age_hours": None, "freshness_status": "UNAVAILABLE"},
    }
    res = trigger_engine.evaluate_rainfall(data)

    assert res["trigger_level"] == "NO_DATA"
    assert res["trigger_score"] is None
    codes = [r["code"] for r in res["trigger_reasons"]]
    assert "RAINFALL_DATA_MISSING" in codes


def test_station_too_far(trigger_engine):
    data = {
        "status": "NO_RELIABLE_LOCAL_STATION",
        "quality": "NO_RELIABLE_STATION",
        "station": "DistantStation",
        "distance_km": 88.5,
        "rainfall_1h": None,
        "rainfall_24h": None,
        "rainfall_3d": None,
        "rainfall_7d": None,
        "quality_notes": "Nearest station is 88.5 km away.",
    }
    res = trigger_engine.evaluate_rainfall(data)

    assert res["trigger_level"] == "NO_DATA"
    assert res["trigger_score"] is None
    codes = [r["code"] for r in res["trigger_reasons"]]
    assert "RAINFALL_NO_RELIABLE_STATION" in codes


def test_stale_rainfall(trigger_engine):
    data = {
        "status": "STALE",
        "quality": "STALE",
        "station": "TestStation",
        "distance_km": 10.0,
        "rainfall_1h": 2.0,
        "rainfall_24h": 10.0,
        "rainfall_3d": 25.0,
        "rainfall_7d": 40.0,
        "freshness": {"age_hours": 12.5, "freshness_status": "STALE", "max_acceptable_age_hours": 6.0},
    }
    res = trigger_engine.evaluate_rainfall(data)

    assert res["data_quality"]["is_stale"] is True
    codes = [r["code"] for r in res["trigger_reasons"]]
    assert "RAINFALL_DATA_STALE" in codes


def test_partial_coverage(trigger_engine):
    data = {
        "status": "OK",
        "quality": "PARTIAL",
        "station": "TestStation",
        "distance_km": 8.0,
        "rainfall_1h": 4.0,
        "rainfall_24h": 25.0,
        "rainfall_3d": 40.0,
        "rainfall_7d": 60.0,
        "coverage_24h": 0.50,
        "freshness": {"age_hours": 1.0, "freshness_status": "FRESH"},
    }
    res = trigger_engine.evaluate_rainfall(data)

    codes = [r["code"] for r in res["trigger_reasons"]]
    assert "RAINFALL_DATA_PARTIAL" in codes


def test_1h_threshold_watch_and_high(trigger_engine):
    # 1h Watch threshold: 20 mm
    data_watch = {
        "status": "OK",
        "quality": "GOOD",
        "station": "TestStation",
        "distance_km": 5.0,
        "rainfall_1h": 25.0,
        "rainfall_24h": 30.0,
        "rainfall_3d": 40.0,
        "rainfall_7d": 50.0,
    }
    res_watch = trigger_engine.evaluate_rainfall(data_watch)
    assert res_watch["trigger_level"] == "WATCH"
    codes_watch = [r["code"] for r in res_watch["trigger_reasons"]]
    assert "RAINFALL_1H_WATCH_THRESHOLD" in codes_watch

    # 1h High threshold: 40 mm
    data_high = {
        "status": "OK",
        "quality": "GOOD",
        "station": "TestStation",
        "distance_km": 5.0,
        "rainfall_1h": 45.0,
        "rainfall_24h": 60.0,
        "rainfall_3d": 70.0,
        "rainfall_7d": 80.0,
    }
    res_high = trigger_engine.evaluate_rainfall(data_high)
    assert res_high["trigger_level"] == "HIGH"
    codes_high = [r["code"] for r in res_high["trigger_reasons"]]
    assert "RAINFALL_1H_HIGH_THRESHOLD" in codes_high


def test_24h_threshold_watch_and_high(trigger_engine):
    # 24h Watch threshold: 50 mm, High: 100 mm
    data_watch = {
        "status": "OK",
        "quality": "GOOD",
        "station": "TestStation",
        "distance_km": 5.0,
        "rainfall_1h": 5.0,
        "rainfall_24h": 65.0,
        "rainfall_3d": 70.0,
        "rainfall_7d": 80.0,
    }
    res_watch = trigger_engine.evaluate_rainfall(data_watch)
    assert res_watch["trigger_level"] == "WATCH"
    codes = [r["code"] for r in res_watch["trigger_reasons"]]
    assert "RAINFALL_24H_WATCH_THRESHOLD" in codes

    data_high = {
        "status": "OK",
        "quality": "GOOD",
        "station": "TestStation",
        "distance_km": 5.0,
        "rainfall_1h": 10.0,
        "rainfall_24h": 125.0,
        "rainfall_3d": 150.0,
        "rainfall_7d": 180.0,
    }
    res_high = trigger_engine.evaluate_rainfall(data_high)
    assert res_high["trigger_level"] == "HIGH"
    codes_high = [r["code"] for r in res_high["trigger_reasons"]]
    assert "RAINFALL_24H_HIGH_THRESHOLD" in codes_high


def test_multi_window_thresholds(trigger_engine):
    data = {
        "status": "OK",
        "quality": "GOOD",
        "station": "TestStation",
        "distance_km": 3.0,
        "rainfall_1h": 45.0,   # > 40 (High)
        "rainfall_24h": 120.0, # > 100 (High)
        "rainfall_3d": 250.0,  # > 200 (High)
        "rainfall_7d": 350.0,  # > 300 (High)
    }
    res = trigger_engine.evaluate_rainfall(data)
    assert res["trigger_level"] == "HIGH"
    codes = [r["code"] for r in res["trigger_reasons"]]
    assert "RAINFALL_1H_HIGH_THRESHOLD" in codes
    assert "RAINFALL_24H_HIGH_THRESHOLD" in codes
    assert "RAINFALL_3D_HIGH_THRESHOLD" in codes
    assert "RAINFALL_7D_HIGH_THRESHOLD" in codes
    assert 0.70 <= res["trigger_score"] <= 1.0


def test_trigger_score_bounds(trigger_engine):
    for val in [0.0, 10.0, 50.0, 99.0, 100.0, 250.0]:
        data = {
            "status": "OK",
            "quality": "GOOD",
            "station": "TestStation",
            "distance_km": 5.0,
            "rainfall_1h": val / 4.0,
            "rainfall_24h": val,
            "rainfall_3d": val * 1.5,
            "rainfall_7d": val * 2.0,
        }
        res = trigger_engine.evaluate_rainfall(data)
        assert 0.0 <= res["trigger_score"] <= 1.0
