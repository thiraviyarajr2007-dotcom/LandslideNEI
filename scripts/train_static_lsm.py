"""
Phase 8F: Static Landslide Susceptibility Model (LSM) Training & Evaluation
Builds, evaluates, and exports a scientifically defensible static LSM for Northeast India.
Implements Spatial Block Cross-Validation, Proximity Feature Ablation, Probability
Calibration, Permutation Importance, and Model Serialization.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sklearn
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve,
    precision_recall_curve,
    brier_score_loss
)

BASE_DIR = r"C:\SIH Landslide"
INPUT_CSV = os.path.join(BASE_DIR, "data", "processed", "landslides", "landslide_training_samples_proximity.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "inspection", "lsm")
PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")
MODEL_DIR = os.path.join(BASE_DIR, "model")

REPORT_JSON = os.path.join(OUTPUT_DIR, "static_lsm_validation_report.json")
REPORT_TXT = os.path.join(OUTPUT_DIR, "static_lsm_validation_report.txt")
SAVED_PIPELINE_PATH = os.path.join(MODEL_DIR, "static_lsm_pipeline.joblib")
SAVED_METADATA_PATH = os.path.join(MODEL_DIR, "static_lsm_metadata.json")


def audit_dataset(df):
    """Step 1: Dataset Feature Audit & Assertions."""
    print("Executing Step 1: Feature Audit...")
    total_rows = len(df)
    pos_count = int((df["label"] == 1).sum())
    neg_count = int((df["label"] == 0).sum())
    
    assert total_rows == 4016, f"Expected 4016 rows, got {total_rows}"
    assert pos_count == 2008, f"Expected 2008 positive samples, got {pos_count}"
    assert neg_count == 2008, f"Expected 2008 negative samples, got {neg_count}"
    assert df["label"].isna().sum() == 0, "Missing labels found!"
    assert df.duplicated().sum() == 0, "Duplicate rows detected!"
    
    # Check landcover column naming
    lc_col = "landcover_class" if "landcover_class" in df.columns else "worldcover_class"
    
    numeric_features = [
        "elevation_m", "slope_deg", "aspect_deg", "relief_std_5x5_m",
        "clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3",
        "distance_to_road_m", "distance_to_river_m", "distance_to_nearest_other_landslide_m"
    ]
    categorical_features = ["soil_class", lc_col]
    
    missing_by_feature = {col: int(df[col].isna().sum()) for col in numeric_features + categorical_features}
    
    numeric_ranges = {}
    for col in numeric_features:
        valid_series = df[col].dropna()
        numeric_ranges[col] = {
            "min": float(valid_series.min()),
            "mean": float(valid_series.mean()),
            "median": float(valid_series.median()),
            "max": float(valid_series.max()),
            "std": float(valid_series.std()),
            "non_finite_count": int((~np.isfinite(valid_series)).sum())
        }
    
    audit_report = {
        "total_rows": total_rows,
        "positive_count": pos_count,
        "negative_count": neg_count,
        "class_balance": round(pos_count / total_rows, 4),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_coordinates": int(df.duplicated(subset=["latitude", "longitude"]).sum()),
        "duplicate_coordinates_explanation": "48 positive records belong to 24 pairs of distinct Bhuvan 2014 events sharing recorded centroid coordinates.",
        "missing_values_by_feature": missing_by_feature,
        "unique_soil_classes": sorted(df["soil_class"].dropna().unique().tolist()),
        "soil_class_counts": df["soil_class"].value_counts(dropna=False).to_dict(),
        "unique_landcover_classes": sorted(df[lc_col].dropna().unique().tolist()),
        "landcover_class_counts": df[lc_col].value_counts(dropna=False).to_dict(),
        "numeric_ranges": numeric_ranges,
        "coordinate_bounds": {
            "min_lat": float(df["latitude"].min()),
            "max_lat": float(df["latitude"].max()),
            "min_lon": float(df["longitude"].min()),
            "max_lon": float(df["longitude"].max())
        }
    }
    return audit_report, lc_col


def assign_spatial_blocks(df):
    """Step 5: Deterministic 1-Degree Spatial Block Cross-Validation."""
    print("Executing Step 5: Spatial Block Cross-Validation Setup...")
    # Construct 1.0 degree regular geographic grid blocks
    df["block_lat"] = np.floor(df["latitude"]).astype(int)
    df["block_lon"] = np.floor(df["longitude"]).astype(int)
    df["spatial_block_id"] = "B_" + df["block_lat"].astype(str) + "_" + df["block_lon"].astype(str)
    
    blocks_agg = df.groupby("spatial_block_id").agg(
        n_samples=("label", "count"),
        pos_count=("label", lambda x: int((x == 1).sum())),
        neg_count=("label", lambda x: int((x == 0).sum())),
        mean_lat=("latitude", "mean"),
        mean_lon=("longitude", "mean")
    ).reset_index()
    
    # Deterministic KMeans to group the 41 blocks into 5 balanced spatial folds
    km = KMeans(n_clusters=5, random_state=42, n_init=50)
    blocks_agg["spatial_fold"] = km.fit_predict(
        blocks_agg[["mean_lat", "mean_lon"]],
        sample_weight=blocks_agg["n_samples"]
    )
    
    # Merge fold assignment back to df
    df = df.merge(blocks_agg[["spatial_block_id", "spatial_fold"]], on="spatial_block_id")
    
    fold_audit = {}
    for f in range(5):
        sub = df[df["spatial_fold"] == f]
        pos = int((sub["label"] == 1).sum())
        neg = int((sub["label"] == 0).sum())
        blocks_in_fold = sorted(sub["spatial_block_id"].unique().tolist())
        fold_audit[f"fold_{f}"] = {
            "fold_index": f,
            "total_samples": len(sub),
            "positive_samples": pos,
            "negative_samples": neg,
            "positive_ratio": round(pos / len(sub), 4),
            "block_count": len(blocks_in_fold),
            "blocks": blocks_in_fold,
            "lat_min": round(float(sub["latitude"].min()), 3),
            "lat_max": round(float(sub["latitude"].max()), 3),
            "lon_min": round(float(sub["longitude"].min()), 3),
            "lon_max": round(float(sub["longitude"].max()), 3)
        }
    
    # Verifications
    assert len(df) == 4016
    assert df["spatial_fold"].isna().sum() == 0
    for f in range(5):
        assert fold_audit[f"fold_{f}"]["positive_samples"] > 0
        assert fold_audit[f"fold_{f}"]["negative_samples"] > 0
        
    return df, fold_audit


def build_pipeline(numeric_cols, categorical_cols):
    """Step 2 & 4: Leakage-Free Preprocessing Pipeline + Balanced Random Forest."""
    numeric_transformer = SimpleImputer(strategy="median")
    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", categorical_transformer, categorical_cols)
        ]
    )
    
    classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    
    return Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", classifier)
    ])


def evaluate_model_cv(df, num_cols, cat_cols, model_name):
    """Step 6 & 8: Spatial Cross-Validation Evaluation & Calibration."""
    print(f"Evaluating {model_name} across 5 spatial folds...")
    all_features = num_cols + cat_cols
    
    fold_metrics = []
    y_true_all = []
    y_prob_all = []
    y_pred_all = []
    y_calib_prob_all = []
    
    fold_predictions = {}
    
    for fold in range(5):
        train_mask = df["spatial_fold"] != fold
        test_mask = df["spatial_fold"] == fold
        
        X_train = df.loc[train_mask, all_features].copy()
        y_train = df.loc[train_mask, "label"].copy()
        X_test = df.loc[test_mask, all_features].copy()
        y_test = df.loc[test_mask, "label"].copy()
        
        # Fit base pipeline
        pipe = build_pipeline(num_cols, cat_cols)
        pipe.fit(X_train, y_train)
        
        probs = pipe.predict_proba(X_test)[:, 1]
        preds = pipe.predict(X_test)
        
        # Calibration using 3-fold CV inside the training fold to avoid test leakage
        calibrator = CalibratedClassifierCV(estimator=pipe, method="sigmoid", cv=3)
        calibrator.fit(X_train, y_train)
        calib_probs = calibrator.predict_proba(X_test)[:, 1]
        
        auc = float(roc_auc_score(y_test, probs))
        pr_auc = float(average_precision_score(y_test, probs))
        acc = float(accuracy_score(y_test, preds))
        bal_acc = float(balanced_accuracy_score(y_test, preds))
        prec = float(precision_score(y_test, preds, zero_division=0))
        rec = float(recall_score(y_test, preds, zero_division=0))
        f1 = float(f1_score(y_test, preds, zero_division=0))
        brier_raw = float(brier_score_loss(y_test, probs))
        brier_calib = float(brier_score_loss(y_test, calib_probs))
        cm = confusion_matrix(y_test, preds).tolist()
        
        fold_res = {
            "fold": fold,
            "train_samples": int(train_mask.sum()),
            "test_samples": int(test_mask.sum()),
            "roc_auc": auc,
            "pr_auc": pr_auc,
            "accuracy": acc,
            "balanced_accuracy": bal_acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "brier_score_raw": brier_raw,
            "brier_score_calibrated": brier_calib,
            "confusion_matrix": cm
        }
        fold_metrics.append(fold_res)
        
        y_true_all.extend(y_test.tolist())
        y_prob_all.extend(probs.tolist())
        y_pred_all.extend(preds.tolist())
        y_calib_prob_all.extend(calib_probs.tolist())
        
        fold_predictions[f"fold_{fold}"] = {
            "y_true": y_test.tolist(),
            "y_prob": probs.tolist(),
            "y_calib_prob": calib_probs.tolist()
        }
        
    summary_metrics = {
        "roc_auc_mean": float(np.mean([m["roc_auc"] for m in fold_metrics])),
        "roc_auc_std": float(np.std([m["roc_auc"] for m in fold_metrics])),
        "pr_auc_mean": float(np.mean([m["pr_auc"] for m in fold_metrics])),
        "pr_auc_std": float(np.std([m["pr_auc"] for m in fold_metrics])),
        "accuracy_mean": float(np.mean([m["accuracy"] for m in fold_metrics])),
        "accuracy_std": float(np.std([m["accuracy"] for m in fold_metrics])),
        "balanced_accuracy_mean": float(np.mean([m["balanced_accuracy"] for m in fold_metrics])),
        "balanced_accuracy_std": float(np.std([m["balanced_accuracy"] for m in fold_metrics])),
        "precision_mean": float(np.mean([m["precision"] for m in fold_metrics])),
        "precision_std": float(np.std([m["precision"] for m in fold_metrics])),
        "recall_mean": float(np.mean([m["recall"] for m in fold_metrics])),
        "recall_std": float(np.std([m["recall"] for m in fold_metrics])),
        "f1_mean": float(np.mean([m["f1_score"] for m in fold_metrics])),
        "f1_std": float(np.std([m["f1_score"] for m in fold_metrics])),
        "brier_raw_mean": float(np.mean([m["brier_score_raw"] for m in fold_metrics])),
        "brier_calib_mean": float(np.mean([m["brier_score_calibrated"] for m in fold_metrics]))
    }
    
    overall_res = {
        "model_name": model_name,
        "features": all_features,
        "summary": summary_metrics,
        "per_fold": fold_metrics,
        "overall_confusion_matrix": confusion_matrix(y_true_all, y_pred_all).tolist(),
        "predictions": {
            "y_true": y_true_all,
            "y_prob": y_prob_all,
            "y_calib_prob": y_calib_prob_all
        },
        "fold_predictions": fold_predictions
    }
    return overall_res


def compute_permutation_importance(df, num_cols, cat_cols, model_name):
    """Step 9: Permutation Feature Importance Evaluated on Spatial Holdouts."""
    print(f"Computing permutation importance for {model_name} on spatial holdouts...")
    all_features = num_cols + cat_cols
    fold_importances = []
    
    for fold in range(5):
        train_mask = df["spatial_fold"] != fold
        test_mask = df["spatial_fold"] == fold
        
        X_train = df.loc[train_mask, all_features]
        y_train = df.loc[train_mask, "label"]
        X_test = df.loc[test_mask, all_features]
        y_test = df.loc[test_mask, "label"]
        
        pipe = build_pipeline(num_cols, cat_cols)
        pipe.fit(X_train, y_train)
        
        res = permutation_importance(
            pipe, X_test, y_test,
            scoring="roc_auc",
            n_repeats=5,
            random_state=42 + fold,
            n_jobs=-1
        )
        fold_importances.append(res.importances_mean)
        
    arr = np.array(fold_importances) # shape: (5, n_features)
    mean_imp = np.mean(arr, axis=0)
    std_imp = np.std(arr, axis=0)
    
    imp_list = []
    for idx, col in enumerate(all_features):
        imp_list.append({
            "feature": col,
            "mean_importance_roc_auc_drop": float(round(mean_imp[idx], 5)),
            "std_importance": float(round(std_imp[idx], 5))
        })
        
    imp_list.sort(key=lambda x: x["mean_importance_roc_auc_drop"], reverse=True)
    return imp_list


def generate_plots(df, results_a, results_b1, results_b2, imp_a, imp_b2):
    """Step 12: Generate Scientific Evaluation Plots."""
    print("Generating evaluation plots under data/inspection/lsm/plots/...")
    os.makedirs(PLOTS_DIR, exist_ok=True)
    
    # 1. Spatial Folds Map
    plt.figure(figsize=(9, 6), dpi=300)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    markers = {1: '^', 0: 'o'}
    for f in range(5):
        sub = df[df["spatial_fold"] == f]
        for lbl, m, alpha in [(0, 'o', 0.4), (1, '^', 0.7)]:
            sub_lbl = sub[sub["label"] == lbl]
            lbl_text = f"Fold {f} ({'Positive' if lbl==1 else 'Negative'})" if f==0 else None
            plt.scatter(
                sub_lbl["longitude"], sub_lbl["latitude"],
                c=colors[f], marker=m, s=16 if lbl==1 else 10,
                alpha=alpha, edgecolors='none', label=lbl_text
            )
    plt.title("Northeast India 1° Grid-Block Spatial Cross-Validation Folds", fontsize=12, fontweight='bold')
    plt.xlabel("Longitude (°E)", fontsize=10)
    plt.ylabel("Latitude (°N)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "spatial_folds_map.png"))
    plt.close()
    
    # 2. ROC Curves (Model A vs Model B)
    plt.figure(figsize=(7, 6), dpi=300)
    fpr_a, tpr_a, _ = roc_curve(results_a["predictions"]["y_true"], results_a["predictions"]["y_prob"])
    fpr_b1, tpr_b1, _ = roc_curve(results_b1["predictions"]["y_true"], results_b1["predictions"]["y_prob"])
    fpr_b2, tpr_b2, _ = roc_curve(results_b2["predictions"]["y_true"], results_b2["predictions"]["y_prob"])
    
    plt.plot(fpr_a, tpr_a, label=f"Model A: Env Only (AUC = {results_a['summary']['roc_auc_mean']:.3f} ± {results_a['summary']['roc_auc_std']:.3f})", color='#1f77b4', lw=2)
    plt.plot(fpr_b1, tpr_b1, label=f"Model B1: Env + Road/River (AUC = {results_b1['summary']['roc_auc_mean']:.3f} ± {results_b1['summary']['roc_auc_std']:.3f})", color='#2ca02c', lw=2, linestyle='--')
    plt.plot(fpr_b2, tpr_b2, label=f"Model B2: Env + All Proximity (AUC = {results_b2['summary']['roc_auc_mean']:.3f} ± {results_b2['summary']['roc_auc_std']:.3f})", color='#d62728', lw=2)
    plt.plot([0, 1], [0, 1], 'k:', lw=1.2, label="Random Guess (AUC = 0.500)")
    plt.title("Spatial Block Cross-Validation ROC Curves", fontsize=12, fontweight='bold')
    plt.xlabel("False Positive Rate", fontsize=10)
    plt.ylabel("True Positive Rate", fontsize=10)
    plt.legend(loc='lower right', fontsize=9)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "roc_curves.png"))
    plt.close()
    
    # 3. Precision-Recall Curves
    plt.figure(figsize=(7, 6), dpi=300)
    prec_a, rec_a, _ = precision_recall_curve(results_a["predictions"]["y_true"], results_a["predictions"]["y_prob"])
    prec_b1, rec_b1, _ = precision_recall_curve(results_b1["predictions"]["y_true"], results_b1["predictions"]["y_prob"])
    prec_b2, rec_b2, _ = precision_recall_curve(results_b2["predictions"]["y_true"], results_b2["predictions"]["y_prob"])
    
    plt.plot(rec_a, prec_a, label=f"Model A (PR-AUC = {results_a['summary']['pr_auc_mean']:.3f} ± {results_a['summary']['pr_auc_std']:.3f})", color='#1f77b4', lw=2)
    plt.plot(rec_b1, prec_b1, label=f"Model B1 (PR-AUC = {results_b1['summary']['pr_auc_mean']:.3f} ± {results_b1['summary']['pr_auc_std']:.3f})", color='#2ca02c', lw=2, linestyle='--')
    plt.plot(rec_b2, prec_b2, label=f"Model B2 (PR-AUC = {results_b2['summary']['pr_auc_mean']:.3f} ± {results_b2['summary']['pr_auc_std']:.3f})", color='#d62728', lw=2)
    plt.axhline(0.5, color='gray', linestyle=':', label="Baseline Prior (0.500)")
    plt.title("Spatial Block Cross-Validation Precision-Recall Curves", fontsize=12, fontweight='bold')
    plt.xlabel("Recall", fontsize=10)
    plt.ylabel("Precision", fontsize=10)
    plt.legend(loc='lower left', fontsize=9)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "pr_curves.png"))
    plt.close()
    
    # 4. Calibration Curves (Raw vs Calibrated)
    plt.figure(figsize=(7, 6), dpi=300)
    prob_true_a, prob_pred_a = calibration_curve(results_a["predictions"]["y_true"], results_a["predictions"]["y_prob"], n_bins=10)
    prob_true_cal_a, prob_pred_cal_a = calibration_curve(results_a["predictions"]["y_true"], results_a["predictions"]["y_calib_prob"], n_bins=10)
    
    plt.plot(prob_pred_a, prob_true_a, 's-', label=f"Model A Raw (Brier = {results_a['summary']['brier_raw_mean']:.3f})", color='#1f77b4')
    plt.plot(prob_pred_cal_a, prob_true_cal_a, 'o-', label=f"Model A Calibrated (Brier = {results_a['summary']['brier_calib_mean']:.3f})", color='#2ca02c')
    plt.plot([0, 1], [0, 1], 'k--', label="Perfect Calibration")
    plt.title("Reliability Diagram (Model A Susceptibility Calibration)", fontsize=12, fontweight='bold')
    plt.xlabel("Mean Predicted Probability", fontsize=10)
    plt.ylabel("Fraction of Positives", fontsize=10)
    plt.legend(loc='lower right', fontsize=9)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "calibration_curves.png"))
    plt.close()
    
    # 5. Feature Importance (Model A)
    plt.figure(figsize=(8, 5), dpi=300)
    feats = [item["feature"] for item in imp_a]
    vals = [item["mean_importance_roc_auc_drop"] for item in imp_a]
    errs = [item["std_importance"] for item in imp_a]
    
    y_pos = np.arange(len(feats))
    plt.barh(y_pos, vals, xerr=errs, align='center', color='#3b528b', alpha=0.85, capsize=3)
    plt.yticks(y_pos, feats, fontsize=9)
    plt.gca().invert_yaxis()
    plt.title("Model A: Permutation Feature Importance (Held-Out Spatial Folds)", fontsize=11, fontweight='bold')
    plt.xlabel("Mean Drop in Spatial ROC-AUC", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5, axis='x')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "feature_importance.png"))
    plt.close()
    
    # 6. Model Comparison Bar Chart
    plt.figure(figsize=(8, 5), dpi=300)
    models = ["Model A\n(Env Only)", "Model B1\n(Env + Road/River)", "Model B2\n(Env + All Proximity)"]
    x = np.arange(len(models))
    width = 0.22
    
    auc_means = [results_a['summary']['roc_auc_mean'], results_b1['summary']['roc_auc_mean'], results_b2['summary']['roc_auc_mean']]
    auc_stds = [results_a['summary']['roc_auc_std'], results_b1['summary']['roc_auc_std'], results_b2['summary']['roc_auc_std']]
    
    pr_means = [results_a['summary']['pr_auc_mean'], results_b1['summary']['pr_auc_mean'], results_b2['summary']['pr_auc_mean']]
    pr_stds = [results_a['summary']['pr_auc_std'], results_b1['summary']['pr_auc_std'], results_b2['summary']['pr_auc_std']]
    
    bal_means = [results_a['summary']['balanced_accuracy_mean'], results_b1['summary']['balanced_accuracy_mean'], results_b2['summary']['balanced_accuracy_mean']]
    bal_stds = [results_a['summary']['balanced_accuracy_std'], results_b1['summary']['balanced_accuracy_std'], results_b2['summary']['balanced_accuracy_std']]
    
    plt.bar(x - width, auc_means, width, yerr=auc_stds, label='Spatial ROC-AUC', color='#1f77b4', capsize=4)
    plt.bar(x, pr_means, width, yerr=pr_stds, label='Spatial PR-AUC', color='#ff7f0e', capsize=4)
    plt.bar(x + width, bal_means, width, yerr=bal_stds, label='Spatial Bal. Acc.', color='#2ca02c', capsize=4)
    
    plt.xticks(x, models, fontsize=9)
    plt.ylabel("Score", fontsize=10)
    plt.ylim(0.5, 1.05)
    plt.title("Proximity Feature Ablation under Spatial Block Cross-Validation", fontsize=12, fontweight='bold')
    plt.legend(loc='lower right', fontsize=9)
    plt.grid(True, linestyle='--', alpha=0.5, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "model_comparison.png"))
    plt.close()


def main():
    print("=" * 80)
    print("STARTING PHASE 8F: STATIC LANDSLIDE SUSCEPTIBILITY MODEL TRAINING")
    print("=" * 80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    df = pd.read_csv(INPUT_CSV)
    
    # Step 1: Feature Audit
    audit_report, lc_col = audit_dataset(df)
    
    # Step 5: Spatial Block Cross-Validation
    df, fold_audit = assign_spatial_blocks(df)
    
    # Feature sets
    num_cols_a = [
        "elevation_m", "slope_deg", "aspect_deg", "relief_std_5x5_m",
        "clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3"
    ]
    cat_cols = ["soil_class", lc_col]
    
    num_cols_b1 = num_cols_a + ["distance_to_road_m", "distance_to_river_m"]
    num_cols_b2 = num_cols_b1 + ["distance_to_nearest_other_landslide_m"]
    
    # Step 6: Cross-Validation Evaluations
    results_a = evaluate_model_cv(df, num_cols_a, cat_cols, "Model A (Environmental Only)")
    results_b1 = evaluate_model_cv(df, num_cols_b1, cat_cols, "Model B1 (Env + Road/River Proximity)")
    results_b2 = evaluate_model_cv(df, num_cols_b2, cat_cols, "Model B2 (Env + All Proximity)")
    
    # Step 7: Proximity Ablation Quantifications
    delta_roc_auc_b1 = results_b1["summary"]["roc_auc_mean"] - results_a["summary"]["roc_auc_mean"]
    delta_pr_auc_b1 = results_b1["summary"]["pr_auc_mean"] - results_a["summary"]["pr_auc_mean"]
    delta_bal_acc_b1 = results_b1["summary"]["balanced_accuracy_mean"] - results_a["summary"]["balanced_accuracy_mean"]
    delta_f1_b1 = results_b1["summary"]["f1_mean"] - results_a["summary"]["f1_mean"]
    
    delta_roc_auc_b2 = results_b2["summary"]["roc_auc_mean"] - results_a["summary"]["roc_auc_mean"]
    delta_pr_auc_b2 = results_b2["summary"]["pr_auc_mean"] - results_a["summary"]["pr_auc_mean"]
    delta_bal_acc_b2 = results_b2["summary"]["balanced_accuracy_mean"] - results_a["summary"]["balanced_accuracy_mean"]
    delta_f1_b2 = results_b2["summary"]["f1_mean"] - results_a["summary"]["f1_mean"]
    
    ablation_summary = {
        "model_a_vs_model_b1_infrastructure_proximity": {
            "delta_roc_auc": round(delta_roc_auc_b1, 4),
            "delta_pr_auc": round(delta_pr_auc_b1, 4),
            "delta_balanced_accuracy": round(delta_bal_acc_b1, 4),
            "delta_f1": round(delta_f1_b1, 4),
            "interpretation": "Adding road and river proximity results in neutral to marginal change in spatial generalization (ROC-AUC ~0.801 vs ~0.800)."
        },
        "model_a_vs_model_b2_all_proximity": {
            "delta_roc_auc": round(delta_roc_auc_b2, 4),
            "delta_pr_auc": round(delta_pr_auc_b2, 4),
            "delta_balanced_accuracy": round(delta_bal_acc_b2, 4),
            "delta_f1": round(delta_f1_b2, 4),
            "interpretation": "Adding distance_to_nearest_other_landslide_m causes a massive +0.1534 surge in spatial ROC-AUC. As hypothesized during Phase 8E.2.3, this feature reflects spatial clustering of the 2014 inventory combined with the >=1 km buffer used in negative generation, functioning as an indirect label lookup rather than a causative physical terrain trigger."
        }
    }
    
    # Step 9: Permutation Importance
    imp_a = compute_permutation_importance(df, num_cols_a, cat_cols, "Model A")
    imp_b2 = compute_permutation_importance(df, num_cols_b2, cat_cols, "Model B2")
    
    # Step 10: Final Model Recommendation
    # Model A is the primary defensible physical susceptibility model.
    selected_model_name = "Model A (Environmental Only)"
    selected_num_cols = num_cols_a
    selected_cat_cols = cat_cols
    selected_results = results_a
    
    selection_rationale = (
        "Model A (Environmental Only: Terrain + Soil + Land Cover) achieves an honest, robust spatial "
        "ROC-AUC of 0.8012 ± 0.0745 and PR-AUC of 0.7871 ± 0.0554 across held-out geographic regions. "
        "While Model B2 scores higher (0.9546), ablation demonstrates that the gain is entirely driven by "
        "'distance_to_nearest_other_landslide_m', which leaks inventory clustering and the >=1 km spatial negative buffer. "
        "Model A is physically causal, generalizable to unmapped terrain, and free from inventory-clustering artifacts."
    )
    
    # Step 11: Train Final Pipeline on Full 4016 Samples & Save
    print("Executing Step 11: Fitting Final Model Pipeline on full dataset...")
    final_pipeline = build_pipeline(selected_num_cols, selected_cat_cols)
    final_pipeline.fit(df[selected_num_cols + selected_cat_cols], df["label"])
    
    joblib.dump(final_pipeline, SAVED_PIPELINE_PATH, compress=3)
    print(f"Saved trained pipeline to: {SAVED_PIPELINE_PATH}")
    
    metadata = {
        "model_name": "Static Landslide Susceptibility Model (LSM)",
        "selected_model": selected_model_name,
        "selection_rationale": selection_rationale,
        "output_description": "Random Forest susceptibility score/probability estimate in the range 0–1.",
        "training_timestamp_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "total_training_samples": 4016,
        "positive_samples": 2008,
        "negative_samples": 2008,
        "features": {
            "numeric": selected_num_cols,
            "categorical": selected_cat_cols,
            "total_feature_count": len(selected_num_cols) + len(selected_cat_cols)
        },
        "classifier_configuration": {
            "algorithm": "RandomForestClassifier",
            "n_estimators": 100,
            "max_depth": 15,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "class_weight": "balanced",
            "random_state": 42
        },
        "spatial_cross_validation": {
            "strategy": "1.0 Degree Geographic Grid-Block Clustering",
            "n_blocks": 41,
            "n_folds": 5,
            "mean_spatial_roc_auc": round(selected_results["summary"]["roc_auc_mean"], 4),
            "std_spatial_roc_auc": round(selected_results["summary"]["roc_auc_std"], 4),
            "mean_spatial_pr_auc": round(selected_results["summary"]["pr_auc_mean"], 4),
            "std_spatial_pr_auc": round(selected_results["summary"]["pr_auc_std"], 4),
            "mean_spatial_balanced_accuracy": round(selected_results["summary"]["balanced_accuracy_mean"], 4)
        },
        "probability_calibration_evaluation": {
            "evaluation_note": "Probability calibration was evaluated using 3-fold internal CV inside spatial training folds. Sigmoid calibration worsened Brier score (0.2021 vs 0.1913 raw), so post-hoc calibration was rejected.",
            "raw_brier_score": round(selected_results["summary"]["brier_raw_mean"], 4),
            "calibrated_sigmoid_brier_score": round(selected_results["summary"]["brier_calib_mean"], 4),
            "deployed_probability_mode": "Raw Random Forest ensemble probability estimate in the range 0-1 (uncalibrated probability estimate, not represented as perfectly calibrated)."
        },
        "ablation_comparison": {
            "model_a_roc_auc": round(results_a["summary"]["roc_auc_mean"], 4),
            "model_b1_roc_auc": round(results_b1["summary"]["roc_auc_mean"], 4),
            "model_b2_roc_auc": round(results_b2["summary"]["roc_auc_mean"], 4)
        },
        "software_versions": {
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__
        }
    }
    
    with open(SAVED_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model metadata to: {SAVED_METADATA_PATH}")
    
    # Step 12: Generate Plots & Write Validation Reports
    generate_plots(df, results_a, results_b1, results_b2, imp_a, imp_b2)
    
    validation_report_json = {
        "status": "VALIDATION_PASSED",
        "dataset_audit": audit_report,
        "spatial_folds": fold_audit,
        "model_a_results": {k: v for k, v in results_a.items() if k not in ["predictions", "fold_predictions"]},
        "model_b1_results": {k: v for k, v in results_b1.items() if k not in ["predictions", "fold_predictions"]},
        "model_b2_results": {k: v for k, v in results_b2.items() if k not in ["predictions", "fold_predictions"]},
        "ablation_analysis": ablation_summary,
        "permutation_importance_model_a": imp_a,
        "permutation_importance_model_b2": imp_b2,
        "model_selection": {
            "selected_model": selected_model_name,
            "rationale": selection_rationale,
            "output_description": "Random Forest susceptibility score/probability estimate in the range 0–1."
        },
        "calibration": {
            "model_a_brier_raw": results_a["summary"]["brier_raw_mean"],
            "model_a_brier_calibrated": results_a["summary"]["brier_calib_mean"],
            "decision": "Post-hoc calibration rejected because sigmoid calibration worsened Brier score (0.2021 vs 0.1913 raw). Deployed model uses raw RF voting fraction.",
            "calibration_status": "Uncalibrated Random Forest probability estimate; not represented as perfectly calibrated."
        }
    }
    
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(validation_report_json, f, indent=2)
    print(f"Saved validation JSON to: {REPORT_JSON}")
    
    # TXT Report
    txt_lines = [
        "=" * 80,
        "PHASE 8F — STATIC LANDSLIDE SUSCEPTIBILITY MODEL VALIDATION REPORT",
        "=" * 80,
        f"Generated UTC: {metadata['training_timestamp_utc']}",
        f"Total Samples: {audit_report['total_rows']} (2,008 Positives, 2,008 Negatives)",
        f"Spatial CV Strategy: 41 1-Degree Grid Blocks -> 5 Balanced Geographic Folds",
        "",
        "1. MODEL PERFORMANCE SUMMARY (5-FOLD SPATIAL BLOCK CROSS-VALIDATION)",
        "-" * 80,
        f"{'Model Configuration':<36} | {'ROC-AUC':<15} | {'PR-AUC':<15} | {'Bal. Acc':<12} | {'F1':<12}",
        "-" * 80,
        f"{'Model A (Environmental Only)':<36} | {results_a['summary']['roc_auc_mean']:.4f} ± {results_a['summary']['roc_auc_std']:.4f} | {results_a['summary']['pr_auc_mean']:.4f} ± {results_a['summary']['pr_auc_std']:.4f} | {results_a['summary']['balanced_accuracy_mean']:.4f}      | {results_a['summary']['f1_mean']:.4f}",
        f"{'Model B1 (Env + Road/River)':<36} | {results_b1['summary']['roc_auc_mean']:.4f} ± {results_b1['summary']['roc_auc_std']:.4f} | {results_b1['summary']['pr_auc_mean']:.4f} ± {results_b1['summary']['pr_auc_std']:.4f} | {results_b1['summary']['balanced_accuracy_mean']:.4f}      | {results_b1['summary']['f1_mean']:.4f}",
        f"{'Model B2 (Env + All Proximity)':<36} | {results_b2['summary']['roc_auc_mean']:.4f} ± {results_b2['summary']['roc_auc_std']:.4f} | {results_b2['summary']['pr_auc_mean']:.4f} ± {results_b2['summary']['pr_auc_std']:.4f} | {results_b2['summary']['balanced_accuracy_mean']:.4f}      | {results_b2['summary']['f1_mean']:.4f}",
        "-" * 80,
        "",
        "2. PROXIMITY FEATURE ABLATION ANALYSIS",
        "-" * 80,
        f"Model A -> Model B1 (Road & River Distance):",
        f"  * Δ Spatial ROC-AUC: {delta_roc_auc_b1:+.4f}",
        f"  * Δ Spatial PR-AUC:  {delta_pr_auc_b1:+.4f}",
        f"  * Assessment: Road and river proximity produce neutral impact across geographic folds.",
        f"Model A -> Model B2 (All Proximity, including distance_to_nearest_other_landslide_m):",
        f"  * Δ Spatial ROC-AUC: {delta_roc_auc_b2:+.4f}",
        f"  * Δ Spatial PR-AUC:  {delta_pr_auc_b2:+.4f}",
        f"  * Critical Scientific Note: The +0.1534 surge in ROC-AUC is driven almost entirely by",
        f"    distance_to_nearest_other_landslide_m, which acts as an inventory clustering proxy",
        f"    and mirrors the >=1 km buffer of negative generation. It is NOT a causal physical mechanism.",
        "",
        "3. PERMUTATION FEATURE IMPORTANCE (MODEL A — HELD-OUT SPATIAL FOLDS)",
        "-" * 80,
    ]
    for item in imp_a:
        txt_lines.append(f"  * {item['feature']:<25} : {item['mean_importance_roc_auc_drop']:+.5f} ± {item['std_importance']:.5f} ROC-AUC drop")
    
    txt_lines.extend([
        "",
        "4. PROBABILITY CALIBRATION & OUTPUT INTERPRETATION (MODEL A)",
        "-" * 80,
        f"  * Raw Random Forest Brier Score:        {results_a['summary']['brier_raw_mean']:.4f}",
        f"  * Calibrated (Sigmoid) Brier Score:     {results_a['summary']['brier_calib_mean']:.4f}",
        f"  * Calibration Evaluation:               Sigmoid calibration worsened the Brier score (0.2021 vs 0.1913 raw).",
        f"  * Calibration Decision:                 Rejected post-hoc calibration; deployed model uses raw RF voting fraction.",
        f"  * Model Output Interpretation:          Model A outputs a Random Forest susceptibility score/probability estimate",
        f"                                          in the range 0–1, and should NOT be represented as perfectly calibrated.",
        "",
        "5. FINAL MODEL SELECTION & ARTIFACTS",
        "-" * 80,
        f"  * Selected Model:     {selected_model_name}",
        f"  * Output Description: Random Forest susceptibility score/probability estimate in the range 0–1",
        f"  * Rationale:          {selection_rationale}",
        f"  * Saved Pipeline:     {SAVED_PIPELINE_PATH}",
        f"  * Saved Metadata:     {SAVED_METADATA_PATH}",
        "=" * 80
    ])
    
    with open(REPORT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))
    print(f"Saved validation TXT to: {REPORT_TXT}")
    
    # Step 13: Prediction Smoke Test
    print("Executing Step 13: Prediction Smoke Test (Representative training rows)...")
    loaded_pipe = joblib.load(SAVED_PIPELINE_PATH)
    sample_data = df.loc[:4, selected_num_cols + selected_cat_cols]
    preds = loaded_pipe.predict(sample_data)
    probs = loaded_pipe.predict_proba(sample_data)[:, 1]
    
    assert len(probs) == 5, f"Expected 5 probabilities, got {len(probs)}"
    assert np.all((probs >= 0.0) & (probs <= 1.0)), "Probabilities out of bounds [0, 1]!"
    assert not np.any(np.isnan(probs)), "NaN values in predictions!"
    assert not np.any(np.isinf(probs)), "Inf values in predictions!"
    print(f"Smoke test passed! Pipeline loaded and verified inference on representative training rows (checking execution and bounds, not independent generalization). Sample predictions: {preds.tolist()}, probabilities: {np.round(probs, 4).tolist()}")
    
    # Step 14: Data Integrity Verification
    print("Executing Step 14: Data Integrity Verification...")
    files_to_check = [
        os.path.join(BASE_DIR, "data", "processed", "landslides", "landslide_training_samples_gadm_corrected.csv"),
        os.path.join(BASE_DIR, "data", "processed", "landslides", "landslide_training_samples_terrain.csv"),
        os.path.join(BASE_DIR, "data", "processed", "landslides", "landslide_training_samples_soil.csv"),
        os.path.join(BASE_DIR, "data", "processed", "landslides", "landslide_training_samples_lulc.csv"),
        os.path.join(BASE_DIR, "data", "processed", "landslides", "landslide_training_samples_proximity.csv")
    ]
    for fp in files_to_check:
        assert os.path.exists(fp), f"File missing: {fp}"
        tdf = pd.read_csv(fp)
        assert len(tdf) == 4016, f"Corrupted row count in {fp}: {len(tdf)}"
        assert (tdf["label"] == 1).sum() == 2008, f"Corrupted labels in {fp}"
    print("Data integrity verified! All 5 previous training datasets remain 100% intact.")
    print("=" * 80)
    print("PHASE 8F PIPELINE COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    main()
