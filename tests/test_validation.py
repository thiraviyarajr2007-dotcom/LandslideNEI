"""
Unit and Integration Tests for Data Validation Engine (scripts/data_validation.py).
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd

# Add project root to sys.path for direct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.data_validation import (
    FEATURE_CONFIG,
    REQUIRED_FEATURES,
    TARGET_COLUMN,
    ALLOWED_TARGET_CLASSES,
    validate_feature_values,
    validate_prediction_input,
    validate_training_data
)


@pytest.fixture
def valid_sample_payload():
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
def valid_training_df():
    return pd.DataFrame([
        {
            "rainfall_24h": 20.0, "rainfall_3d": 45.0, "rainfall_7d": 80.0,
            "slope": 12.0, "elevation": 400.0, "historical_landslide": 0,
            "distance_to_landslide": 8.5, "soil_risk": 0.1, "risk": "Low"
        },
        {
            "rainfall_24h": 45.0, "rainfall_3d": 130.0, "rainfall_7d": 250.0,
            "slope": 24.0, "elevation": 650.0, "historical_landslide": 1,
            "distance_to_landslide": 4.5, "soil_risk": 0.4, "risk": "Watch"
        },
        {
            "rainfall_24h": 80.0, "rainfall_3d": 260.0, "rainfall_7d": 450.0,
            "slope": 34.0, "elevation": 800.0, "historical_landslide": 1,
            "distance_to_landslide": 2.0, "soil_risk": 0.6, "risk": "High"
        },
        {
            "rainfall_24h": 160.0, "rainfall_3d": 460.0, "rainfall_7d": 700.0,
            "slope": 45.0, "elevation": 920.0, "historical_landslide": 1,
            "distance_to_landslide": 0.8, "soil_risk": 0.9, "risk": "Critical"
        }
    ])


# ==============================================================================
# INFERENCE PAYLOAD VALIDATION TESTS
# ==============================================================================

def test_valid_inference_payload(valid_sample_payload):
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_missing_inference_field(valid_sample_payload):
    del valid_sample_payload["rainfall_24h"]
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("rainfall_24h" in err["message"] for err in result["errors"])


def test_extra_inference_field_strict(valid_sample_payload):
    valid_sample_payload["unwanted_metric"] = 123
    result = validate_prediction_input(valid_sample_payload, allow_extra_features=False)
    assert result["valid"] is False
    assert any("unwanted_metric" in err["message"] for err in result["errors"])


def test_extra_inference_field_allowed(valid_sample_payload):
    valid_sample_payload["extra_info"] = "test"
    result = validate_prediction_input(valid_sample_payload, allow_extra_features=True)
    assert result["valid"] is True
    assert any("extra_info" in warn["message"] for warn in result["warnings"])


def test_wrong_data_type(valid_sample_payload):
    valid_sample_payload["rainfall_24h"] = "heavy_rain"
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("must be numeric" in err["message"] for err in result["errors"])


def test_nan_inference_value(valid_sample_payload):
    valid_sample_payload["slope"] = float("nan")
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("cannot be NaN" in err["message"] for err in result["errors"])


def test_infinite_inference_value(valid_sample_payload):
    valid_sample_payload["elevation"] = float("inf")
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("cannot be infinite" in err["message"] for err in result["errors"])


def test_negative_rainfall(valid_sample_payload):
    valid_sample_payload["rainfall_24h"] = -15.0
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("rainfall_24h" in err["field"] and "less than 0.0" in err["message"] for err in result["errors"])


def test_invalid_slope_negative(valid_sample_payload):
    valid_sample_payload["slope"] = -5.0
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("slope" in err["field"] for err in result["errors"])


def test_invalid_slope_exceeds_90(valid_sample_payload):
    valid_sample_payload["slope"] = 105.0
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("slope" in err["field"] and "cannot exceed 90.0" in err["message"] for err in result["errors"])


def test_invalid_elevation_limits(valid_sample_payload):
    valid_sample_payload["elevation"] = 12000.0  # Higher than Mt. Everest
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("elevation" in err["field"] and "cannot exceed 9000.0" in err["message"] for err in result["errors"])


def test_invalid_historical_landslide_value(valid_sample_payload):
    valid_sample_payload["historical_landslide"] = 5
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("historical_landslide" in err["field"] and "must be 0 or 1" in err["message"] for err in result["errors"])


def test_negative_distance(valid_sample_payload):
    valid_sample_payload["distance_to_landslide"] = -2.5
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("distance_to_landslide" in err["field"] and "less than 0.0" in err["message"] for err in result["errors"])


def test_invalid_soil_risk_exceeds_one(valid_sample_payload):
    valid_sample_payload["soil_risk"] = 1.8
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("soil_risk" in err["field"] and "cannot exceed 1.0" in err["message"] for err in result["errors"])


def test_invalid_soil_risk_negative(valid_sample_payload):
    valid_sample_payload["soil_risk"] = -0.2
    result = validate_prediction_input(valid_sample_payload)
    assert result["valid"] is False
    assert any("soil_risk" in err["field"] and "less than 0.0" in err["message"] for err in result["errors"])


# ==============================================================================
# TRAINING DATASET VALIDATION TESTS
# ==============================================================================

def test_valid_training_dataframe(valid_training_df):
    result = validate_training_data(valid_training_df)
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["row_count"] == 4


def test_missing_column_training(valid_training_df):
    df_missing = valid_training_df.drop(columns=["slope"])
    result = validate_training_data(df_missing)
    assert result["valid"] is False
    assert any("slope" in err["message"] for err in result["errors"])


def test_missing_target_column(valid_training_df):
    df_no_target = valid_training_df.drop(columns=["risk"])
    result = validate_training_data(df_no_target)
    assert result["valid"] is False
    assert any("target column" in err["message"] for err in result["errors"])


def test_extra_column_training(valid_training_df):
    df_extra = valid_training_df.copy()
    df_extra["unrelated_col"] = [1, 2, 3, 4]
    result = validate_training_data(df_extra, allow_extra_columns=False)
    assert result["valid"] is False
    assert any("unexpected columns" in err["message"] for err in result["errors"])


def test_nan_in_training_features(valid_training_df):
    df_nan = valid_training_df.copy()
    df_nan.loc[0, "rainfall_24h"] = np.nan
    result = validate_training_data(df_nan)
    assert result["valid"] is False
    assert any("rainfall_24h" in err["field"] and "null/NaN" in err["message"] for err in result["errors"])


def test_infinity_in_training_features(valid_training_df):
    df_inf = valid_training_df.copy()
    df_inf.loc[0, "elevation"] = np.inf
    result = validate_training_data(df_inf)
    assert result["valid"] is False
    assert any("elevation" in err["field"] and "infinite" in err["message"] for err in result["errors"])


def test_duplicate_rows_warning(valid_training_df):
    df_dup = pd.concat([valid_training_df, valid_training_df.iloc[[0]]], ignore_index=True)
    result = validate_training_data(df_dup)
    assert result["valid"] is True  # Duplicates generate warning, not blocking error
    assert any("duplicate row" in warn["message"] for warn in result["warnings"])


def test_invalid_target_label(valid_training_df):
    df_bad_target = valid_training_df.copy()
    df_bad_target.loc[0, "risk"] = "ExtremeDanger"  # Not in Allowed Target Classes
    result = validate_training_data(df_bad_target)
    assert result["valid"] is False
    assert any("Invalid target labels" in err["message"] for err in result["errors"])


def test_real_demo_csv_validation():
    demo_df = pd.read_csv("data/raw/landslide_training.csv")
    result = validate_training_data(demo_df)
    assert result["valid"] is True
    assert result["row_count"] == 18
    assert len(result["errors"]) == 0
    assert "Critical" in result["class_distribution"]
