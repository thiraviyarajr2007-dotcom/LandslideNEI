"""
Data Validation Module for Landslide Risk Assessment.

Centralizes data-quality, schema verification, and input-sanity limits
for both training datasets and real-time inference payloads.

NOTE: All boundaries defined herein represent physical/sanity bounds,
NOT landslide-risk decision thresholds.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

# ==============================================================================
# 1. CENTRALIZED FEATURE SPECIFICATIONS & PHYSICAL SANITY LIMITS
# ==============================================================================

FEATURE_CONFIG: Dict[str, Dict[str, Any]] = {
    "rainfall_24h": {
        "type": (int, float, np.integer, np.floating),
        "min": 0.0,
        "max": 2500.0,  # Extreme world-record rainfall ceiling for input sanity
        "description": "24-hour cumulative rainfall in mm"
    },
    "rainfall_3d": {
        "type": (int, float, np.integer, np.floating),
        "min": 0.0,
        "max": 5000.0,
        "description": "3-day cumulative rainfall in mm"
    },
    "rainfall_7d": {
        "type": (int, float, np.integer, np.floating),
        "min": 0.0,
        "max": 10000.0,
        "description": "7-day cumulative rainfall in mm"
    },
    "slope": {
        "type": (int, float, np.integer, np.floating),
        "min": 0.0,
        "max": 90.0,
        "description": "Slope angle in degrees (0 to 90)"
    },
    "elevation": {
        "type": (int, float, np.integer, np.floating),
        "min": -500.0,
        "max": 9000.0,
        "description": "Elevation in metres above sea level (-500m to 9000m)"
    },
    "historical_landslide": {
        "type": (int, float, bool, np.integer, np.floating, np.bool_),
        "allowed_values": {0, 1, 0.0, 1.0, True, False},
        "description": "Binary indicator of past landslide event (0 or 1)"
    },
    "distance_to_landslide": {
        "type": (int, float, np.integer, np.floating),
        "min": 0.0,
        "max": 50000.0,
        "description": "Distance to nearest historical landslide in km"
    },
    "soil_risk": {
        "type": (int, float, np.integer, np.floating),
        "min": 0.0,
        "max": 1.0,
        "description": "Soil susceptibility index (0.0 to 1.0)"
    }
}

REQUIRED_FEATURES: List[str] = list(FEATURE_CONFIG.keys())
TARGET_COLUMN: str = "risk"
ALLOWED_TARGET_CLASSES: List[str] = ["Critical", "High", "Low", "Watch"]


# ==============================================================================
# 2. FEATURE VALUE VALIDATION (SHARED)
# ==============================================================================

def validate_feature_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates individual feature values against physical sanity bounds.
    """
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    for field, value in data.items():
        if field not in FEATURE_CONFIG:
            continue

        config = FEATURE_CONFIG[field]

        # Null / None / NaN check
        if value is None:
            errors.append({
                "field": field,
                "message": f"Field '{field}' cannot be null/None"
            })
            continue

        if isinstance(value, (float, np.floating)) and np.isnan(value):
            errors.append({
                "field": field,
                "message": f"Field '{field}' cannot be NaN"
            })
            continue

        # Infinite check
        if isinstance(value, (float, int, np.number)) and np.isinf(value):
            errors.append({
                "field": field,
                "message": f"Field '{field}' cannot be infinite"
            })
            continue

        # Data type check
        if not isinstance(value, config["type"]):
            errors.append({
                "field": field,
                "message": f"Field '{field}' must be numeric, got {type(value).__name__}"
            })
            continue

        # Discrete / Categorical checks (e.g. historical_landslide)
        if "allowed_values" in config:
            if value not in config["allowed_values"]:
                errors.append({
                    "field": field,
                    "message": f"Field '{field}' must be 0 or 1, got {value}"
                })
            continue

        # Continuous Range checks
        num_val = float(value)
        if "min" in config and num_val < config["min"]:
            errors.append({
                "field": field,
                "message": f"Field '{field}' cannot be less than {config['min']}, got {value}"
            })

        if "max" in config and num_val > config["max"]:
            errors.append({
                "field": field,
                "message": f"Field '{field}' cannot exceed {config['max']}, got {value}"
            })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


