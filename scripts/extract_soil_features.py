from __future__ import annotations

import json
import math
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslides"
    / "landslide_training_samples_terrain.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "landslides"
OUTPUT_CSV = OUTPUT_DIR / "landslide_training_samples_soil.csv"
REPORT_JSON = OUTPUT_DIR / "soil_extraction_report.json"
CACHE_FILE = OUTPUT_DIR / "soilgrids_cache.json"

URL_PROPERTIES = "https://rest.isric.org/soilgrids/v2.0/properties/query"
URL_CLASSIFICATION = "https://rest.isric.org/soilgrids/v2.0/classification/query"

MAX_WORKERS = 6
REQUEST_TIMEOUT = 12.0
SAVE_INTERVAL = 25  # Save cache every 25 queries

_thread_local = threading.local()


def log(msg=""):
    print(msg, flush=True)


def get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=5, pool_maxsize=5)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _thread_local.session = s
    return _thread_local.session


def query_soilgrids_single(lat: float, lon: float) -> dict:
    session = get_session()
    result = {
        "latitude": lat,
        "longitude": lon,
        "soil_class": None,
        "clay_percent": None,
        "sand_percent": None,
        "silt_percent": None,
        "bulk_density_kg_dm3": None,
        "soil_quality": "OK",
        "api_properties_status": None,
        "api_classification_status": None,
        "error_message": None,
    }

    # 1. Properties Query (0-5 cm depth)
    try:
        r_prop = session.get(
            URL_PROPERTIES,
            params={
                "lat": lat,
                "lon": lon,
                "property": ["clay", "sand", "silt", "bdod"],
                "depth": ["0-5cm"],
                "value": ["mean"],
            },
            timeout=REQUEST_TIMEOUT,
        )
        result["api_properties_status"] = r_prop.status_code
        if r_prop.status_code == 200:
            d_prop = r_prop.json()
            layers = d_prop.get("properties", {}).get("layers", [])
            prop_map = {}
            for layer in layers:
                name = layer.get("name")
                depths = layer.get("depths", [])
                if depths:
                    val = depths[0].get("values", {}).get("mean")
                    prop_map[name] = val

            clay_raw = prop_map.get("clay")
            sand_raw = prop_map.get("sand")
            silt_raw = prop_map.get("silt")
            bdod_raw = prop_map.get("bdod")

            if clay_raw is not None:
                result["clay_percent"] = round(float(clay_raw) / 10.0, 2)
            if sand_raw is not None:
                result["sand_percent"] = round(float(sand_raw) / 10.0, 2)
            if silt_raw is not None:
                result["silt_percent"] = round(float(silt_raw) / 10.0, 2)
            if bdod_raw is not None:
                result["bulk_density_kg_dm3"] = round(float(bdod_raw) / 100.0, 3)

            if all(v is None for v in [clay_raw, sand_raw, silt_raw, bdod_raw]):
                result["soil_quality"] = "MISSING"

        elif r_prop.status_code in (404, 400):
            result["soil_quality"] = "MISSING"
        else:
            result["soil_quality"] = "API_ERROR"
            result["error_message"] = f"Properties HTTP {r_prop.status_code}"

    except Exception as e:
        result["soil_quality"] = "API_ERROR"
        result["error_message"] = f"Properties error: {e}"

    # 2. Classification Query (WRB Most Probable)
    try:
        r_class = session.get(
            URL_CLASSIFICATION,
            params={"lat": lat, "lon": lon},
            timeout=REQUEST_TIMEOUT,
        )
        result["api_classification_status"] = r_class.status_code
        if r_class.status_code == 200:
            d_class = r_class.json()
            wrb_class = d_class.get("wrb_class_name")
            if wrb_class:
                result["soil_class"] = str(wrb_class).strip()
            elif result["soil_quality"] == "OK":
                result["soil_quality"] = "MISSING"
        elif r_class.status_code in (404, 400):
            if result["soil_quality"] == "OK":
                result["soil_quality"] = "MISSING"
        else:
            if result["soil_quality"] != "API_ERROR":
                result["soil_quality"] = "API_ERROR"
                result["error_message"] = f"Classification HTTP {r_class.status_code}"

    except Exception as e:
        if result["soil_quality"] != "API_ERROR":
            result["soil_quality"] = "API_ERROR"
            result["error_message"] = f"Classification error: {e}"

    return result


