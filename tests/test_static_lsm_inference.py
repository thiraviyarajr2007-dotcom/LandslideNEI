"""
Unit and Integration Tests for Static Landslide Susceptibility Inference
========================================================================
Covers the 12 required test cases for Phase 8G:
1. Valid coordinate
2. Outside-NER coordinate
3. Invalid latitude
4. Invalid longitude
5. Boundary/edge coordinate
6. Model loading
7. Required feature contract
8. Missing-value handling
9. Probability bounds
10. JSON schema
11. Category thresholds
12. WorldCover label mapping
"""

import math
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.inference.location_profiler import (
    LocationProfiler,
    profile_location,
    WORLDCOVER_LEGEND,
    WRB_CLASS_MAP,
    DEFAULT_SUSCEPTIBILITY_CATEGORIES,
)


@pytest.fixture(scope="module")
def profiler():
    """Module-level LocationProfiler instance with cached rasters."""
    p = LocationProfiler()
    yield p
    p.close()


# ------------------------------------------------------------------------------
# Test 1: Valid Coordinate Profiling
# ------------------------------------------------------------------------------
def test_valid_coordinate(profiler):
    lat, lon = 27.5925, 91.6087 # Tawang, Arunachal Pradesh
    res = profiler.profile_location(lat, lon)

    assert res["status"] == "SUCCESS"
    assert res["location"]["supported_domain"] is True
    assert res["location"]["state"] == "Arunachal Pradesh"
    assert res["location"]["country"] == "India"

    # Terrain
    assert isinstance(res["terrain"]["elevation_m"], (int, float))
    assert res["terrain"]["elevation_m"] > 0
    assert 0.0 <= res["terrain"]["slope_deg"] <= 90.0
    assert 0.0 <= res["terrain"]["aspect_deg"] <= 360.0

    # Soil
    assert res["soil"]["soil_class"] in WRB_CLASS_MAP.values()
    assert 0.0 <= res["soil"]["clay_percent"] <= 100.0

    # Landcover
    assert res["landcover"]["landcover_class"] in WORLDCOVER_LEGEND.values()

    # Susceptibility
    assert 0.0 <= res["susceptibility"]["score"] <= 1.0
    assert res["susceptibility"]["category"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    assert res["quality"]["status"] == "OK"


# ------------------------------------------------------------------------------
# Test 2: Outside-NER Coordinate
# ------------------------------------------------------------------------------
def test_outside_ner_coordinate(profiler):
    lat, lon = 28.6139, 77.2090 # New Delhi
    res = profiler.profile_location(lat, lon)

    assert res["status"] == "OUTSIDE_SUPPORTED_DOMAIN"
    assert res["location"]["supported_domain"] is False
    assert "outside" in res["error"].lower()
    assert len(res["supported_states"]) == 8


# ------------------------------------------------------------------------------
# Test 3: Invalid Latitude
# ------------------------------------------------------------------------------
def test_invalid_latitude(profiler):
    res_high = profiler.profile_location(95.0, 91.0)
    assert res_high["status"] == "OUTSIDE_SUPPORTED_DOMAIN"
    assert "invalid latitude" in res_high["error"].lower()

    res_low = profiler.profile_location(-95.0, 91.0)
    assert res_low["status"] == "OUTSIDE_SUPPORTED_DOMAIN"
    assert "invalid latitude" in res_low["error"].lower()


# ------------------------------------------------------------------------------
# Test 4: Invalid Longitude
# ------------------------------------------------------------------------------
def test_invalid_longitude(profiler):
    res_high = profiler.profile_location(25.0, 195.0)
    assert res_high["status"] == "OUTSIDE_SUPPORTED_DOMAIN"
    assert "invalid longitude" in res_high["error"].lower()

    res_low = profiler.profile_location(25.0, -195.0)
    assert res_low["status"] == "OUTSIDE_SUPPORTED_DOMAIN"
    assert "invalid longitude" in res_low["error"].lower()


# ------------------------------------------------------------------------------
# Test 5: Boundary / Edge Coordinate
# ------------------------------------------------------------------------------
def test_boundary_edge_coordinate(profiler):
    # A point on the border of Assam/Meghalaya
    lat, lon = 25.99, 91.50
    res = profiler.profile_location(lat, lon)
    assert res["status"] in ["SUCCESS", "OUTSIDE_SUPPORTED_DOMAIN"]
    if res["status"] == "SUCCESS":
        assert 0.0 <= res["susceptibility"]["score"] <= 1.0


# ------------------------------------------------------------------------------
# Test 6: Model Loading
# ------------------------------------------------------------------------------
def test_model_loading(profiler):
    assert profiler.pipeline is not None
    assert hasattr(profiler.pipeline, "predict_proba")
    assert profiler.metadata is not None
    assert profiler.metadata["selected_model"] == "Model A (Environmental Only)"


# ------------------------------------------------------------------------------
# Test 7: Required Feature Contract
# ------------------------------------------------------------------------------
def test_feature_contract(profiler):
    expected_numeric = [
        "elevation_m", "slope_deg", "aspect_deg", "relief_std_5x5_m",
        "clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3"
    ]
    expected_categorical = ["soil_class", "landcover_class"]

    assert profiler.numeric_features == expected_numeric
    assert profiler.categorical_features == expected_categorical
    assert len(profiler.required_features) == 10

    # Ensure proximity features are strictly excluded
    assert "distance_to_road_m" not in profiler.required_features
    assert "distance_to_river_m" not in profiler.required_features
    assert "distance_to_nearest_other_landslide_m" not in profiler.required_features


# ------------------------------------------------------------------------------
# Test 8: Missing-Value Handling & Imputation
# ------------------------------------------------------------------------------
def test_missing_value_handling(profiler):
    # Construct synthetic record with missing features
    sample_with_nans = pd.DataFrame([{
        "elevation_m": 1500.0,
        "slope_deg": 28.0,
        "aspect_deg": np.nan, # Missing aspect
        "relief_std_5x5_m": 20.0,
        "clay_percent": np.nan, # Missing soil
        "sand_percent": 35.0,
        "silt_percent": 35.0,
        "bulk_density_kg_dm3": 1.15,
        "soil_class": np.nan, # Missing categorical soil
        "landcover_class": "Tree cover"
    }])

    # Preprocessing pipeline inside Model A should impute without throwing an error
    prob = profiler.pipeline.predict_proba(sample_with_nans)[0, 1]
    assert isinstance(prob, (int, float))
    assert 0.0 <= prob <= 1.0


# ------------------------------------------------------------------------------
# Test 9: Probability Bounds
# ------------------------------------------------------------------------------
def test_probability_bounds(profiler):
    test_points = [
        (27.5925, 91.6087), # Tawang
        (25.5788, 91.8933), # Shillong
        (26.1445, 91.7362), # Guwahati
        (23.7271, 92.7176), # Aizawl
        (27.3389, 88.6065), # Gangtok
    ]
    for lat, lon in test_points:
        res = profiler.profile_location(lat, lon)
        if res["status"] == "SUCCESS":
            score = res["susceptibility"]["score"]
            assert not math.isnan(score)
            assert not math.isinf(score)
            assert 0.0 <= score <= 1.0


# ------------------------------------------------------------------------------
# Test 10: JSON Schema Structure
# ------------------------------------------------------------------------------
def test_json_schema(profiler):
    res = profiler.profile_location(27.5925, 91.6087)
    required_top_level = [
        "status", "location", "terrain", "soil", "landcover",
        "susceptibility", "quality", "explainability", "model"
    ]
    for key in required_top_level:
        assert key in res, f"Missing key: {key}"

    # Verify explainability sub-keys
    assert "reason_codes" in res["explainability"]
    assert "model_level_top_features" in res["explainability"]
    assert "disclaimer" in res["explainability"]


# ------------------------------------------------------------------------------
# Test 11: Category Thresholds
# ------------------------------------------------------------------------------
def test_category_thresholds(profiler):
    assert profiler._assign_susceptibility_category(0.00) == "LOW"
    assert profiler._assign_susceptibility_category(0.24) == "LOW"
    assert profiler._assign_susceptibility_category(0.25) == "MODERATE"
    assert profiler._assign_susceptibility_category(0.49) == "MODERATE"
    assert profiler._assign_susceptibility_category(0.50) == "HIGH"
    assert profiler._assign_susceptibility_category(0.74) == "HIGH"
    assert profiler._assign_susceptibility_category(0.75) == "VERY_HIGH"
    assert profiler._assign_susceptibility_category(1.00) == "VERY_HIGH"


# ------------------------------------------------------------------------------
# Test 12: WorldCover Label Mapping
# ------------------------------------------------------------------------------
def test_worldcover_label_mapping():
    assert WORLDCOVER_LEGEND[10] == "Tree cover"
    assert WORLDCOVER_LEGEND[20] == "Shrubland"
    assert WORLDCOVER_LEGEND[30] == "Grassland"
    assert WORLDCOVER_LEGEND[40] == "Cropland"
    assert WORLDCOVER_LEGEND[50] == "Built-up"
    assert WORLDCOVER_LEGEND[60] == "Bare / sparse vegetation"
    assert WORLDCOVER_LEGEND[70] == "Snow and ice"
    assert WORLDCOVER_LEGEND[80] == "Permanent water bodies"
    assert WORLDCOVER_LEGEND[90] == "Herbaceous wetland"
    assert WORLDCOVER_LEGEND[95] == "Mangroves"
    assert WORLDCOVER_LEGEND[100] == "Moss and lichen"
    assert 0 not in WORLDCOVER_LEGEND