# ==============================================================================
# 3. INFERENCE PAYLOAD VALIDATION
# ==============================================================================

def validate_prediction_input(
    data: Any,
    allow_extra_features: bool = False
) -> Dict[str, Any]:
    """
    Validates a dictionary payload supplied for real-time inference.
    """
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    if not isinstance(data, dict):
        return {
            "valid": False,
            "errors": [{
                "field": "payload",
                "message": f"Expected dictionary payload, got {type(data).__name__}"
            }],
            "warnings": []
        }

    # Missing features check
    missing = [f for f in REQUIRED_FEATURES if f not in data]
    if missing:
        errors.append({
            "field": "features",
            "message": f"Missing required features: {missing}"
        })

    # Unexpected features check
    extra = [f for f in data if f not in FEATURE_CONFIG]
    if extra:
        if allow_extra_features:
            warnings.append({
                "field": "features",
                "message": f"Ignored unexpected extra features: {extra}"
            })
        else:
            errors.append({
                "field": "features",
                "message": f"Unexpected extra features: {extra}"
            })

    # Value-level sanity validation
    value_val = validate_feature_values(data)
    errors.extend(value_val["errors"])
    warnings.extend(value_val["warnings"])

    # Logical cross-field sanity checks (non-blocking warnings)
    if "rainfall_24h" in data and "rainfall_3d" in data:
        r24 = data["rainfall_24h"]
        r3d = data["rainfall_3d"]
        if isinstance(r24, (int, float)) and isinstance(r3d, (int, float)):
            if r24 > r3d and not (np.isnan(r24) or np.isnan(r3d)):
                warnings.append({
                    "field": "rainfall_24h",
                    "message": "rainfall_24h is greater than cumulative rainfall_3d"
                })

    if "rainfall_3d" in data and "rainfall_7d" in data:
        r3d = data["rainfall_3d"]
        r7d = data["rainfall_7d"]
        if isinstance(r3d, (int, float)) and isinstance(r7d, (int, float)):
            if r3d > r7d and not (np.isnan(r3d) or np.isnan(r7d)):
                warnings.append({
                    "field": "rainfall_3d",
                    "message": "rainfall_3d is greater than cumulative rainfall_7d"
                })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


# ==============================================================================
# 4. TRAINING DATASET VALIDATION
# ==============================================================================

