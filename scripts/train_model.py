"""
Reproducible Training Pipeline and CV-Driven Model Selection.

Performs candidate model benchmarking using Stratified K-Fold Cross-Validation
STRICTLY on the training partition. The holdout test set remains completely
untouched during model selection, and is evaluated only once on the selected winner.
"""

from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Import canonical schema from shared data_validation and evaluation modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.data_validation import (
    ALLOWED_TARGET_CLASSES,
    REQUIRED_FEATURES,
    TARGET_COLUMN,
    validate_training_data,
)
from scripts.evaluate_model import (
    SEVERITY_ORDER,
    compute_multiclass_metrics,
    evaluate_cross_validation,
)

DATA_PATH: str = "data/raw/landslide_training.csv"
MODEL_DIR: str = "model"
MODEL_PATH: str = os.path.join(MODEL_DIR, "landslide_model.pkl")
FEATURE_INFO_PATH: str = os.path.join(MODEL_DIR, "feature_info.json")
FEATURE_IMPORTANCE_PATH: str = os.path.join(MODEL_DIR, "feature_importance.json")
RANDOM_STATE: int = 42


# ==============================================================================
# 1. DATA LOADING & VALIDATION
# ==============================================================================

def load_and_validate_data(data_path: str = DATA_PATH) -> pd.DataFrame:
    """
    Loads training dataset and performs schema and physical sanity checks.
    Fails fast with descriptive errors if invalid.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Training dataset not found at: {data_path}. "
            "Please ensure data/raw/landslide_training.csv exists."
        )

    data = pd.read_csv(data_path)

    # Validate against centralized schema
    val_result = validate_training_data(data, allow_extra_columns=False)
    if not val_result["valid"]:
        error_msgs = "\n".join([f"  - [{e['field']}]: {e['message']}" for e in val_result["errors"]])
        raise ValueError(
            f"Training data validation failed with {len(val_result['errors'])} error(s):\n{error_msgs}"
        )

    if val_result["warnings"]:
        print("\n[DATA VALIDATION WARNINGS]")
        for w in val_result["warnings"]:
            print(f"  * [{w['field']}]: {w['message']}")

    return data


# ==============================================================================
# 2. CANDIDATE MODELS DEFINITION
# ==============================================================================

def get_candidate_models(random_state: int = RANDOM_STATE) -> Dict[str, Any]:
    """
    Returns candidate models configured with fixed random_state for reproducibility.
    """
    return {
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            random_state=random_state,
            class_weight="balanced",
        ),
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                max_iter=2000,
                random_state=random_state,
            ))
        ]),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            random_state=random_state,
        )
    }


# ==============================================================================
# 3. CV-DRIVEN MODEL SELECTION (HOLDOUT UNTOUCHED)
# ==============================================================================

def evaluate_and_select_best_model(
    candidate_models: Dict[str, Any],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int = 3,
    random_state: int = RANDOM_STATE,
) -> Tuple[str, Any, Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Performs 3-Fold Stratified Cross-Validation STRICTLY on the training split
    to select the best model architecture. The holdout split is not touched.

    Selection priority:
      1. Mean CV Macro F1 (class-balanced harmonic mean across folds)
      2. Mean CV Critical Recall (minimizing dangerous false negatives)
      3. Mean CV High Recall
      4. Mean CV Accuracy
    """
    evaluated_candidates: Dict[str, Dict[str, Any]] = {}

    print("\n" + "=" * 60)
    print(f"CANDIDATE MODEL SELECTION ({n_splits}-FOLD STRATIFIED CV ON TRAINING SPLIT)")
    print("=" * 60)

    for name, model in candidate_models.items():
        # Stratified Cross-Validation on training data only
        cv_result = evaluate_cross_validation(
            model,
            X_train,
            y_train,
            n_splits=n_splits,
            random_state=random_state,
            class_order=SEVERITY_ORDER
        )

        evaluated_candidates[name] = {
            "model_template": model,
            "cv_metrics": cv_result,
            # Selection priority tuple
            "selection_score": (
                cv_result["mean_macro_f1"],
                cv_result["mean_critical_recall"],
                cv_result["mean_high_recall"],
                cv_result["mean_accuracy"],
            )
        }

        print(f"\nModel: {name}")
        print(f"  CV Mean Macro F1         : {cv_result['mean_macro_f1']:.4f} (+/- {cv_result['std_macro_f1']:.4f})")
        print(f"  CV Mean Critical Recall  : {cv_result['mean_critical_recall']:.4f} (+/- {cv_result['std_critical_recall']:.4f})")
        print(f"  CV Mean High Recall      : {cv_result['mean_high_recall']:.4f} (+/- {cv_result['std_high_recall']:.4f})")
        print(f"  CV Mean Accuracy         : {cv_result['mean_accuracy']:.4f} (+/- {cv_result['std_accuracy']:.4f})")

    # Deterministic multi-metric selection
    best_name = max(
        evaluated_candidates.keys(),
        key=lambda k: evaluated_candidates[k]["selection_score"]
    )
    best_entry = evaluated_candidates[best_name]

    print("\n" + "=" * 60)
    print(f"SELECTED WINNING MODEL: {best_name}")
    print(f"Selection Basis: CV Macro F1 ({best_entry['cv_metrics']['mean_macro_f1']:.4f}) -> "
          f"CV Critical Recall ({best_entry['cv_metrics']['mean_critical_recall']:.4f}) -> "
          f"CV High Recall ({best_entry['cv_metrics']['mean_high_recall']:.4f}) -> "
          f"CV Accuracy ({best_entry['cv_metrics']['mean_accuracy']:.4f})")
    print("=" * 60)

    # Fit the winning model on the full training split
    best_model = best_entry["model_template"]
    best_model.fit(X_train, y_train)

    return best_name, best_model, best_entry["cv_metrics"], evaluated_candidates


