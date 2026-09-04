"""
Unit and Behavioral Tests for Training Pipeline and Model Selection (scripts/train_model.py).
"""

import json
import os
import sys
import pytest
import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.data_validation import REQUIRED_FEATURES, TARGET_COLUMN
from scripts.train_model import (
    DATA_PATH,
    MODEL_PATH,
    FEATURE_INFO_PATH,
    FEATURE_IMPORTANCE_PATH,
    load_and_validate_data,
    get_candidate_models,
    evaluate_and_select_best_model,
    extract_feature_importance,
    train_pipeline,
)
from scripts.predict import predict_risk


def test_valid_training_data_loads():
    df = load_and_validate_data(DATA_PATH)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert TARGET_COLUMN in df.columns
    for feat in REQUIRED_FEATURES:
        assert feat in df.columns


def test_invalid_training_data_fails_validation(tmp_path):
    # Create corrupted CSV with negative rainfall
    bad_csv = tmp_path / "bad_landslide.csv"
    bad_df = pd.DataFrame([{
        "rainfall_24h": -50.0,  # Invalid
        "rainfall_3d": 45.0,
        "rainfall_7d": 80.0,
        "slope": 12.0,
        "elevation": 400.0,
        "historical_landslide": 0,
        "distance_to_landslide": 8.5,
        "soil_risk": 0.1,
        "risk": "Low"
    }])
    bad_df.to_csv(bad_csv, index=False)

    with pytest.raises(ValueError, match="Training data validation failed"):
        load_and_validate_data(str(bad_csv))


def test_target_not_included_in_features():
    df = load_and_validate_data(DATA_PATH)
    X = df[REQUIRED_FEATURES]
    assert TARGET_COLUMN not in X.columns
    assert TARGET_COLUMN not in REQUIRED_FEATURES


def test_candidate_models_structure():
    candidates = get_candidate_models(random_state=42)
    assert "Random Forest" in candidates
    assert "Logistic Regression" in candidates
    assert "Gradient Boosting" in candidates


def test_model_selection_uses_cv_metrics():
    df = load_and_validate_data(DATA_PATH)
    X = df[REQUIRED_FEATURES]
    y = df[TARGET_COLUMN]

    candidates = get_candidate_models(random_state=42)
    best_name, best_model, best_cv, evaluated_candidates = evaluate_and_select_best_model(
        candidates, X, y, n_splits=3, random_state=42
    )

    assert best_name in candidates
    assert "mean_macro_f1" in best_cv
    assert "mean_critical_recall" in best_cv
    assert hasattr(best_model, "predict")

    # Verify selection matches highest CV score
    scores = {name: data["cv_metrics"]["mean_macro_f1"] for name, data in evaluated_candidates.items()}
    assert best_cv["mean_macro_f1"] == max(scores.values())


def test_model_selection_deterministic():
    df = load_and_validate_data(DATA_PATH)
    X = df[REQUIRED_FEATURES]
    y = df[TARGET_COLUMN]

    candidates1 = get_candidate_models(random_state=42)
    best_name1, _, cv1, _ = evaluate_and_select_best_model(
        candidates1, X, y, n_splits=3, random_state=42
    )

    candidates2 = get_candidate_models(random_state=42)
    best_name2, _, cv2, _ = evaluate_and_select_best_model(
        candidates2, X, y, n_splits=3, random_state=42
    )

    assert best_name1 == best_name2
    assert cv1["mean_macro_f1"] == cv2["mean_macro_f1"]


def test_feature_importance_extraction():
    df = load_and_validate_data(DATA_PATH)
    X = df[REQUIRED_FEATURES]
    y = df[TARGET_COLUMN]

    candidates = get_candidate_models(random_state=42)
    rf = candidates["Random Forest"]
    rf.fit(X, y)

    feat_imp = extract_feature_importance(rf, REQUIRED_FEATURES)
    assert feat_imp["model_type"] == "RandomForestClassifier"
    assert set(feat_imp["features"].keys()) == set(REQUIRED_FEATURES)
    total_importance = sum(feat_imp["features"].values())
    assert 0.95 <= total_importance <= 1.05


def test_training_pipeline_artifacts_creation(tmp_path):
    temp_model_dir = str(tmp_path / "model_test")
    res = train_pipeline(data_path=DATA_PATH, model_dir=temp_model_dir, random_state=42)

    # Check artifacts exist
    saved_model_file = os.path.join(temp_model_dir, "landslide_model.pkl")
    feat_info_file = os.path.join(temp_model_dir, "feature_info.json")
    feat_imp_file = os.path.join(temp_model_dir, "feature_importance.json")

    assert os.path.exists(saved_model_file)
    assert os.path.exists(feat_info_file)
    assert os.path.exists(feat_imp_file)

    # Check model is loadable
    loaded_model = joblib.load(saved_model_file)
    assert hasattr(loaded_model, "predict")

    # Check metadata fields
    with open(feat_info_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["model_version"] == "1.2.0"
    assert meta["target"] == "risk"
    assert meta["training_rows"] == 18
    assert "cv_selection_metrics" in meta
    assert "holdout_evaluation_metrics" in meta
    assert "dataset_limitation" in meta


def test_saved_model_prediction_compatibility():
    # Verify existing predict_risk still works with saved model
    low_sample = {
        "rainfall_24h": 20, "rainfall_3d": 45, "rainfall_7d": 80,
        "slope": 12, "elevation": 400, "historical_landslide": 0,
        "distance_to_landslide": 8.5, "soil_risk": 0.1
    }
    result_low = predict_risk(low_sample)
    assert result_low["risk"] in ["Low", "Watch", "High", "Critical"]
    assert "probabilities" in result_low
    assert result_low["confidence"] > 0.0

    high_sample = {
        "rainfall_24h": 180, "rainfall_3d": 500, "rainfall_7d": 750,
        "slope": 47, "elevation": 950, "historical_landslide": 1,
        "distance_to_landslide": 0.5, "soil_risk": 0.9
    }
    result_high = predict_risk(high_sample)
    assert result_high["risk"] in ["High", "Critical"]
