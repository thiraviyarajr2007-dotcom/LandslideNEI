"""
Comprehensive Model Evaluation Suite for Landslide Risk Assessment.

Computes multiclass metrics, confusion matrices (ordered by risk severity),
stratified cross-validation, and safety-critical recall metrics.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Import shared schema constants
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.data_validation import (
    REQUIRED_FEATURES,
    TARGET_COLUMN,
    validate_training_data,
)

# Logical severity order (not alphabetical) for meaningful decision support
SEVERITY_ORDER: List[str] = ["Low", "Watch", "High", "Critical"]
DATASET_PATH: str = "data/raw/landslide_training.csv"
SAVED_MODEL_PATH: str = "model/landslide_model.pkl"
EVAL_RESULTS_PATH: str = "model/evaluation_results.json"


# ==============================================================================
# 1. CORE MULTICLASS METRIC COMPUTATION
# ==============================================================================

def compute_multiclass_metrics(
    y_true: Union[List[str], np.ndarray, pd.Series],
    y_pred: Union[List[str], np.ndarray, pd.Series],
    class_order: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes global macro/weighted metrics, per-class metrics, and confusion matrix.
    """
    if class_order is None:
        class_order = SEVERITY_ORDER

    # Global aggregate metrics
    acc = float(accuracy_score(y_true, y_pred))
    macro_p = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    macro_r = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_p = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
    weighted_r = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    # Per-class metrics
    prec_per_class = precision_score(y_true, y_pred, labels=class_order, average=None, zero_division=0)
    rec_per_class = recall_score(y_true, y_pred, labels=class_order, average=None, zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, labels=class_order, average=None, zero_division=0)

    per_class_dict: Dict[str, Dict[str, float]] = {}
    for idx, cls_name in enumerate(class_order):
        per_class_dict[cls_name] = {
            "precision": float(prec_per_class[idx]),
            "recall": float(rec_per_class[idx]),
            "f1_score": float(f1_per_class[idx]),
        }

    # Confusion matrix with fixed class order
    cm = confusion_matrix(y_true, y_pred, labels=class_order)
    cm_dict: Dict[str, Dict[str, int]] = {}
    for i, actual_cls in enumerate(class_order):
        cm_dict[actual_cls] = {}
        for j, pred_cls in enumerate(class_order):
            cm_dict[actual_cls][pred_cls] = int(cm[i, j])

    # Early-warning safety focus metrics
    high_recall = per_class_dict.get("High", {}).get("recall", 0.0)
    critical_recall = per_class_dict.get("Critical", {}).get("recall", 0.0)
    high_f1 = per_class_dict.get("High", {}).get("f1_score", 0.0)
    critical_f1 = per_class_dict.get("Critical", {}).get("f1_score", 0.0)

    return {
        "accuracy": acc,
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "macro_f1": macro_f1,
        "weighted_precision": weighted_p,
        "weighted_recall": weighted_r,
        "weighted_f1": weighted_f1,
        "high_recall": high_recall,
        "critical_recall": critical_recall,
        "high_f1": high_f1,
        "critical_f1": critical_f1,
        "per_class": per_class_dict,
        "confusion_matrix_raw": cm.tolist(),
        "confusion_matrix": cm_dict,
        "class_order": class_order,
    }


# ==============================================================================
# 2. STRATIFIED CROSS-VALIDATION
# ==============================================================================

