"""
Unit and Integration Tests for Model Evaluation Suite (scripts/evaluate_model.py).
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.evaluate_model import (
    SEVERITY_ORDER,
    compute_multiclass_metrics,
    evaluate_cross_validation,
    run_evaluation_suite,
)


@pytest.fixture
def perfect_multiclass_data():
    y_true = ["Low", "Watch", "High", "Critical"]
    y_pred = ["Low", "Watch", "High", "Critical"]
    return y_true, y_pred


@pytest.fixture
def imperfect_multiclass_data():
    y_true = ["Low", "Low", "Watch", "High", "Critical", "Critical"]
    y_pred = ["Low", "Watch", "Watch", "High", "Critical", "High"]
    return y_true, y_pred


def test_metrics_calculation_perfect(perfect_multiclass_data):
    y_true, y_pred = perfect_multiclass_data
    metrics = compute_multiclass_metrics(y_true, y_pred, class_order=SEVERITY_ORDER)

    assert metrics["accuracy"] == 1.0
    assert metrics["macro_precision"] == 1.0
    assert metrics["macro_recall"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["critical_recall"] == 1.0
    assert metrics["high_recall"] == 1.0


def test_metrics_calculation_imperfect(imperfect_multiclass_data):
    y_true, y_pred = imperfect_multiclass_data
    metrics = compute_multiclass_metrics(y_true, y_pred, class_order=SEVERITY_ORDER)

    assert metrics["accuracy"] < 1.0
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert 0.0 <= metrics["critical_recall"] <= 1.0
    assert 0.0 <= metrics["high_recall"] <= 1.0


def test_confusion_matrix_shape_and_ordering():
    y_true = ["Low", "Watch", "High", "Critical"]
    y_pred = ["Low", "Watch", "High", "Critical"]
    metrics = compute_multiclass_metrics(y_true, y_pred, class_order=SEVERITY_ORDER)

    # 4x4 matrix
    assert np.array(metrics["confusion_matrix_raw"]).shape == (4, 4)
    assert metrics["class_order"] == ["Low", "Watch", "High", "Critical"]

    cm = metrics["confusion_matrix"]
    assert set(cm.keys()) == {"Low", "Watch", "High", "Critical"}
    for actual in SEVERITY_ORDER:
        assert set(cm[actual].keys()) == {"Low", "Watch", "High", "Critical"}
        assert cm[actual][actual] == 1


def test_zero_division_safety_missing_class():
    # Only Low and Watch are present in predictions
    y_true = ["Low", "Watch"]
    y_pred = ["Low", "Low"]
    metrics = compute_multiclass_metrics(y_true, y_pred, class_order=SEVERITY_ORDER)

    assert metrics["per_class"]["High"]["precision"] == 0.0
    assert metrics["per_class"]["High"]["recall"] == 0.0
    assert metrics["per_class"]["Critical"]["precision"] == 0.0
    assert metrics["per_class"]["Critical"]["recall"] == 0.0


def test_cross_validation_insufficient_samples():
    # If smallest class has only 1 sample, stratified CV should report limitation safely
    df_tiny = pd.DataFrame({
        "f1": [1, 2, 3, 4],
        "risk": ["Low", "Watch", "High", "Critical"]
    })
    model = RandomForestClassifier(random_state=42)
    cv_res = evaluate_cross_validation(
        model, df_tiny[["f1"]], df_tiny["risk"], n_splits=3, random_state=42
    )

    assert cv_res["status"] == "INSUFFICIENT_DATA"
    assert cv_res["n_splits"] == 0


def test_deterministic_evaluation():
    res1 = run_evaluation_suite(save_results=False, random_state=42)
    res2 = run_evaluation_suite(save_results=False, random_state=42)

    assert res1["primary_model"]["holdout_metrics"]["macro_f1"] == res2["primary_model"]["holdout_metrics"]["macro_f1"]
    assert res1["primary_model"]["cross_validation"]["mean_macro_f1"] == res2["primary_model"]["cross_validation"]["mean_macro_f1"]


def test_valid_json_output_structure(tmp_path):
    out_file = str(tmp_path / "eval_test.json")
    res = run_evaluation_suite(output_path=out_file, save_results=True)

    assert os.path.exists(out_file)
    assert res["dataset"]["type"] == "DEMO / PIPELINE VALIDATION DATA"
    assert "limitation" in res["dataset"]
    assert "High" in res["primary_model"]["holdout_metrics"]["per_class"]
    assert "Critical" in res["primary_model"]["holdout_metrics"]["per_class"]
