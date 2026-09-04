"""
Document Understanding to ML Feature Extraction Bridge.

Converts structured entity outputs from PyMuPDF + GLiNER2 into the canonical
8-feature ML vector required by predict_risk().

Key Principles:
1. NEVER fabricate or guess missing features.
2. If required features are missing, prediction is marked as UNAVAILABLE.
3. Unit normalization is applied only when units are explicitly provided.
4. Preserves source traceability for every extracted feature.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import re
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.data_validation import (
    REQUIRED_FEATURES,
    validate_feature_values,
    validate_prediction_input,
)
from scripts.predict import predict_risk

# Canonical GLiNER2 extraction label candidates
GLINER_LABELS: List[str] = [
    "24-hour rainfall",
    "3-day rainfall",
    "7-day rainfall",
    "rainfall",
    "slope",
    "slope angle",
    "elevation",
    "historical landslide",
    "distance to landslide",
    "soil risk",
    "soil susceptibility",
    "landslide location",
    "district",
    "state",
    "date",
]

_CACHED_GLINER_MODEL: Optional[Any] = None


# ==============================================================================
# 1. PARSING & UNIT NORMALIZATION HELPERS
# ==============================================================================

def parse_numeric_with_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts a numeric float value and its trailing unit string from text.
    Examples:
      '182 mm' -> (182.0, 'mm')
      '38 degrees' -> (38.0, 'degrees')
      '0.8 km' -> (0.8, 'km')
    """
    if not isinstance(text, str) or not text.strip():
        return None, None

    # Match numeric portion (integer or float) and optional unit
    pattern = r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([a-zA-Z°%]+)?"
    match = re.search(pattern, text.strip())
    if not match:
        return None, None

    try:
        val = float(match.group(1))
        unit = match.group(2).lower() if match.group(2) else None
        return val, unit
    except (ValueError, TypeError):
        return None, None


