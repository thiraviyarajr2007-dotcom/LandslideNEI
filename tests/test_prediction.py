"""
Unit and Integration Tests for Production Prediction Engine (scripts/predict.py).
"""

from datetime import datetime
import json
import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.data_validation import REQUIRED_FEATURES
from scripts.evaluate_model import SEVERITY_ORDER
from scripts.predict import (
    REASON_RULES,
    load_model_artifacts,
    generate_contributing_factors,
    predict_risk,
)


@pytest.fixture
def low_risk_payload():
    return {
        "rainfall_24h": 20.0,
        "rainfall_3d": 45.0,
        "rainfall_7d": 80.0,
        "slope": 12.0,
        "elevation": 400.0,
        "historical_landslide": 0,
        "distance_to_landslide": 8.5,
        "soil_risk": 0.1
    }


@pytest.fixture
def high_risk_payload():
    return {
        "rainfall_24h": 182.0,
        "rainfall_3d": 420.0,
        "rainfall_7d": 650.0,
        "slope": 38.0,
        "elevation": 850.0,
        "historical_landslide": 1,
        "distance_to_landslide": 0.8,
        "soil_risk": 0.7
    }


# ==============================================================================
# 1. CORE PREDICTION & PROBABILITY TESTS
# ==============================================================================

def test_valid_low_risk_prediction(low_risk_payload):
    result = predict_risk(low_risk_payload)
    assert result["risk"] == "Low"
    assert result["confidence"] > 0.5
    assert result["probabilities"]["Low"] == result["confidence"]


def test_valid_high_risk_prediction(high_risk_payload):
    result = predict_risk(high_risk_payload)
    assert result["risk"] in ["High", "Critical"]
    assert result["confidence"] > 0.5
    assert result["probabilities"][result["risk"]] == result["confidence"]


def test_prediction_output_schema(low_risk_payload):
    result = predict_risk(low_risk_payload)
    required_keys = {"risk", "confidence", "probabilities", "contributing_factors", "model_version", "prediction_timestamp"}
    assert required_keys.issubset(result.keys())
    assert isinstance(result["risk"], str)
    assert isinstance(result["confidence"], float)
    assert isinstance(result["probabilities"], dict)
    assert isinstance(result["contributing_factors"], list)


def test_all_four_classes_present_in_probabilities(low_risk_payload):
    result = predict_risk(low_risk_payload)
    probs = result["probabilities"]
    for expected_cls in SEVERITY_ORDER:
        assert expected_cls in probs
        assert isinstance(probs[expected_cls], float)
        assert 0.0 <= probs[expected_cls] <= 1.0


def test_probabilities_sum_to_one(low_risk_payload, high_risk_payload):
    for payload in [low_risk_payload, high_risk_payload]:
        res = predict_risk(payload)
        prob_sum = sum(res["probabilities"].values())
        assert abs(prob_sum - 1.0) < 0.01


def test_confidence_equals_predicted_class_probability(low_risk_payload, high_risk_payload):
    for payload in [low_risk_payload, high_risk_payload]:
        res = predict_risk(payload)
        pred_class = res["risk"]
        assert res["confidence"] == res["probabilities"][pred_class]


def test_prediction_timestamp_utc_format(low_risk_payload):
    res = predict_risk(low_risk_payload)
    ts = res["prediction_timestamp"]
    parsed_dt = datetime.fromisoformat(ts)
    assert parsed_dt.tzinfo is not None


# ==============================================================================
# 2. INPUT VALIDATION & ERROR REJECTION TESTS
# ==============================================================================

def test_missing_feature_rejected(low_risk_payload):
    del low_risk_payload["slope"]
    with pytest.raises(ValueError, match="Missing required features"):
        predict_risk(low_risk_payload)


def test_unexpected_feature_rejected_strict(low_risk_payload):
    low_risk_payload["extra_unwanted"] = 123
    with pytest.raises(ValueError, match="Unexpected extra features"):
        predict_risk(low_risk_payload, allow_extra_features=False)


def test_unexpected_feature_allowed_when_flag_set(low_risk_payload):
    low_risk_payload["extra_unwanted"] = 123
    res = predict_risk(low_risk_payload, allow_extra_features=True)
    assert res["risk"] == "Low"


def test_wrong_data_type_rejected(low_risk_payload):
    low_risk_payload["rainfall_24h"] = "one_hundred"
    with pytest.raises(ValueError, match="must be numeric"):
        predict_risk(low_risk_payload)


def test_nan_value_rejected(low_risk_payload):
    low_risk_payload["elevation"] = float("nan")
    with pytest.raises(ValueError, match="cannot be NaN"):
        predict_risk(low_risk_payload)


