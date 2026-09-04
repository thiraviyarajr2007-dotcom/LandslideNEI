"""
Unit and Integration Tests for Document-to-Feature Extraction Bridge (scripts/extract_features.py).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.data_validation import REQUIRED_FEATURES
from scripts.extract_features import (
    parse_numeric_with_unit,
    normalize_rainfall,
    normalize_slope,
    normalize_elevation,
    normalize_distance,
    normalize_soil_risk,
    parse_historical_landslide,
    extract_features_from_entities,
    predict_from_document,
)


@pytest.fixture
def complete_entity_payload():
    return {
        "entities": {
            "24-hour rainfall": ["182 mm"],
            "3-day rainfall": ["420 mm"],
            "7-day rainfall": ["650 mm"],
            "slope angle": ["38 degrees"],
            "elevation": ["850 metres"],
            "historical landslide": ["occurred in 2022"],
            "distance to landslide": ["0.8 km"],
            "soil risk": ["0.70"]
        }
    }


# ==============================================================================
# 1. UNIT PARSING & NORMALIZATION TESTS
# ==============================================================================

def test_parse_numeric_with_unit():
    assert parse_numeric_with_unit("182 mm") == (182.0, "mm")
    assert parse_numeric_with_unit("38.5 degrees") == (38.5, "degrees")
    assert parse_numeric_with_unit("850m") == (850.0, "m")
    assert parse_numeric_with_unit("invalid text") == (None, None)


def test_normalize_rainfall_units():
    # mm (standard)
    val, unit, warn = normalize_rainfall("182 mm")
    assert val == 182.0 and warn is None

    # cm conversion (18.2 cm -> 182 mm)
    val_cm, _, _ = normalize_rainfall("18.2 cm")
    assert val_cm == 182.0

    # inches conversion (1 in -> 25.4 mm)
    val_in, _, _ = normalize_rainfall("2 in")
    assert val_in == 50.8


def test_normalize_slope():
    val, unit, warn = normalize_slope("38 degrees")
    assert val == 38.0 and warn is None

    val_deg, _, _ = normalize_slope("45°")
    assert val_deg == 45.0


def test_normalize_elevation_units():
    # meters (standard)
    val_m, _, _ = normalize_elevation("850 metres")
    assert val_m == 850.0

    # feet conversion (1000 ft -> 304.8 m)
    val_ft, _, _ = normalize_elevation("1000 ft")
    assert val_ft == 304.8

    # km conversion (1.5 km -> 1500 m)
    val_km, _, _ = normalize_elevation("1.5 km")
    assert val_km == 1500.0


def test_normalize_distance_units():
    # km (standard)
    val_km, _, _ = normalize_distance("0.8 km")
    assert val_km == 0.8

    # meters conversion (800 m -> 0.8 km)
    val_m, _, _ = normalize_distance("800 m")
    assert val_m == 0.8


def test_normalize_soil_risk():
    # Valid float
    val, _, warn = normalize_soil_risk("0.70")
    assert val == 0.7 and warn is None

    # Percentage string (70% -> 0.7)
    val_pct, _, _ = normalize_soil_risk("70%")
    assert val_pct == 0.7

    # Qualitative description should NOT fabricate number
    val_qual, _, warn = normalize_soil_risk("highly erodible clay soil")
    assert val_qual is None
    assert "qualitative" in warn.lower()


def test_parse_historical_landslide():
    # Explicit positive mentions -> 1
    val1, _ = parse_historical_landslide("Landslide occurred near site in July 2022")
    assert val1 == 1

    val2, _ = parse_historical_landslide("documented previous landslide history")
    assert val2 == 1

    # Explicit negative mentions -> 0
    val0, _ = parse_historical_landslide("No prior landslide recorded in this sector")
    assert val0 == 0

    # Unclear mention -> None
    val_none, warn = parse_historical_landslide("Site visited by geological survey")
    assert val_none is None


# ==============================================================================
# 2. ENTITY MAPPING & COMPLETENESS TESTS
# ==============================================================================

def test_complete_entity_mapping(complete_entity_payload):
    res = extract_features_from_entities(complete_entity_payload)
    assert res["prediction_ready"] is True
    assert len(res["missing_features"]) == 0
    for feat in REQUIRED_FEATURES:
        assert res["features"][feat] is not None
    assert res["features"]["rainfall_24h"] == 182.0
    assert res["features"]["rainfall_3d"] == 420.0
    assert res["features"]["rainfall_7d"] == 650.0
    assert res["features"]["slope"] == 38.0
    assert res["features"]["elevation"] == 850.0
    assert res["features"]["historical_landslide"] == 1
    assert res["features"]["distance_to_landslide"] == 0.8
    assert res["features"]["soil_risk"] == 0.70


def test_missing_rainfall_window():
    # Report has 24h rain, but missing 3d and 7d rain
    entities = {
        "24-hour rainfall": ["182 mm"],
        "slope": ["38 degrees"],
        "elevation": ["850 m"]
    }
    res = extract_features_from_entities(entities)
    assert res["prediction_ready"] is False
    assert "rainfall_3d" in res["missing_features"]
    assert "rainfall_7d" in res["missing_features"]
    assert res["features"]["rainfall_3d"] is None
    assert res["features"]["rainfall_7d"] is None


def test_missing_elevation():
    entities = {
        "24-hour rainfall": ["182 mm"],
        "3-day rainfall": ["420 mm"],
        "7-day rainfall": ["650 mm"],
        "slope": ["38 degrees"],
        "historical landslide": ["yes"],
        "distance to landslide": ["0.8 km"],
        "soil risk": ["0.70"]
    }
    res = extract_features_from_entities(entities)
    assert res["prediction_ready"] is False
    assert "elevation" in res["missing_features"]
    assert res["features"]["elevation"] is None


def test_missing_soil_risk():
    entities = {
        "24-hour rainfall": ["182 mm"],
        "3-day rainfall": ["420 mm"],
        "7-day rainfall": ["650 mm"],
        "slope": ["38 degrees"],
        "elevation": ["850 m"],
        "historical landslide": ["yes"],
        "distance to landslide": ["0.8 km"]
    }
    res = extract_features_from_entities(entities)
    assert res["prediction_ready"] is False
    assert "soil_risk" in res["missing_features"]


def test_ambiguous_generic_rainfall():
    # Document contains generic 'rainfall: 182 mm' without 24h/3d/7d specification
    entities = {
        "rainfall": ["182 mm"],
        "slope": ["38 degrees"],
    }
    res = extract_features_from_entities(entities)
    assert res["prediction_ready"] is False
    assert res["features"]["rainfall_24h"] is None
    assert res["features"]["rainfall_3d"] is None
    assert res["features"]["rainfall_7d"] is None
    assert any("time window (24h/3d/7d) is unspecified" in w for w in res["warnings"])


def test_invalid_extracted_numeric_rejected():
    # Slope = 120° violates physical sanity validation
    entities = {
        "24-hour rainfall": ["182 mm"],
        "3-day rainfall": ["420 mm"],
        "7-day rainfall": ["650 mm"],
        "slope": ["120 degrees"],  # Invalid
        "elevation": ["850 m"],
        "historical landslide": ["yes"],
        "distance to landslide": ["0.8 km"],
        "soil risk": ["0.70"]
    }
    res = extract_features_from_entities(entities)
    assert res["prediction_ready"] is False
    assert any("slope" in w and "Validation failure" in w for w in res["warnings"])


def test_source_traceability(complete_entity_payload):
    res = extract_features_from_entities(complete_entity_payload)
    assert "rainfall_24h" in res["sources"]
    assert res["sources"]["rainfall_24h"]["value"] == 182.0
    assert res["sources"]["rainfall_24h"]["source_text"] == "182 mm"
    assert "entity_label" in res["sources"]["rainfall_24h"]


# ==============================================================================
# 3. END-TO-END DOCUMENT PREDICTION BRIDGE TESTS
# ==============================================================================

def test_incomplete_document_does_not_call_predict_risk():
    incomplete_entities = {
        "entities": {
            "24-hour rainfall": ["182 mm"],
            "slope": ["38 degrees"]
        }
    }
    res = predict_from_document(incomplete_entities)
    assert res["prediction_ready"] is False
    assert res["prediction_status"] == "UNAVAILABLE_MISSING_FEATURES"
    assert res["prediction"] is None
    assert "Prediction unavailable" in res["message"]


def test_complete_document_executes_prediction(complete_entity_payload):
    res = predict_from_document(complete_entity_payload)
    assert res["prediction_ready"] is True
    assert res["prediction_status"] == "COMPLETED"
    assert res["prediction"] is not None
    assert res["prediction"]["risk"] in ["High", "Critical"]
    assert res["prediction"]["confidence"] > 0.0
    assert len(res["prediction"]["contributing_factors"]) > 0


def test_deterministic_document_extraction(complete_entity_payload):
    res1 = predict_from_document(complete_entity_payload)
    res2 = predict_from_document(complete_entity_payload)
    assert res1["features"] == res2["features"]
    assert res1["prediction"]["risk"] == res2["prediction"]["risk"]
    assert res1["prediction"]["confidence"] == res2["prediction"]["confidence"]
