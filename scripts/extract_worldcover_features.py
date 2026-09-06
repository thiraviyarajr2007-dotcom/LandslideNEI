"""
Phase 8E.2.2 - ESA WorldCover 10m (v200, 2021) Feature Extraction
==================================================================
Dataset:
  ESA WorldCover 10m 2021 v200
  Source: AWS Open Data (s3://esa-worldcover/v200/2021/map/)
  Resolution: 10m nominal (8.333333e-5 degrees, EPSG:4326)

Extracted Feature Columns:
  - landcover_class_code: Numeric code (10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100)
  - landcover_class: Human-readable official ESA class description
  - lulc_quality: Quality indicator ("OK", "NODATA", "OUT_OF_TILE", "INVALID_CLASS")

Strict Preservation Rules:
  - Preserves all 4,016 samples (2,008 positive Bhuvan landslides, 2,008 GADM ADM1 spatial negatives)
  - 0 coordinate drift, 0 label changes, 0 SlideNo alterations
  - All existing terrain and soil features remain 100% bitwise identical
  - Existing Bhuvan 'lulc' column remains untouched as separate historical attribute
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests

# ==============================================================================
# CONFIGURATION & PATHS
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslides"
    / "landslide_training_samples_soil.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "landslides"
OUTPUT_CSV = OUTPUT_DIR / "landslide_training_samples_lulc.csv"
REPORT_JSON = OUTPUT_DIR / "lulc_extraction_report.json"

RAW_WORLDCOVER_DIR = PROJECT_ROOT / "data" / "raw" / "worldcover" / "esa_worldcover_v200"
PLAN_JSON = PROJECT_ROOT / "data" / "inspection" / "worldcover" / "worldcover_tile_plan.json"

AWS_S3_BASE = "https://esa-worldcover.s3.amazonaws.com/v200/2021/map"

# Official ESA WorldCover v200 10m Legend
WORLDCOVER_LEGEND = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

MAX_DOWNLOAD_WORKERS = 3


def log(msg=""):
    print(msg, flush=True)


def get_tile_id(lat: float, lon: float) -> str:
    """Determine the 3x3 degree tile ID containing a given coordinate."""
    tile_lat = int(math.floor(lat / 3.0) * 3)
    tile_lon = int(math.floor(lon / 3.0) * 3)
    return f"N{tile_lat:02d}E{tile_lon:03d}"


def download_tile(tile_info: dict) -> Path:
    """Download a single WorldCover tile atomically if not already complete."""
    file_name = tile_info["file_name"]
    target_path = RAW_WORLDCOVER_DIR / file_name
    expected_size = tile_info["size_bytes"]

    if target_path.exists() and target_path.stat().st_size == expected_size:
        log(f"  [OK] Already downloaded: {file_name} ({target_path.stat().st_size / (1024*1024):.2f} MB)")
        return target_path

    url = tile_info["https_url"]
    tmp_path = target_path.with_suffix(".tif.tmp")
    log(f"  Downloading {file_name} ({tile_info['size_mb']:.2f} MB) from AWS...")
    t0 = time.time()

    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()

    with open(tmp_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    if tmp_path.stat().st_size != expected_size:
        tmp_path.unlink(missing_ok=True)
        raise IOError(
            f"Download incomplete for {file_name}: expected {expected_size} bytes, got {tmp_path.stat().st_size}"
        )

    tmp_path.replace(target_path)
    elapsed = time.time() - t0
    speed_mb = (target_path.stat().st_size / (1024 * 1024)) / elapsed if elapsed > 0 else 0
    log(f"  [OK] Finished {file_name} in {elapsed:.2f}s ({speed_mb:.2f} MB/s)")
    return target_path


def validate_raster(tif_path: Path, tile_id: dict) -> dict:
    """Thoroughly validate a downloaded GeoTIFF raster."""
    val_res = {
        "file": str(tif_path.name),
        "exists": tif_path.exists(),
        "size_bytes": tif_path.stat().st_size,
        "readable": False,
        "crs": None,
        "dimensions": None,
        "bounds": None,
        "nominal_res_deg": None,
        "nodata_val": None,
        "valid_classes_observed": [],
        "passed": False,
        "error": None,
    }

    try:
        with rasterio.open(tif_path) as src:
            val_res["readable"] = True
            val_res["crs"] = str(src.crs)
            val_res["dimensions"] = [int(src.height), int(src.width)]
            val_res["bounds"] = [float(src.bounds.left), float(src.bounds.bottom), float(src.bounds.right), float(src.bounds.top)]
            val_res["nominal_res_deg"] = float(src.res[0])
            val_res["nodata_val"] = float(src.nodatavals[0]) if src.nodatavals else None

            # Assertions
            if src.crs != rasterio.crs.CRS.from_epsg(4326):
                raise ValueError(f"Expected CRS EPSG:4326, got {src.crs}")
            if (src.height, src.width) != (36000, 36000):
                raise ValueError(f"Expected dimensions (36000, 36000), got ({src.height}, {src.width})")
            if not math.isclose(src.res[0], 8.333333e-5, rel_tol=1e-3):
                raise ValueError(f"Expected 10m nominal resolution ~8.333e-5, got {src.res[0]}")

            val_res["passed"] = True

    except Exception as e:
        val_res["error"] = str(e)
        val_res["passed"] = False

    return val_res


def main():
    log("=" * 80)
    log("PHASE 8E.2.2 - ESA WORLDCOVER 10M FEATURE EXTRACTION")
    log("=" * 80)

    start_time = time.time()
    extraction_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Load and verify input dataset
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

    # 2. Verify / load tile plan
    if not PLAN_JSON.exists():
        raise FileNotFoundError(f"Tile plan not found: {PLAN_JSON}")

    tile_plan = json.loads(PLAN_JSON.read_text(encoding="utf-8"))
    tiles_to_process = tile_plan["tiles"]
    log(f"\nTile Plan: {len(tiles_to_process)} required tiles, {tile_plan['total_download_size_mb']:.2f} MB total")

    # 3. Acquire raw WorldCover tiles
    log(f"\nAcquiring raw tiles to {RAW_WORLDCOVER_DIR}...")
    RAW_WORLDCOVER_DIR.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(download_tile, t): t for t in tiles_to_process}
        for future in as_completed(futures):
            future.result()

    log("\nAll tiles acquired successfully.")

    # 4. Validate all downloaded rasters
    log("\nValidating downloaded GeoTIFFs with rasterio...")
    validation_results = []
    all_passed = True
    for t in tiles_to_process:
        tif_path = RAW_WORLDCOVER_DIR / t["file_name"]
        res = validate_raster(tif_path, t)
        validation_results.append(res)
        status_str = "PASS" if res["passed"] else f"FAIL: {res['error']}"
        log(f"  {t['tile_id']}: {status_str} ({res['dimensions']}, res={res['nominal_res_deg']:.2e})")
        if not res["passed"]:
            all_passed = False

    if not all_passed:
        raise RuntimeError("One or more WorldCover tiles failed rasterio validation!")

    log("\nAll 9 WorldCover tiles PASSED validation.")

    # 5. Extract Land Cover Class for all 4,016 samples
    log("\nExtracting land cover classes at sample coordinates...")
    df["assigned_tile_id"] = [get_tile_id(lat, lon) for lat, lon in zip(df["latitude"], df["longitude"])]

    # Open each tile once and sample all coordinates falling inside it
    extracted_codes = {}
    extracted_names = {}
    extracted_qualities = {}

    for t in tiles_to_process:
        tile_id = t["tile_id"]
        tif_path = RAW_WORLDCOVER_DIR / t["file_name"]
        mask = df["assigned_tile_id"] == tile_id
        tile_indices = df[mask].index

        if len(tile_indices) == 0:
            continue

        lons = df.loc[tile_indices, "longitude"].values
        lats = df.loc[tile_indices, "latitude"].values
        coords = list(zip(lons, lats))

        with rasterio.open(tif_path) as src:
            sampled_vals = [val[0] for val in src.sample(coords)]

        for idx, val in zip(tile_indices, sampled_vals):
            int_val = int(val)
            if int_val == 0:
                # Nodata / water outside coverage
                extracted_codes[idx] = np.nan
                extracted_names[idx] = None
                extracted_qualities[idx] = "NODATA"
            elif int_val in WORLDCOVER_LEGEND:
                extracted_codes[idx] = int_val
                extracted_names[idx] = WORLDCOVER_LEGEND[int_val]
                extracted_qualities[idx] = "OK"
            else:
                extracted_codes[idx] = int_val
                extracted_names[idx] = f"Unknown ({int_val})"
                extracted_qualities[idx] = "INVALID_CLASS"

    # Map back to DataFrame in exact original order
    df["landcover_class_code"] = [extracted_codes.get(i, np.nan) for i in range(len(df))]
    df["landcover_class"] = [extracted_names.get(i, None) for i in range(len(df))]
    df["lulc_quality"] = [extracted_qualities.get(i, "OUT_OF_TILE") for i in range(len(df))]
    df.drop(columns=["assigned_tile_id"], inplace=True)

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

    # Check that existing terrain & soil columns are 100% untouched
    terrain_cols = ["elevation_m", "slope_deg", "aspect_deg", "relief_std_5x5_m", "terrain_quality"]
    soil_cols = ["soil_class", "clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3", "soil_quality"]
    bhuvan_lulc_diff = (df["lulc"].fillna("") != original_df["lulc"].fillna("")).sum()

    terrain_diff = 0
    for c in terrain_cols:
        terrain_diff += (df[c].fillna(-9999) != original_df[c].fillna(-9999)).sum()

    soil_diff = 0
    for c in soil_cols:
        soil_diff += (df[c].fillna(-9999) != original_df[c].fillna(-9999)).sum()

    log(f"Input samples:             {len(original_df)}")
    log(f"Output samples:            {len(df)}")
    log(f"Row count preserved:       {'PASS' if len(df) == 4016 else 'FAIL'}")
    log(f"Positive labels:           {(df['label'] == 1).sum()}")
    log(f"Negative labels:           {(df['label'] == 0).sum()}")
    log(f"Coordinate changes:        {coord_diff}")
    log(f"Label changes:             {label_diff}")
    log(f"SlideNo changes:           {slide_no_diff}")
    log(f"Terrain columns drift:     {terrain_diff}")
    log(f"Soil columns drift:        {soil_diff}")
    log(f"Bhuvan lulc column drift:  {bhuvan_lulc_diff}")
    log(f"Duplicate rows:            {dup_rows}")

    if (
        len(df) != 4016
        or coord_diff > 0
        or label_diff > 0
        or slide_no_diff > 0
        or terrain_diff > 0
        or soil_diff > 0
        or bhuvan_lulc_diff > 0
        or dup_rows > 0
    ):
        raise ValueError("Critical integrity violation: baseline sample attributes were modified!")

    # Class distribution
    class_counts = df["landcover_class"].value_counts(dropna=False).to_dict()
    log(f"\nLand Cover Class distribution:\n{json.dumps(class_counts, indent=2)}")

    quality_counts = df["lulc_quality"].value_counts().to_dict()
    log(f"\nLULC Quality distribution: {quality_counts}")

    # Scientific comparison: Landslides vs Negatives
    log("\n" + "=" * 80)
    log("SCIENTIFIC FEATURE DISTRIBUTION: LANDSLIDES (1) vs NEGATIVES (0)")
    log("=" * 80)
    crosstab = pd.crosstab(df["landcover_class"].fillna("NODATA"), df["label"], margins=True)
    crosstab.columns = ["Spatial Negatives (0)", "Landslides (1)", "All"]
    log(crosstab.to_string())

    # 7. Save output CSV atomically with 100% exact text line preservation
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_csv = OUTPUT_CSV.with_suffix(".csv.tmp")
    with open(INPUT_CSV, "r", encoding="utf-8") as f_in:
        in_lines = [line.rstrip("\r\n") for line in f_in]

    header = in_lines[0] + ",landcover_class_code,landcover_class,lulc_quality\n"
    out_lines = [header]
    for i in range(len(df)):
        c_val = df.loc[i, "landcover_class_code"]
        c_str = str(int(c_val)) if pd.notna(c_val) else ""
        n_str = str(df.loc[i, "landcover_class"]) if pd.notna(df.loc[i, "landcover_class"]) else ""
        q_str = str(df.loc[i, "lulc_quality"])
        out_lines.append(f"{in_lines[i + 1]},{c_str},{n_str},{q_str}\n")

    with open(tmp_csv, "w", encoding="utf-8") as f_out:
        f_out.writelines(out_lines)
    tmp_csv.replace(OUTPUT_CSV)

    # 8. Save comprehensive audit report
    report = {
        "status": "PASS",
        "dataset_name": "Landslide Training Samples with ESA WorldCover 10m Features",
        "dataset_version": "v200 (2021)",
        "source": "ESA WorldCover 10m (AWS Open Data s3://esa-worldcover/v200/2021/map/)",
        "nominal_resolution_m": 10.0,
        "extraction_timestamp_utc": extraction_timestamp,
        "input_file": str(INPUT_CSV),
        "output_file": str(OUTPUT_CSV),
        "input_rows": len(original_df),
        "output_rows": len(df),
        "preservation_checks": {
            "row_count_preserved": len(df) == 4016,
            "positive_label_count": int((df["label"] == 1).sum()),
            "negative_label_count": int((df["label"] == 0).sum()),
            "coordinate_changes": int(coord_diff),
            "label_changes": int(label_diff),
            "slide_no_changes": int(slide_no_diff),
            "terrain_drift": int(terrain_diff),
            "soil_drift": int(soil_diff),
            "bhuvan_lulc_drift": int(bhuvan_lulc_diff),
            "duplicate_rows": int(dup_rows),
        },
        "tiles_required": len(tiles_to_process),
        "tiles_downloaded": len(tiles_to_process),
        "tile_validation_summary": [
            {
                "tile_id": t["tile_id"],
                "file_name": t["file_name"],
                "sample_count": t["sample_count"],
                "passed": next(r["passed"] for r in validation_results if r["file"] == t["file_name"]),
            }
            for t in tiles_to_process
        ],
        "lulc_quality_distribution": quality_counts,
        "landcover_class_distribution": {str(k): int(v) for k, v in class_counts.items()},
        "landcover_by_label": {
            str(cls): {
                "landslide_positives": int((df[df["landcover_class"] == cls]["label"] == 1).sum()),
                "spatial_negatives": int((df[df["landcover_class"] == cls]["label"] == 0).sum()),
                "total": int((df["landcover_class"] == cls).sum()),
            }
            for cls in df["landcover_class"].dropna().unique()
        },
        "scientific_notes": [
            "ESA WorldCover 10m v200 provides global land cover at 10 m resolution for 2021 based on Sentinel-1 and Sentinel-2.",
            "Class codes and human-readable names follow the official ESA WorldCover 11-class legend exactly.",
            "Base Bhuvan inventory 'lulc' attribute is 100% preserved as historical provenance.",
            "Baseline landslide inventory, coordinates, and labels are 100% preserved.",
            "No synthetic imputation or default zeroes were applied.",
        ],
    }

    tmp_json = REPORT_JSON.with_suffix(".json.tmp")
    tmp_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    tmp_json.replace(REPORT_JSON)

    log(f"\nSaved LULC-enriched CSV: {OUTPUT_CSV}")
    log(f"Saved audit report:       {REPORT_JSON}")
    log(f"Total pipeline elapsed:   {time.time()-start_time:.2f}s")
    log("\nPhase 8E.2.2 WorldCover extraction PASSED.")


if __name__ == "__main__":
    main()