def validate_training_data(
    df: Any,
    allow_extra_columns: bool = False
) -> Dict[str, Any]:
    """
    Validates a training dataset (pandas DataFrame) for schema, types,
    physical bounds, duplicates, target labels, and class distribution.
    """
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    if not isinstance(df, pd.DataFrame):
        return {
            "valid": False,
            "errors": [{
                "field": "dataset",
                "message": f"Expected pandas DataFrame, got {type(df).__name__}"
            }],
            "warnings": [],
            "class_distribution": {},
            "row_count": 0
        }

    row_count = len(df)
    if row_count == 0:
        return {
            "valid": False,
            "errors": [{
                "field": "dataset",
                "message": "Training dataset is empty (0 rows)"
            }],
            "warnings": [],
            "class_distribution": {},
            "row_count": 0
        }

    # 1. Required columns check
    missing_features = [f for f in REQUIRED_FEATURES if f not in df.columns]
    if missing_features:
        errors.append({
            "field": "columns",
            "message": f"Missing required feature columns: {missing_features}"
        })

    if TARGET_COLUMN not in df.columns:
        errors.append({
            "field": "columns",
            "message": f"Missing target column: '{TARGET_COLUMN}'"
        })

    # 2. Unexpected columns check
    expected_all = set(REQUIRED_FEATURES + [TARGET_COLUMN])
    extra_cols = [c for c in df.columns if c not in expected_all]
    if extra_cols:
        if allow_extra_columns:
            warnings.append({
                "field": "columns",
                "message": f"Dataset contains extra columns that will be ignored: {extra_cols}"
            })
        else:
            errors.append({
                "field": "columns",
                "message": f"Dataset contains unexpected columns: {extra_cols}"
            })

    # 3. Target label validation
    class_dist: Dict[str, int] = {}
    if TARGET_COLUMN in df.columns:
        unique_targets = df[TARGET_COLUMN].dropna().unique().tolist()
        invalid_targets = [t for t in unique_targets if t not in ALLOWED_TARGET_CLASSES]
        if invalid_targets:
            errors.append({
                "field": TARGET_COLUMN,
                "message": f"Invalid target labels found: {invalid_targets}. Allowed: {ALLOWED_TARGET_CLASSES}"
            })

        # Check target nulls
        target_nulls = int(df[TARGET_COLUMN].isnull().sum())
        if target_nulls > 0:
            errors.append({
                "field": TARGET_COLUMN,
                "message": f"Target column contains {target_nulls} null/NaN values"
            })

        class_dist = {str(k): int(v) for k, v in df[TARGET_COLUMN].value_counts().to_dict().items()}

        # Class balance information / warnings
        for target_cls in ALLOWED_TARGET_CLASSES:
            if target_cls not in class_dist:
                warnings.append({
                    "field": "class_balance",
                    "message": f"Target class '{target_cls}' has 0 samples in training data"
                })

    # 4. Duplicate rows check
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        warnings.append({
            "field": "duplicates",
            "message": f"Dataset contains {dup_count} duplicate row(s)"
        })

    # 5. Row-level and column-level feature checks
    for feature in REQUIRED_FEATURES:
        if feature not in df.columns:
            continue

        col = df[feature]

        # Numeric type check
        if not pd.api.types.is_numeric_dtype(col):
            errors.append({
                "field": feature,
                "message": f"Column '{feature}' must be numeric, got dtype {col.dtype}"
            })
            continue

        # Null / NaN check
        null_count = int(col.isnull().sum())
        if null_count > 0:
            errors.append({
                "field": feature,
                "message": f"Column '{feature}' contains {null_count} null/NaN value(s)"
            })

        # Infinity check
        inf_count = int(np.isinf(col).sum())
        if inf_count > 0:
            errors.append({
                "field": feature,
                "message": f"Column '{feature}' contains {inf_count} infinite value(s)"
            })

        # Physical boundary checks on valid numbers
        valid_vals = col.dropna()
        valid_vals = valid_vals[~np.isinf(valid_vals)]

        config = FEATURE_CONFIG[feature]
        if "allowed_values" in config:
            invalid_discrete = valid_vals[~valid_vals.isin(config["allowed_values"])]
            if len(invalid_discrete) > 0:
                errors.append({
                    "field": feature,
                    "message": f"Column '{feature}' contains {len(invalid_discrete)} value(s) outside allowed set {config['allowed_values']}"
                })
        else:
            if "min" in config:
                below_min = int((valid_vals < config["min"]).sum())
                if below_min > 0:
                    min_val = float(valid_vals.min())
                    errors.append({
                        "field": feature,
                        "message": f"Column '{feature}' has {below_min} value(s) below minimum {config['min']} (min found: {min_val})"
                    })

            if "max" in config:
                above_max = int((valid_vals > config["max"]).sum())
                if above_max > 0:
                    max_val = float(valid_vals.max())
                    errors.append({
                        "field": feature,
                        "message": f"Column '{feature}' has {above_max} value(s) exceeding maximum {config['max']} (max found: {max_val})"
                    })

    # 6. Dataset size warning (for demo / small datasets)
    if row_count < 50:
        warnings.append({
            "field": "dataset_size",
            "message": f"Dataset has only {row_count} rows. Suitable for pipeline testing, but statistically insufficient for real-world validation."
        })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "class_distribution": class_dist,
        "row_count": row_count
    }


if __name__ == "__main__":
    import json

    print("=" * 60)
    print("DATA VALIDATION TEST - CURRENT DEMO DATASET")
    print("=" * 60)

    try:
        demo_df = pd.read_csv("data/raw/landslide_training.csv")
        result = validate_training_data(demo_df)
        print(f"Dataset Valid: {result['valid']}")
        print(f"Row Count    : {result['row_count']}")
        print(f"Distribution : {result['class_distribution']}")
        print(f"Errors ({len(result['errors'])}): {json.dumps(result['errors'], indent=2)}")
        print(f"Warnings ({len(result['warnings'])}): {json.dumps(result['warnings'], indent=2)}")
    except Exception as exc:
        print(f"Error loading demo dataset: {exc}")