# ==============================================================================
# 4. FEATURE IMPORTANCE EXTRACTION
# ==============================================================================

def extract_feature_importance(model: Any, feature_names: List[str]) -> Dict[str, Any]:
    """
    Extracts real, model-derived feature importances or coefficient weights.
    Does NOT fabricate values.
    """
    importance_dict: Dict[str, float] = {}

    if hasattr(model, "feature_importances_"):
        # Tree-based models (RandomForest, GradientBoosting)
        raw_importances = model.feature_importances_
        for feat, imp in zip(feature_names, raw_importances):
            importance_dict[feat] = round(float(imp), 4)

        # Sort descending by importance
        sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

        return {
            "model_type": type(model).__name__,
            "method": "Gini / Mean Impurity Reduction",
            "features": sorted_importance
        }

    elif isinstance(model, Pipeline) and hasattr(model.named_steps.get("classifier"), "coef_"):
        # Linear models (LogisticRegression in Pipeline)
        clf = model.named_steps["classifier"]
        mean_abs_coef = np.mean(np.abs(clf.coef_), axis=0)
        total = np.sum(mean_abs_coef)
        norm_coef = mean_abs_coef / total if total > 0 else mean_abs_coef

        for feat, imp in zip(feature_names, norm_coef):
            importance_dict[feat] = round(float(imp), 4)

        sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

        return {
            "model_type": type(clf).__name__,
            "method": "Normalized Mean Absolute Coefficients",
            "features": sorted_importance
        }

    return {
        "model_type": type(model).__name__,
        "method": "Not applicable",
        "features": {f: 0.0 for f in feature_names}
    }


# ==============================================================================
# 5. MAIN TRAINING WORKFLOW
# ==============================================================================

