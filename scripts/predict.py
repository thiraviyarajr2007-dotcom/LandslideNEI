"""
Production-Ready Inference Engine and Transparent Explainability Layer.

Validates inference payloads against physical sanity constraints, executes
ML risk classification, computes full class probability distributions,
and generates transparent, model-informed contributing factors (reason codes).

NOTE: Contributing factors are human-readable input-condition descriptions,
NOT scientifically validated causal proofs.
"""

from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

# Import canonical schema from shared data_validation and evaluation modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.data_validation import (
    REQUIRED_FEATURES,
    validate_prediction_input,
)
from scripts.evaluate_model import SEVERITY_ORDER

MODEL_PATH: str = "model/landslide_model.pkl"
FEATURE_INFO_PATH: str = "model/feature_info.json"
FEATURE_IMPORTANCE_PATH: str = "model/feature_importance.json"

# Module-level model artifact cache
_CACHED_MODEL: Optional[Any] = None
_CACHED_METADATA: Optional[Dict[str, Any]] = None
_CACHED_IMPORTANCE: Optional[Dict[str, float]] = None


# ==============================================================================
# 1. MODEL ARTIFACT LOADER & VALIDATOR
# ==============================================================================

def load_model_artifacts(
    model_path: str = MODEL_PATH,
    feature_info_path: str = FEATURE_INFO_PATH,
    feature_importance_path: str = FEATURE_IMPORTANCE_PATH,
    force_reload: bool = False,
) -> Tuple[Any, Dict[str, Any], Dict[str, float]]:
    """
    Loads and validates model artifacts from disk with in-memory caching.
    Validates model methods, class alignment, and feature metadata.
    """
    global _CACHED_MODEL, _CACHED_METADATA, _CACHED_IMPORTANCE

    if not force_reload and _CACHED_MODEL is not None and _CACHED_METADATA is not None:
        return _CACHED_MODEL, _CACHED_METADATA, _CACHED_IMPORTANCE or {}

    # 1. Verify model artifact exists
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Trained landslide model artifact not found at '{model_path}'. "
            "Please run 'python scripts/train_model.py' first."
        )

    try:
        model = joblib.load(model_path)
    except Exception as exc:
        raise RuntimeError(f"Corrupted or unreadable model file at '{model_path}': {exc}") from exc

    # Verify model interface
    if not hasattr(model, "predict"):
        raise AttributeError(f"Loaded model from '{model_path}' lacks required 'predict()' method.")
    if not hasattr(model, "predict_proba"):
        raise AttributeError(f"Loaded model from '{model_path}' lacks required 'predict_proba()' method.")
    if not hasattr(model, "classes_"):
        raise AttributeError(f"Loaded model from '{model_path}' lacks required 'classes_' attribute.")

    # 2. Load model metadata
    metadata: Dict[str, Any] = {}
    if os.path.exists(feature_info_path):
        try:
            with open(feature_info_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as exc:
            metadata = {"model_version": "1.0.0", "warning": f"Could not read metadata: {exc}"}
    else:
        metadata = {"model_version": "1.0.0", "warning": "feature_info.json missing"}

    # 3. Load feature importances
    importance_map: Dict[str, float] = {}
    if os.path.exists(feature_importance_path):
        try:
            with open(feature_importance_path, "r", encoding="utf-8") as f:
                imp_payload = json.load(f)
                importance_map = imp_payload.get("features", {})
        except Exception:
            importance_map = {}

    # Fallback to model's own feature_importances_ if json was missing
    if not importance_map and hasattr(model, "feature_importances_"):
        importance_map = {
            feat: round(float(imp), 4)
            for feat, imp in zip(REQUIRED_FEATURES, model.feature_importances_)
        }

    _CACHED_MODEL = model
    _CACHED_METADATA = metadata
    _CACHED_IMPORTANCE = importance_map

    return _CACHED_MODEL, _CACHED_METADATA, _CACHED_IMPORTANCE


# ==============================================================================
# 2. TRANSPARENT EXPLAINABILITY & REASON CODES
# ==============================================================================

# DISCLAIMER:
# These reason codes are demonstration/explainability rules based on current input
# conditions. They are NOT scientifically validated landslide-risk thresholds and
# should NOT be interpreted as causal physical explanations.

REASON_RULES = [
    {
        "code": "very_high_rainfall_24h",
        "feature": "rainfall_24h",
        "condition": lambda v: v["rainfall_24h"] >= 100.0,
        "message": "24-hour rainfall is very high (>=100mm) and is flagged as a model-relevant concern."
    },
    {
        "code": "high_rainfall_24h",
        "feature": "rainfall_24h",
        "condition": lambda v: 50.0 <= v["rainfall_24h"] < 100.0,
        "message": "24-hour rainfall is elevated (50-100mm) and is flagged as a contributing input condition."
    },
    {
        "code": "very_high_rainfall_7d",
        "feature": "rainfall_7d",
        "condition": lambda v: v["rainfall_7d"] >= 500.0,
        "message": "7-day cumulative rainfall is very high (>=500mm) and is flagged as a model-relevant concern."
    },
    {
        "code": "high_rainfall_7d",
        "feature": "rainfall_7d",
        "condition": lambda v: 250.0 <= v["rainfall_7d"] < 500.0,
        "message": "7-day cumulative rainfall is elevated (250-500mm) and is flagged as a contributing input condition."
    },
    {
        "code": "high_rainfall_3d",
        "feature": "rainfall_3d",
        "condition": lambda v: v["rainfall_3d"] >= 200.0,
        "message": "3-day cumulative rainfall is elevated (>=200mm) and is flagged as a contributing input condition."
    },
    {
        "code": "steep_slope",
        "feature": "slope",
        "condition": lambda v: v["slope"] >= 30.0,
        "message": "Terrain slope is steep (>=30°) and is flagged as a model-relevant contributing condition."
    },
    {
        "code": "moderate_slope",
        "feature": "slope",
        "condition": lambda v: 20.0 <= v["slope"] < 30.0,
        "message": "Moderate terrain slope (20°-30°) present in assessment area."
    },
    {
        "code": "historical_landslide_present",
        "feature": "historical_landslide",
        "condition": lambda v: v["historical_landslide"] in (1, 1.0, True),
        "message": "Location has a documented history of prior landslide occurrence."
    },
    {
        "code": "near_historical_landslide",
        "feature": "distance_to_landslide",
        "condition": lambda v: v["distance_to_landslide"] <= 2.0,
        "message": "Close proximity (<=2.0 km) to historical landslide zone is flagged as an elevated concern."
    },
    {
        "code": "high_soil_risk",
        "feature": "soil_risk",
        "condition": lambda v: v["soil_risk"] >= 0.6,
        "message": "Soil susceptibility index is high (>=0.60) and is flagged as a contributing factor."
    },
    {
        "code": "moderate_soil_risk",
        "feature": "soil_risk",
        "condition": lambda v: 0.4 <= v["soil_risk"] < 0.6,
        "message": "Moderate soil susceptibility index (0.40-0.60) present."
    },
    {
        "code": "low_rainfall_stable",
        "feature": "rainfall_24h",
        "condition": lambda v: v["rainfall_24h"] < 30.0 and v["rainfall_7d"] < 100.0,
        "message": "Rainfall levels are low (<30mm 24h, <100mm 7d), within baseline demonstration range."
    },
    {
        "code": "gentle_slope_stable",
        "feature": "slope",
        "condition": lambda v: v["slope"] < 15.0,
        "message": "Gentle slope gradient (<15°) indicates baseline terrain condition."
    },
]


def generate_contributing_factors(
    values: Dict[str, Any],
    global_importance: Dict[str, float],
    max_factors: int = 5
) -> List[Dict[str, Any]]:
    """
    Evaluates input conditions against domain reason rules and orders them
    deterministically by model feature importance.
    """
    triggered: List[Dict[str, Any]] = []

    for rule in REASON_RULES:
        feat = rule["feature"]
        if feat not in values:
            continue

        try:
            if rule["condition"](values):
                val = values[feat]
                imp = global_importance.get(feat, 0.0)
                triggered.append({
                    "code": rule["code"],
                    "feature": feat,
                    "value": val,
                    "importance": imp,
                    "message": rule["message"]
                })
        except Exception:
            continue

    # Deterministic sorting:
    # 1. Global feature importance (descending)
    # 2. Feature name (alphabetical tie-breaker)
    # 3. Rule code (alphabetical secondary tie-breaker)
    sorted_factors = sorted(
        triggered,
        key=lambda x: (-x["importance"], x["feature"], x["code"])
    )

    # Return at most max_factors
    return sorted_factors[:max_factors]


# ==============================================================================
# 3. MAIN PREDICTION FUNCTION
# ==============================================================================

def predict_risk(
    values: Dict[str, Any],
    allow_extra_features: bool = False
) -> Dict[str, Any]:
    """
    Executes full inference lifecycle:
    1. Validates input schema, types, and physical bounds
    2. Loads model and metadata
    3. Builds ordered feature DataFrame
    4. Computes risk classification, probabilities, and confidence
    5. Generates transparent contributing factors
    """
    # 1. Strict input validation
    val_result = validate_prediction_input(values, allow_extra_features=allow_extra_features)
    if not val_result["valid"]:
        error_details = "; ".join([f"{e['field']}: {e['message']}" for e in val_result["errors"]])
        raise ValueError(f"Inference input validation failed: {error_details}")

    # 2. Load model artifacts
    model, metadata, importance_map = load_model_artifacts()

    # 3. Feature Order Safety: build DataFrame in exact canonical order
    row_data = [[float(values[f]) if f != "historical_landslide" else int(values[f]) for f in REQUIRED_FEATURES]]
    row_df = pd.DataFrame(row_data, columns=REQUIRED_FEATURES)

    # 4. Predict risk and class probabilities
    raw_prediction = model.predict(row_df)[0]
    raw_probabilities = model.predict_proba(row_df)[0]

    # Map model classes to probabilities
    model_classes = list(model.classes_)
    prob_by_class = {cls_name: float(prob) for cls_name, prob in zip(model_classes, raw_probabilities)}

    # Ensure all 4 severity classes are present in output dictionary
    complete_probabilities: Dict[str, float] = {}
    for cls_name in SEVERITY_ORDER:
        complete_probabilities[cls_name] = round(prob_by_class.get(cls_name, 0.0), 4)

    # Confidence is defined as the probability assigned to the predicted class
    predicted_confidence = complete_probabilities.get(raw_prediction, 0.0)

    # 5. Generate transparent contributing factors
    contributing_factors = generate_contributing_factors(
        values,
        importance_map,
        max_factors=5
    )

    # 6. Format API-ready response
    response: Dict[str, Any] = {
        "risk": raw_prediction,
        "confidence": round(predicted_confidence, 4),
        "probabilities": complete_probabilities,
        "contributing_factors": contributing_factors,
        "model_version": metadata.get("model_version", "1.2.0"),
        "prediction_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return response


# ==============================================================================
# 4. CLI DEMONSTRATION RUNNER
# ==============================================================================

if __name__ == "__main__":
    low_risk_sample = {
        "rainfall_24h": 20,
        "rainfall_3d": 45,
        "rainfall_7d": 80,
        "slope": 12,
        "elevation": 400,
        "historical_landslide": 0,
        "distance_to_landslide": 8.5,
        "soil_risk": 0.1
    }

    high_risk_sample = {
        "rainfall_24h": 182,
        "rainfall_3d": 420,
        "rainfall_7d": 650,
        "slope": 38,
        "elevation": 850,
        "historical_landslide": 1,
        "distance_to_landslide": 0.8,
        "soil_risk": 0.7
    }

    print("=" * 60)
    print("LANDSLIDE RISK INFERENCE ENGINE")
    print("=" * 60)

    for label, sample in [("LOW-RISK SCENARIO", low_risk_sample), ("HIGH/CRITICAL-RISK SCENARIO", high_risk_sample)]:
        print(f"\n--- Running: {label} ---")
        res = predict_risk(sample)

        print(f"Risk Level           : {res['risk']}")
        print(f"Prediction Confidence: {res['confidence']:.2%}")
        print(f"Model Version        : {res['model_version']}")
        print(f"Timestamp (UTC)      : {res['prediction_timestamp']}")

        print("\nClass Probabilities:")
        for cls_name, prob in res["probabilities"].items():
            print(f"  {cls_name:<10}: {prob:.2%}")

        print(f"\nContributing Factors ({len(res['contributing_factors'])} factors):")
        for factor in res["contributing_factors"]:
            print(f"  * [{factor['code']}] {factor['feature']} = {factor['value']} "
                  f"(Importance: {factor['importance']:.4f}) -> {factor['message']}")

    print("\n" + "=" * 60)