def test_infinite_value_rejected(low_risk_payload):
    low_risk_payload["elevation"] = float("inf")
    with pytest.raises(ValueError, match="cannot be infinite"):
        predict_risk(low_risk_payload)


def test_negative_rainfall_rejected(low_risk_payload):
    low_risk_payload["rainfall_24h"] = -10.0
    with pytest.raises(ValueError, match="cannot be less than 0.0"):
        predict_risk(low_risk_payload)


def test_invalid_slope_rejected(low_risk_payload):
    low_risk_payload["slope"] = 95.0
    with pytest.raises(ValueError, match="cannot exceed 90.0"):
        predict_risk(low_risk_payload)


def test_invalid_elevation_rejected(low_risk_payload):
    low_risk_payload["elevation"] = 10000.0
    with pytest.raises(ValueError, match="cannot exceed 9000.0"):
        predict_risk(low_risk_payload)


def test_invalid_historical_landslide_rejected(low_risk_payload):
    low_risk_payload["historical_landslide"] = 2
    with pytest.raises(ValueError, match="must be 0 or 1"):
        predict_risk(low_risk_payload)


def test_negative_distance_rejected(low_risk_payload):
    low_risk_payload["distance_to_landslide"] = -5.0
    with pytest.raises(ValueError, match="cannot be less than 0.0"):
        predict_risk(low_risk_payload)


def test_invalid_soil_risk_rejected(low_risk_payload):
    low_risk_payload["soil_risk"] = 1.5
    with pytest.raises(ValueError, match="cannot exceed 1.0"):
        predict_risk(low_risk_payload)


# ==============================================================================
# 3. EXPLAINABILITY & NON-CAUSAL REASON CODE TESTS
# ==============================================================================

def test_contributing_factors_deterministic(high_risk_payload):
    res1 = predict_risk(high_risk_payload)
    res2 = predict_risk(high_risk_payload)
    assert res1["contributing_factors"] == res2["contributing_factors"]


def test_contributing_factors_limited_to_five(high_risk_payload):
    res = predict_risk(high_risk_payload)
    assert len(res["contributing_factors"]) <= 5
    assert len(res["contributing_factors"]) > 0


def test_contributing_factors_ordered_by_importance():
    sample = {
        "rainfall_24h": 150.0,
        "rainfall_3d": 350.0,
        "rainfall_7d": 600.0,
        "slope": 40.0,
        "elevation": 800.0,
        "historical_landslide": 1,
        "distance_to_landslide": 0.5,
        "soil_risk": 0.8
    }
    importance_map = {
        "rainfall_7d": 0.30,
        "rainfall_24h": 0.25,
        "slope": 0.20,
        "distance_to_landslide": 0.15,
        "soil_risk": 0.10
    }
    factors = generate_contributing_factors(sample, importance_map, max_factors=5)
    importances = [f["importance"] for f in factors]
    assert importances == sorted(importances, reverse=True)


def test_no_causal_wording_in_reason_rules():
    """
    Asserts that all reason rules use non-causal, transparent decision-support
    language and contain zero prohibited causal terms.
    """
    prohibited_terms = [
        "causing",
        "causes",
        "results in",
        "leads to",
        "proves",
        "guarantees",
        "caused by",
        "pore-water pressure",
        "gravitational shear stress"
    ]

    for rule in REASON_RULES:
        msg = rule["message"].lower()
        for term in prohibited_terms:
            assert term not in msg, f"Prohibited causal term '{term}' found in rule '{rule['code']}': {rule['message']}"


def test_no_causal_wording_in_prediction_output(low_risk_payload, high_risk_payload):
    prohibited_terms = ["causing", "causes", "results in", "leads to", "proves", "guarantees"]
    for payload in [low_risk_payload, high_risk_payload]:
        res = predict_risk(payload)
        for factor in res["contributing_factors"]:
            msg = factor["message"].lower()
            for term in prohibited_terms:
                assert term not in msg, f"Prohibited causal term '{term}' found in factor message: {factor['message']}"


def test_model_version_from_metadata(low_risk_payload):
    res = predict_risk(low_risk_payload)
    assert res["model_version"] == "1.2.0"


def test_model_artifacts_caching_and_reload():
    model1, meta1, imp1 = load_model_artifacts(force_reload=False)
    model2, meta2, imp2 = load_model_artifacts(force_reload=False)
    assert model1 is model2  # In-memory cached reference
    assert meta1 is meta2

    model_reloaded, _, _ = load_model_artifacts(force_reload=True)
    assert hasattr(model_reloaded, "predict")