def evaluate_cross_validation(
    model: Any,
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 3,
    random_state: int = 42,
    class_order: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Performs stratified K-fold cross-validation and reports fold-level metrics.
    """
    if class_order is None:
        class_order = SEVERITY_ORDER

    # Verify minimum class representation for stratified splitting
    min_class_count = y.value_counts().min()
    safe_splits = min(n_splits, min_class_count)

    if safe_splits < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": f"Smallest class has only {min_class_count} sample(s); stratified CV requires at least 2.",
            "n_splits": 0,
            "folds": [],
            "mean_macro_f1": 0.0,
            "std_macro_f1": 0.0,
            "mean_critical_recall": 0.0,
        }

    skf = StratifiedKFold(n_splits=safe_splits, shuffle=True, random_state=random_state)
    folds_results: List[Dict[str, Any]] = []

    fold_macro_f1s = []
    fold_accuracies = []
    fold_critical_recalls = []
    fold_high_recalls = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y), start=1):
        X_train_f, X_val_f = X.iloc[train_idx], X.iloc[val_idx]
        y_train_f, y_val_f = y.iloc[train_idx], y.iloc[val_idx]

        # Fit model on training fold
        model.fit(X_train_f, y_train_f)
        y_pred_f = model.predict(X_val_f)

        fold_metrics = compute_multiclass_metrics(y_val_f, y_pred_f, class_order=class_order)

        fold_macro_f1s.append(fold_metrics["macro_f1"])
        fold_accuracies.append(fold_metrics["accuracy"])
        fold_critical_recalls.append(fold_metrics["critical_recall"])
        fold_high_recalls.append(fold_metrics["high_recall"])

        folds_results.append({
            "fold": fold_idx,
            "train_size": len(train_idx),
            "val_size": len(val_idx),
            "accuracy": fold_metrics["accuracy"],
            "macro_f1": fold_metrics["macro_f1"],
            "critical_recall": fold_metrics["critical_recall"],
            "high_recall": fold_metrics["high_recall"],
        })

    return {
        "status": "COMPLETED",
        "n_splits": safe_splits,
        "folds": folds_results,
        "mean_accuracy": float(np.mean(fold_accuracies)),
        "std_accuracy": float(np.std(fold_accuracies)),
        "mean_macro_f1": float(np.mean(fold_macro_f1s)),
        "std_macro_f1": float(np.std(fold_macro_f1s)),
        "mean_critical_recall": float(np.mean(fold_critical_recalls)),
        "std_critical_recall": float(np.std(fold_critical_recalls)),
        "mean_high_recall": float(np.mean(fold_high_recalls)),
        "std_high_recall": float(np.std(fold_high_recalls)),
    }


# ==============================================================================
# 3. FULL PIPELINE EVALUATION & COMPARISON
# ==============================================================================

def run_evaluation_suite(
    data_path: str = DATASET_PATH,
    saved_model_path: str = SAVED_MODEL_PATH,
    output_path: str = EVAL_RESULTS_PATH,
    save_results: bool = True,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Executes full evaluation:
    1. Validates dataset
    2. Trains and compares Logistic Regression vs Random Forest on held-out split & CV
    3. Evaluates serialized saved model
    4. Compiles structured JSON results and terminal report
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Training dataset not found: {data_path}")

    df = pd.read_csv(data_path)

    # 1. Dataset validation check
    val_res = validate_training_data(df)
    if not val_res["valid"]:
        raise ValueError(f"Dataset validation failed: {val_res['errors']}")

    X = df[REQUIRED_FEATURES]
    y = df[TARGET_COLUMN]

    # Split for hold-out test evaluation (75/25 stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state, stratify=y
    )

    candidate_models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=300, random_state=random_state, class_weight="balanced"
        ),
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=2000, random_state=random_state))
        ])
    }

    comparison_results: Dict[str, Any] = {}

    for name, model_inst in candidate_models.items():
        # Fit on train split and evaluate on test split
        model_inst.fit(X_train, y_train)
        y_test_pred = model_inst.predict(X_test)
        holdout_metrics = compute_multiclass_metrics(y_test, y_test_pred, class_order=SEVERITY_ORDER)

        # Cross validation on full dataset
        cv_metrics = evaluate_cross_validation(
            model_inst, X, y, n_splits=3, random_state=random_state, class_order=SEVERITY_ORDER
        )

        comparison_results[name] = {
            "holdout_test": holdout_metrics,
            "cross_validation": cv_metrics,
        }

    # Evaluate currently saved model if available
    saved_model_metrics = None
    if os.path.exists(saved_model_path):
        saved_model = joblib.load(saved_model_path)
        y_saved_pred = saved_model.predict(X_test)
        saved_model_metrics = compute_multiclass_metrics(y_test, y_saved_pred, class_order=SEVERITY_ORDER)

    # Primary selected model evaluation (Random Forest)
    primary_eval = comparison_results["Random Forest"]["holdout_test"]
    primary_cv = comparison_results["Random Forest"]["cross_validation"]

    dataset_limitation = (
        "Performance is measured on an 18-row synthetic demonstration dataset. "
        "These metrics serve strictly to validate software pipeline mechanics, data ingestion, "
        "and multi-class output schemas. The dataset is statistically insufficient for real-world "
        "predictive validation or operational deployment."
    )

    evaluation_payload = {
        "dataset": {
            "path": data_path,
            "type": "DEMO / PIPELINE VALIDATION DATA",
            "rows": len(df),
            "features": REQUIRED_FEATURES,
            "target": TARGET_COLUMN,
            "classes": SEVERITY_ORDER,
            "class_distribution": val_res["class_distribution"],
            "limitation": dataset_limitation,
        },
        "primary_model": {
            "name": "Random Forest",
            "holdout_metrics": primary_eval,
            "cross_validation": primary_cv,
        },
        "model_comparison": {
            model_name: {
                "accuracy": data["holdout_test"]["accuracy"],
                "macro_f1": data["holdout_test"]["macro_f1"],
                "weighted_f1": data["holdout_test"]["weighted_f1"],
                "high_recall": data["holdout_test"]["high_recall"],
                "critical_recall": data["holdout_test"]["critical_recall"],
                "cv_mean_macro_f1": data["cross_validation"]["mean_macro_f1"],
                "cv_std_macro_f1": data["cross_validation"]["std_macro_f1"],
                "cv_mean_critical_recall": data["cross_validation"]["mean_critical_recall"],
            }
            for model_name, data in comparison_results.items()
        },
        "saved_model_verified": saved_model_metrics is not None,
    }

    if save_results:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_payload, f, indent=4)

    return evaluation_payload


# ==============================================================================
# 4. TERMINAL FORMATTER
# ==============================================================================

def print_evaluation_report(eval_payload: Dict[str, Any]) -> None:
    """
    Renders structured terminal evaluation report.
    """
    ds = eval_payload["dataset"]
    pm = eval_payload["primary_model"]
    hm = pm["holdout_metrics"]
    cv = pm["cross_validation"]

    print("\n" + "=" * 60)
    print("LANDSLIDE ML MODEL EVALUATION")
    print("=" * 60)

    print(f"\nDataset:")
    print(f"{ds['path']} ({ds['type']})")

    print(f"\nRows:")
    print(f"{ds['rows']}")

    print(f"\nClasses:")
    print(" / ".join(ds["classes"]))

    print(f"\nModel:")
    print(f"{pm['name']}")

    print(f"\nAccuracy:")
    print(f"{hm['accuracy']:.4f}")

    print(f"\nMacro Precision:")
    print(f"{hm['macro_precision']:.4f}")

    print(f"\nMacro Recall:")
    print(f"{hm['macro_recall']:.4f}")

    print(f"\nMacro F1:")
    print(f"{hm['macro_f1']:.4f}")

    print(f"\nWeighted F1:")
    print(f"{hm['weighted_f1']:.4f}")

    print(f"\nHigh Recall:")
    print(f"{hm['high_recall']:.4f}")

    print(f"\nCritical Recall:")
    print(f"{hm['critical_recall']:.4f}")

    print("\nConfusion Matrix:")
    print(f"{'Actual':<10} {' | '.join([f'{c:>8}' for c in SEVERITY_ORDER])} (Predicted)")
    print("-" * 52)
    for actual in SEVERITY_ORDER:
        row_str = " | ".join([f"{hm['confusion_matrix'][actual][pred]:>8}" for pred in SEVERITY_ORDER])
        print(f"{actual:<10} {row_str}")

    print(f"\nCross Validation ({cv['n_splits']}-Fold Stratified):")
    for fold in cv["folds"]:
        print(f"  Fold {fold['fold']}: Macro F1 = {fold['macro_f1']:.4f}, Critical Recall = {fold['critical_recall']:.4f}")
    print(f"  Mean Macro F1         : {cv['mean_macro_f1']:.4f} (+/- {cv['std_macro_f1']:.4f})")
    print(f"  Mean Critical Recall  : {cv['mean_critical_recall']:.4f} (+/- {cv['std_critical_recall']:.4f})")
    print(f"  Mean High Recall      : {cv['mean_high_recall']:.4f} (+/- {cv['std_high_recall']:.4f})")

    print("\nModel Comparison Summary:")
    print(f"{'Model':<22} {'Accuracy':<10} {'Macro F1':<10} {'High Rec':<10} {'Crit Rec':<10} {'CV Macro F1'}")
    print("-" * 75)
    for m_name, comp in eval_payload["model_comparison"].items():
        print(
            f"{m_name:<22} "
            f"{comp['accuracy']:<10.4f} "
            f"{comp['macro_f1']:<10.4f} "
            f"{comp['high_recall']:<10.4f} "
            f"{comp['critical_recall']:<10.4f} "
            f"{comp['cv_mean_macro_f1']:.4f} (+/- {comp['cv_std_macro_f1']:.4f})"
        )

    print(f"\nDataset Limitation:")
    print(f"{ds['limitation']}")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    payload = run_evaluation_suite()
    print_evaluation_report(payload)