def main():
    log("=" * 80)
    log("PHASE 8E.2.1 - SOILGRIDS SOIL FEATURE EXTRACTION")
    log("=" * 80)

    start_time = time.time()
    extraction_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Verify input CSV
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    log(f"Input dataset:       {INPUT_CSV}")
    log(f"Input row count:     {len(df)}")

    if len(df) != 4016:
        raise ValueError(f"Expected exactly 4,016 samples, found {len(df)}.")

    positives = int((df["label"] == 1).sum())
    negatives = int((df["label"] == 0).sum())
    log(f"Positive samples:    {positives}")
    log(f"Negative samples:    {negatives}")

    if positives != 2008 or negatives != 2008:
        raise ValueError(f"Expected 2,008 positives and 2,008 negatives. Found {positives} / {negatives}.")

    # 2. Extract unique coordinates
    unique_coords = (
        df[["latitude", "longitude"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    total_unique = len(unique_coords)
    log(f"\nUnique coordinates to query: {total_unique} (from {len(df)} samples)")

    # 3. Load cache if exists
    cache: dict[str, dict] = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            log(f"Loaded existing cache with {len(cache)} cached coordinates.")
        except Exception as e:
            log(f"Warning: Failed to load cache file: {e}. Starting fresh.")
            cache = {}

    # Determine coordinates needing queries
    to_query = []
    for _, row in unique_coords.iterrows():
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        key = f"{lat:.6f},{lon:.6f}"
        if key not in cache:
            to_query.append((lat, lon, key))

    log(f"Coordinates already in cache: {total_unique - len(to_query)}")
    log(f"Coordinates needing API call: {len(to_query)}")

    # 4. Query SoilGrids API with thread pool
    if to_query:
        log(f"\nStarting queries with {MAX_WORKERS} workers...")
        completed_count = 0
        batch_start_time = time.time()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_key = {
                executor.submit(query_soilgrids_single, lat, lon): key
                for lat, lon, key in to_query
            }

            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    res = future.result()
                    cache[key] = res
                except Exception as exc:
                    log(f"Error querying {key}: {exc}")
                    cache[key] = {
                        "soil_class": None,
                        "clay_percent": None,
                        "sand_percent": None,
                        "silt_percent": None,
                        "bulk_density_kg_dm3": None,
                        "soil_quality": "API_ERROR",
                        "error_message": str(exc),
                    }

                completed_count += 1

                # Log progress every 50
                if completed_count % 50 == 0 or completed_count == len(to_query):
                    elapsed_batch = time.time() - batch_start_time
                    rate = completed_count / elapsed_batch if elapsed_batch > 0 else 0
                    remaining = (len(to_query) - completed_count) / rate if rate > 0 else 0
                    log(
                        f"  Queried {completed_count}/{len(to_query)} "
                        f"({completed_count/len(to_query)*100:.1f}%) "
                        f"| Speed: {rate:.2f} coords/s | ETA: {remaining/60:.1f}m"
                    )

                # Periodic cache save every SAVE_INTERVAL
                if completed_count % SAVE_INTERVAL == 0 or completed_count == len(to_query):
                    tmp_cache = CACHE_FILE.with_suffix(".json.tmp")
                    tmp_cache.write_text(json.dumps(cache, indent=1), encoding="utf-8")
                    tmp_cache.replace(CACHE_FILE)

    # Final cache save
    tmp_cache = CACHE_FILE.with_suffix(".json.tmp")
    tmp_cache.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    tmp_cache.replace(CACHE_FILE)
    log(f"\nCache successfully updated: {len(cache)} total entries saved to {CACHE_FILE}")

    # 5. Map features back to all 4,016 samples
    log("\nMapping soil features to sample rows...")

    soil_classes = []
    clay_vals = []
    sand_vals = []
    silt_vals = []
    bdod_vals = []
    qualities = []

    for _, row in df.iterrows():
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        key = f"{lat:.6f},{lon:.6f}"
        data = cache.get(key, {})

        soil_classes.append(data.get("soil_class") if data.get("soil_class") else np.nan)
        clay_vals.append(data.get("clay_percent") if data.get("clay_percent") is not None else np.nan)
        sand_vals.append(data.get("sand_percent") if data.get("sand_percent") is not None else np.nan)
        silt_vals.append(data.get("silt_percent") if data.get("silt_percent") is not None else np.nan)
        bdod_vals.append(data.get("bulk_density_kg_dm3") if data.get("bulk_density_kg_dm3") is not None else np.nan)
        qualities.append(data.get("soil_quality", "MISSING"))

    df["soil_class"] = soil_classes
    df["clay_percent"] = clay_vals
    df["sand_percent"] = sand_vals
    df["silt_percent"] = silt_vals
    df["bulk_density_kg_dm3"] = bdod_vals
    df["soil_quality"] = qualities

    # 6. Preservation & Integrity Checks
    log("\n" + "=" * 80)
    log("VALIDATION & INTEGRITY SUMMARY")
    log("=" * 80)

    original_df = pd.read_csv(INPUT_CSV)

    coord_diff = (
        (df["latitude"] != original_df["latitude"]).sum()
        + (df["longitude"] != original_df["longitude"]).sum()
    )
    label_diff = (df["label"] != original_df["label"]).sum()
    slide_no_diff = (df["slide_no"].fillna("") != original_df["slide_no"].fillna("")).sum()
    dup_rows = df.duplicated(subset=["sample_id"]).sum()

    log(f"Input samples:       {len(original_df)}")
    log(f"Output samples:      {len(df)}")
    log(f"Row count preserved: {'PASS' if len(df) == 4016 else 'FAIL'}")
    log(f"Positive labels:     {(df['label'] == 1).sum()}")
    log(f"Negative labels:     {(df['label'] == 0).sum()}")
    log(f"Coordinate changes:  {coord_diff}")
    log(f"Label changes:       {label_diff}")
    log(f"SlideNo changes:     {slide_no_diff}")
    log(f"Duplicate rows:      {dup_rows}")

    if coord_diff > 0 or label_diff > 0 or slide_no_diff > 0 or dup_rows > 0:
        raise ValueError("Critical integrity violation: base sample attributes were altered.")

    # Soil quality distribution
    quality_counts = df["soil_quality"].value_counts().to_dict()
    log(f"\nSoil quality distribution: {quality_counts}")

    # Top soil classes
    class_counts = df["soil_class"].value_counts(dropna=False).head(10).to_dict()
    log(f"\nTop WRB soil classes: {class_counts}")

    # Feature statistics
    stats = {}
    for feat in ["clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3"]:
        valid_s = df[feat].dropna()
        stat_dict = {
            "valid": int(len(valid_s)),
            "null": int(df[feat].isna().sum()),
            "min": float(valid_s.min()) if len(valid_s) else None,
            "max": float(valid_s.max()) if len(valid_s) else None,
            "mean": float(valid_s.mean()) if len(valid_s) else None,
            "std": float(valid_s.std()) if len(valid_s) else None,
        }
        stats[feat] = stat_dict

        log(f"\n{feat.upper()}:")
        log(f"  valid: {stat_dict['valid']}")
        log(f"  null:  {stat_dict['null']}")
        if len(valid_s):
            log(f"  min:   {stat_dict['min']:.2f}")
            log(f"  max:   {stat_dict['max']:.2f}")
            log(f"  mean:  {stat_dict['mean']:.2f}")
            log(f"  std:   {stat_dict['std']:.2f}")

    # 7. Save output CSV atomically
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tmp_csv = OUTPUT_CSV.with_suffix(".csv.tmp")
    df.to_csv(tmp_csv, index=False)
    tmp_csv.replace(OUTPUT_CSV)

    # 8. Save audit report
    api_requests_count = len(to_query) * 2
    successful_count = sum(1 for v in cache.values() if v.get("soil_quality") == "OK")

    report = {
        "status": "PASS",
        "dataset_name": "Landslide Training Samples with SoilGrids Features",
        "source": "ISRIC SoilGrids v2.0 REST API",
        "api_properties_url": URL_PROPERTIES,
        "api_classification_url": URL_CLASSIFICATION,
        "extraction_timestamp_utc": extraction_timestamp,
        "input_file": str(INPUT_CSV),
        "output_file": str(OUTPUT_CSV),
        "input_rows": len(original_df),
        "output_rows": len(df),
        "unique_coordinates": total_unique,
        "coordinates_queried_this_run": len(to_query),
        "total_cached_coordinates": len(cache),
        "api_requests": api_requests_count,
        "successful_coordinates": successful_count,
        "failed_coordinates": total_unique - successful_count,
        "preservation_checks": {
            "row_count_preserved": len(df) == 4016,
            "coordinate_changes": int(coord_diff),
            "label_changes": int(label_diff),
            "slide_no_changes": int(slide_no_diff),
            "duplicate_rows": int(dup_rows),
        },
        "soil_quality_distribution": quality_counts,
        "soil_class_nulls": int(df["soil_class"].isna().sum()),
        "clay_nulls": int(df["clay_percent"].isna().sum()),
        "sand_nulls": int(df["sand_percent"].isna().sum()),
        "silt_nulls": int(df["silt_percent"].isna().sum()),
        "bulk_density_nulls": int(df["bulk_density_kg_dm3"].isna().sum()),
        "feature_statistics": stats,
        "top_wrb_soil_classes": {str(k): int(v) for k, v in class_counts.items()},
        "scientific_notes": [
            "Soil data extracted from ISRIC SoilGrids v2.0 (250m resolution).",
            "Physical properties (clay, sand, silt, bdod) sampled at 0-5 cm depth.",
            "bulk_density_kg_dm3 represents fine earth fraction bulk density (bdod) converted from cg/cm3 to kg/dm3.",
            "soil_class represents the World Reference Base (WRB) Most Probable Reference Soil Group.",
            "Base landslide inventory, coordinates, and labels are 100% preserved.",
        ],
    }

    tmp_json = REPORT_JSON.with_suffix(".json.tmp")
    tmp_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    tmp_json.replace(REPORT_JSON)

    log(f"\nSaved soil-enriched CSV: {OUTPUT_CSV}")
    log(f"Saved audit report:       {REPORT_JSON}")
    log("\nPhase 8E.2.1 soil extraction PASSED.")


if __name__ == "__main__":
    main()