def train_pipeline(
    data_path: str = DATA_PATH,
    model_dir: str = MODEL_DIR,
    random_state: int = RANDOM_STATE,
) -> Dict[str, Any]:
    """
    Executes full training pipeline:
    1. Loads and validates dataset
    2. Splits into train and untouched holdout test partitions
    3. Benchmarks candidates via Stratified CV on training partition
    4. Evaluates selected model once on untouched holdout test partition
    5. Saves serialized model, feature importance, and enriched metadata
    """
    os.makedirs(model_dir, exist_ok=True)

    print("\n--- [STEP 1/5] Loading and Validating Dataset ---")
    data = load_and_validate_data(data_path)
    print(f"Loaded {len(data)} rows with {len(REQUIRED_FEATURES)} features.")

    X = data[REQUIRED_FEATURES]
    y = data[TARGET_COLUMN]

    print("\n--- [STEP 2/5] Splitting Train/Holdout Data (75/25 Stratified) ---")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.25,
        random_state=random_state,
        stratify=y
    )
    print(f"Training set: {len(X_train)} rows | Untouched holdout test set: {len(X_test)} rows")

    print("\n--- [STEP 3/5] Selecting Best Model via 3-Fold Stratified CV on Training Set ---")
    candidates = get_candidate_models(random_state=random_state)
    best_name, best_model, best_cv_metrics, candidate_cv_summary = evaluate_and_select_best_model(
        candidates, X_train, y_train, n_splits=3, random_state=random_state
    )

    print("\n--- [STEP 4/5] Evaluating Selected Model on Untouched Holdout Test Split ---")
    y_test_pred = best_model.predict(X_test)
    holdout_metrics = compute_multiclass_metrics(y_test, y_test_pred, class_order=SEVERITY_ORDER)
    print(f"Holdout Accuracy        : {holdout_metrics['accuracy']:.4f}")
    print(f"Holdout Macro F1        : {holdout_metrics['macro_f1']:.4f}")
    print(f"Holdout Critical Recall : {holdout_metrics['critical_recall']:.4f}")
    print(f"Holdout High Recall     : {holdout_metrics['high_recall']:.4f}")

    print("\n--- [STEP 5/5] Serializing Artifacts and Metadata ---")
    model_path = os.path.join(model_dir, "landslide_model.pkl")
    feature_info_path = os.path.join(model_dir, "feature_info.json")
    feature_importance_path = os.path.join(model_dir, "feature_importance.json")

    # Extract feature importance from selected model
    feat_imp_payload = extract_feature_importance(best_model, REQUIRED_FEATURES)

    # Save feature importance
    with open(feature_importance_path, "w", encoding="utf-8") as f:
        json.dump(feat_imp_payload, f, indent=4)
    print(f"Saved feature importance to: {feature_importance_path}")

    # Save serialized model artifact
    joblib.dump(best_model, model_path)
    print(f"Saved serialized model to   : {model_path}")

    # Build and save enriched metadata
    dataset_disclaimer = (
        "Performance is measured on an 18-row synthetic demonstration dataset. "
        "These metrics serve strictly to validate software pipeline mechanics, data ingestion, "
        "and multi-class output schemas. The dataset is statistically insufficient for real-world "
        "predictive validation or operational deployment."
    )

    feature_info = {
        "model_version": "1.2.0",
        "model_type": type(best_model).__name__,
        "model_name": best_name,
        "features": REQUIRED_FEATURES,
        "target": TARGET_COLUMN,
        "classes": SEVERITY_ORDER,
        "training_dataset": data_path,
        "training_rows": len(data),
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_state": random_state,
        "validation_status": "PASSED_DEMO_VALIDATION",
        "dataset_type": "DEMO / PIPELINE VALIDATION DATA",
        "dataset_limitation": dataset_disclaimer,
        "model_selection_method": "3-Fold Stratified Cross-Validation on Training Split (Holdout Untouched)",
        "model_selection_criteria": "Priority: (1) CV Macro F1 -> (2) CV Critical Recall -> (3) CV High Recall -> (4) CV Accuracy",
        "cv_selection_metrics": {
            "mean_accuracy": best_cv_metrics["mean_accuracy"],
            "std_accuracy": best_cv_metrics["std_accuracy"],
            "mean_macro_f1": best_cv_metrics["mean_macro_f1"],
            "std_macro_f1": best_cv_metrics["std_macro_f1"],
            "mean_critical_recall": best_cv_metrics["mean_critical_recall"],
            "std_critical_recall": best_cv_metrics["std_critical_recall"],
            "mean_high_recall": best_cv_metrics["mean_high_recall"],
            "std_high_recall": best_cv_metrics["std_high_recall"],
        },
        "holdout_evaluation_metrics": {
            "accuracy": holdout_metrics["accuracy"],
            "macro_precision": holdout_metrics["macro_precision"],
            "macro_recall": holdout_metrics["macro_recall"],
            "macro_f1": holdout_metrics["macro_f1"],
            "weighted_f1": holdout_metrics["weighted_f1"],
            "high_recall": holdout_metrics["high_recall"],
            "critical_recall": holdout_metrics["critical_recall"],
        },
        "feature_importance": feat_imp_payload["features"],
    }

    with open(feature_info_path, "w", encoding="utf-8") as f:
        json.dump(feature_info, f, indent=4)
    print(f"Saved model metadata to     : {feature_info_path}")

    print("\nTraining Pipeline Completed Successfully.")

    return feature_info


if __name__ == "__main__":
    train_pipeline()