def normalize_rainfall(val_str: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Normalizes rainfall to millimeters (mm).
    Returns (normalized_value, parsed_unit, warning_message).
    """
    val, unit = parse_numeric_with_unit(val_str)
    if val is None:
        return None, None, f"Could not parse numeric rainfall from '{val_str}'"

    if unit in ("cm", "centimeter", "centimeters", "centimetres"):
        return val * 10.0, unit, None
    elif unit in ("m", "meter", "meters", "metres"):
        return val * 1000.0, unit, None
    elif unit in ("in", "inch", "inches"):
        return val * 25.4, unit, None
    elif unit in ("mm", "millimeter", "millimeters", "millimetres") or unit is None:
        return val, unit or "mm", None
    else:
        return val, unit, f"Unrecognized rainfall unit '{unit}' in '{val_str}'; assumed mm"


def normalize_slope(val_str: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Normalizes terrain slope to degrees.
    """
    val, unit = parse_numeric_with_unit(val_str)
    if val is None:
        return None, None, f"Could not parse numeric slope from '{val_str}'"

    if unit in ("%", "percent", "percentage"):
        # Road/gradient percentage to degrees: degrees = arctan(percentage / 100)
        import math
        deg = math.degrees(math.atan(val / 100.0))
        return round(deg, 2), unit, None

    if unit in ("deg", "degree", "degrees", "°") or unit is None:
        return val, unit or "degrees", None

    return val, unit, f"Unrecognized slope unit '{unit}' in '{val_str}'"


def normalize_elevation(val_str: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Normalizes elevation to meters (m).
    """
    val, unit = parse_numeric_with_unit(val_str)
    if val is None:
        return None, None, f"Could not parse numeric elevation from '{val_str}'"

    if unit in ("ft", "feet", "foot"):
        return round(val * 0.3048, 2), unit, None
    elif unit in ("km", "kilometer", "kilometre", "kilometres", "kilometers"):
        return val * 1000.0, unit, None
    elif unit in ("m", "meter", "meters", "metre", "metres") or unit is None:
        return val, unit or "m", None

    return val, unit, f"Unrecognized elevation unit '{unit}' in '{val_str}'"


def normalize_distance(val_str: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Normalizes distance to kilometers (km).
    """
    val, unit = parse_numeric_with_unit(val_str)
    if val is None:
        return None, None, f"Could not parse numeric distance from '{val_str}'"

    if unit in ("m", "meter", "meters", "metre", "metres"):
        return round(val / 1000.0, 4), unit, None
    elif unit in ("km", "kilometer", "kilometre", "kilometres", "kilometers") or unit is None:
        return val, unit or "km", None
    elif unit in ("mi", "mile", "miles"):
        return round(val * 1.60934, 4), unit, None

    return val, unit, f"Unrecognized distance unit '{unit}' in '{val_str}'"


def normalize_soil_risk(val_str: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Normalizes soil susceptibility to a 0.0 to 1.0 index.
    Does NOT convert qualitative words into arbitrary numbers.
    """
    val, unit = parse_numeric_with_unit(val_str)
    if val is None:
        return None, None, f"Soil information '{val_str}' is qualitative; no numeric 0-1 index found"

    if unit in ("%", "percent"):
        return round(val / 100.0, 4), unit, None

    if 0.0 <= val <= 1.0:
        return round(val, 4), unit or "index", None
    elif 1.0 < val <= 10.0:
        # Scale 1-10 index to 0-1
        return round(val / 10.0, 4), unit, None
    elif 10.0 < val <= 100.0:
        # Scale 0-100 index to 0-1
        return round(val / 100.0, 4), unit, None

    return None, unit, f"Soil risk value '{val}' is outside valid range [0, 1]"


def parse_historical_landslide(val_str: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parses historical landslide indicator into 0, 1, or None (if missing/unspecified).
    Uses word-boundary regex patterns to avoid false matches on substring numbers (e.g. years).
    """
    if not isinstance(val_str, str):
        return None, "Invalid type for historical landslide"

    text = val_str.lower().strip()

    # Negative patterns (checked first to prioritize explicit negation)
    negative_patterns = [
        r"\bno\s+past\b",
        r"\bno\s+prior\b",
        r"\bno\s+previous\b",
        r"\bno\s+historical\b",
        r"\bno\s+landslide\b",
        r"\bnone\b",
        r"\bfalse\b",
        r"\b0\b",
        r"\babsent\b",
        r"\bzero\b"
    ]
    for pat in negative_patterns:
        if re.search(pat, text):
            return 0, None

    # Positive patterns
    positive_patterns = [
        r"\boccurred\b",
        r"\bprevious\b",
        r"\bpast\b",
        r"\bhistory\b",
        r"\byes\b",
        r"\btrue\b",
        r"\bdocumented\b",
        r"\bprior\b",
        r"\b1\b",
        r"\bpresent\b",
        r"\brecorded\b"
    ]
    for pat in positive_patterns:
        if re.search(pat, text):
            return 1, None

    return None, f"Could not conclusively determine historical landslide binary status from '{val_str}'"


# ==============================================================================
# 2. STRUCTURED ENTITY -> 8-FEATURE VECTOR BRIDGE
# ==============================================================================

def extract_features_from_entities(
    entities_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    raw_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Maps GLiNER2 entity extractions into the canonical 8-feature ML dictionary.
    Handles entity aliases, unit normalization, ambiguity flagging, and missing values.
    """
    extracted_features: Dict[str, Optional[float]] = {f: None for f in REQUIRED_FEATURES}
    sources: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []

    # Flatten input entities to a dict of label -> list of text mentions
    entity_map: Dict[str, List[str]] = {}

    if isinstance(entities_data, dict):
        # Format: {"entities": {"label": [...]}} or {"label": [...]}
        raw_dict = entities_data.get("entities", entities_data)
        for k, v in raw_dict.items():
            norm_k = k.lower().strip()
            if isinstance(v, list):
                entity_map[norm_k] = [str(item) for item in v]
            elif isinstance(v, (str, int, float)):
                entity_map[norm_k] = [str(v)]

    elif isinstance(entities_data, list):
        # Format: [{"label": "rainfall", "text": "182 mm"}, ...]
        for item in entities_data:
            if isinstance(item, dict) and "label" in item and "text" in item:
                lbl = str(item["label"]).lower().strip()
                entity_map.setdefault(lbl, []).append(str(item["text"]))

    # 1. RAINFALL 24H
    r24_labels = ["24-hour rainfall", "24h rainfall", "1-day rainfall", "daily rainfall", "rainfall 24h"]
    r24_found = False
    for lbl in r24_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, unit, warn = normalize_rainfall(raw_val)
            if val is not None:
                extracted_features["rainfall_24h"] = val
                sources["rainfall_24h"] = {"value": val, "source_text": raw_val, "entity_label": lbl, "unit": unit}
                r24_found = True
                if warn:
                    warnings.append(warn)
                break

    # 2. RAINFALL 3D
    r3d_labels = ["3-day rainfall", "3d rainfall", "72-hour rainfall", "rainfall 3d"]
    for lbl in r3d_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, unit, warn = normalize_rainfall(raw_val)
            if val is not None:
                extracted_features["rainfall_3d"] = val
                sources["rainfall_3d"] = {"value": val, "source_text": raw_val, "entity_label": lbl, "unit": unit}
                if warn:
                    warnings.append(warn)
                break

    # 3. RAINFALL 7D
    r7d_labels = ["7-day rainfall", "7d rainfall", "weekly rainfall", "cumulative 7-day rainfall", "rainfall 7d"]
    for lbl in r7d_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, unit, warn = normalize_rainfall(raw_val)
            if val is not None:
                extracted_features["rainfall_7d"] = val
                sources["rainfall_7d"] = {"value": val, "source_text": raw_val, "entity_label": lbl, "unit": unit}
                if warn:
                    warnings.append(warn)
                break

    # Generic Rainfall Ambiguity Check:
    # If generic 'rainfall' exists without explicit window labels
    if not r24_found and "rainfall" in entity_map and entity_map["rainfall"]:
        raw_val = entity_map["rainfall"][0]
        # Check if text explicitly says 24-hour
        if raw_text and ("24-hour" in raw_text.lower() or "24 hour" in raw_text.lower() or "daily" in raw_text.lower()):
            val, unit, warn = normalize_rainfall(raw_val)
            if val is not None:
                extracted_features["rainfall_24h"] = val
                sources["rainfall_24h"] = {"value": val, "source_text": raw_val, "entity_label": "rainfall (inferred 24h from context)", "unit": unit}
        else:
            warnings.append(
                f"Generic rainfall value '{raw_val}' extracted, but time window (24h/3d/7d) is unspecified. "
                "Feature left unassigned to avoid data fabrication."
            )

    # 4. SLOPE
    slope_labels = ["slope", "slope angle", "terrain slope", "gradient"]
    for lbl in slope_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, unit, warn = normalize_slope(raw_val)
            if val is not None:
                extracted_features["slope"] = val
                sources["slope"] = {"value": val, "source_text": raw_val, "entity_label": lbl, "unit": unit}
                if warn:
                    warnings.append(warn)
                break

    # 5. ELEVATION
    elev_labels = ["elevation", "altitude", "elevation above sea level"]
    for lbl in elev_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, unit, warn = normalize_elevation(raw_val)
            if val is not None:
                extracted_features["elevation"] = val
                sources["elevation"] = {"value": val, "source_text": raw_val, "entity_label": lbl, "unit": unit}
                if warn:
                    warnings.append(warn)
                break

    # 6. HISTORICAL LANDSLIDE
    hist_labels = ["historical landslide", "past landslide", "prior landslide", "previous landslide"]
    hist_found = False
    for lbl in hist_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, warn = parse_historical_landslide(raw_val)
            if val is not None:
                extracted_features["historical_landslide"] = val
                sources["historical_landslide"] = {"value": val, "source_text": raw_val, "entity_label": lbl}
                hist_found = True
                if warn:
                    warnings.append(warn)
                break

    if not hist_found and raw_text:
        # Check context for explicit occurrence
        val, _ = parse_historical_landslide(raw_text)
        if val is not None:
            extracted_features["historical_landslide"] = val
            sources["historical_landslide"] = {"value": val, "source_text": "Contextual document text", "entity_label": "inferred from document context"}

    # 7. DISTANCE TO LANDSLIDE
    dist_labels = ["distance to landslide", "distance to historical landslide", "proximity to landslide", "distance"]
    for lbl in dist_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, unit, warn = normalize_distance(raw_val)
            if val is not None:
                extracted_features["distance_to_landslide"] = val
                sources["distance_to_landslide"] = {"value": val, "source_text": raw_val, "entity_label": lbl, "unit": unit}
                if warn:
                    warnings.append(warn)
                break

    # 8. SOIL RISK
    soil_labels = ["soil risk", "soil susceptibility", "soil erodibility index", "soil index"]
    for lbl in soil_labels:
        if lbl in entity_map and entity_map[lbl]:
            raw_val = entity_map[lbl][0]
            val, unit, warn = normalize_soil_risk(raw_val)
            if val is not None:
                extracted_features["soil_risk"] = val
                sources["soil_risk"] = {"value": val, "source_text": raw_val, "entity_label": lbl, "unit": unit}
            if warn:
                warnings.append(warn)
            break

    # Determine missing features
    missing_features = [f for f in REQUIRED_FEATURES if extracted_features[f] is None]
    prediction_ready = (len(missing_features) == 0)

    # Validate extracted numeric bounds if complete
    if prediction_ready:
        val_check = validate_feature_values(extracted_features)
        if not val_check["valid"]:
            prediction_ready = False
            for err in val_check["errors"]:
                warnings.append(f"Validation failure on extracted field '{err['field']}': {err['message']}")

    return {
        "prediction_ready": prediction_ready,
        "features": extracted_features,
        "missing_features": missing_features,
        "warnings": warnings,
        "sources": sources,
    }


# ==============================================================================
# 3. TEXT-LEVEL & DOCUMENT-LEVEL PREDICTION PIPELINE
# ==============================================================================

def get_gliner_model(model_name: str = "fastino/gliner2-multi-v1") -> Any:
    """
    Lazy-loads and caches the GLiNER2 zero-shot NER model.
    """
    global _CACHED_GLINER_MODEL
    if _CACHED_GLINER_MODEL is None:
        from gliner2 import GLiNER2
        _CACHED_GLINER_MODEL = GLiNER2.from_pretrained(model_name)
    return _CACHED_GLINER_MODEL


def extract_features_from_text(
    text: str,
    gliner_model: Optional[Any] = None,
    custom_labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes GLiNER2 entity extraction on raw text and maps to 8-feature vector.
    """
    if not isinstance(text, str) or not text.strip():
        return {
            "prediction_ready": False,
            "features": {f: None for f in REQUIRED_FEATURES},
            "missing_features": REQUIRED_FEATURES.copy(),
            "warnings": ["Input document text is empty"],
            "sources": {}
        }

    labels = custom_labels or GLINER_LABELS
    model = gliner_model or get_gliner_model()
    raw_entities = model.extract_entities(text, labels)

    return extract_features_from_entities(raw_entities, raw_text=text)


def predict_from_document(
    document_input: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    gliner_model: Optional[Any] = None
) -> Dict[str, Any]:
    """
    End-to-End Document Pipeline:
    1. Extracts structured features from text or entity dict
    2. Validates completeness of the 8 canonical features
    3. Calls predict_risk() ONLY IF all 8 features are valid
    4. Returns structured result with explanation or missing-feature diagnostic
    """
    if isinstance(document_input, str):
        extraction = extract_features_from_text(document_input, gliner_model=gliner_model)
    else:
        extraction = extract_features_from_entities(document_input)

    if not extraction["prediction_ready"]:
        return {
            "prediction_ready": False,
            "prediction_status": "UNAVAILABLE_MISSING_FEATURES",
            "features": extraction["features"],
            "missing_features": extraction["missing_features"],
            "warnings": extraction["warnings"],
            "sources": extraction["sources"],
            "prediction": None,
            "message": (
                f"Prediction unavailable: {len(extraction['missing_features'])} required feature(s) missing "
                f"({', '.join(extraction['missing_features'])}). Data was not fabricated."
            )
        }

    # All 8 features are complete and physically valid -> execute risk prediction
    try:
        prediction_result = predict_risk(extraction["features"])
        return {
            "prediction_ready": True,
            "prediction_status": "COMPLETED",
            "features": extraction["features"],
            "missing_features": [],
            "warnings": extraction["warnings"],
            "sources": extraction["sources"],
            "prediction": prediction_result,
            "message": "Risk prediction successfully generated from document."
        }
    except Exception as exc:
        return {
            "prediction_ready": False,
            "prediction_status": "PREDICTION_ERROR",
            "features": extraction["features"],
            "missing_features": [],
            "warnings": extraction["warnings"] + [f"Prediction error: {exc}"],
            "sources": extraction["sources"],
            "prediction": None,
            "message": f"Inference engine error: {exc}"
        }


# ==============================================================================
# 4. CLI DEMONSTRATION RUNNER
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DOCUMENT TO ML FEATURE EXTRACTION BRIDGE DEMO")
    print("=" * 60)

    # Example 1: Incomplete report (typical real-world case)
    incomplete_text_entities = {
        "entities": {
            "rainfall": ["182 mm"],
            "slope angle": ["38 degrees"],
            "elevation": ["850 metres"],
            "landslide location": ["Cherrapunji"]
        }
    }

    print("\n--- TEST 1: INCOMPLETE DOCUMENT ENTITIES ---")
    res1 = predict_from_document(incomplete_text_entities)
    print(f"Prediction Ready: {res1['prediction_ready']}")
    print(f"Status          : {res1['prediction_status']}")
    print(f"Missing Features: {res1['missing_features']}")
    print(f"Message         : {res1['message']}")

    # Example 2: Complete report (all 8 features available)
    complete_text_entities = {
        "entities": {
            "24-hour rainfall": ["182 mm"],
            "3-day rainfall": ["420 mm"],
            "7-day rainfall": ["650 mm"],
            "slope angle": ["38 degrees"],
            "elevation": ["850 metres"],
            "historical landslide": ["occurred near Cherrapunji in 2022"],
            "distance to landslide": ["0.8 km"],
            "soil risk": ["0.70"]
        }
    }

    print("\n--- TEST 2: COMPLETE DOCUMENT ENTITIES ---")
    res2 = predict_from_document(complete_text_entities)
    print(f"Prediction Ready: {res2['prediction_ready']}")
    print(f"Status          : {res2['prediction_status']}")
    if res2["prediction"]:
        print(f"Predicted Risk  : {res2['prediction']['risk']}")
        print(f"Confidence      : {res2['prediction']['confidence']:.2%}")
        print(f"Contributing Factors ({len(res2['prediction']['contributing_factors'])}):")
        for f in res2["prediction"]["contributing_factors"]:
            print(f"  * {f['feature']} = {f['value']}: {f['message']}")

    print("\n" + "=" * 60)
