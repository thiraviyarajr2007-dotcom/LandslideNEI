from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslides"
    / "landslide_training_samples_gadm_corrected.csv"
)

DEM_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "dem"
    / "copernicus_glo30"
    / "downloads"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "landslides"
OUTPUT_CSV = OUTPUT_DIR / "landslide_training_samples_terrain.csv"
REPORT_JSON = OUTPUT_DIR / "terrain_extraction_report.json"

METRES_PER_DEGREE_LAT = 111320.0
MIN_VALID_CELLS_5X5 = 13


def log(msg=""):
    print(msg, flush=True)


def get_tile_info(lat: float, lon: float) -> tuple[str, Path]:
    lat_f = int(math.floor(lat))
    lon_f = int(math.floor(lon))
    key = f"Copernicus_DSM_COG_10_N{lat_f:02d}_00_E{lon_f:03d}_00_DEM"
    filename = f"{key}.tif"
    return key, DEM_DIR / filename


def extract_features_for_point(
    ds: rasterio.io.DatasetReader,
    lat: float,
    lon: float,
    tile_key: str,
) -> dict:
    # Get pixel coordinates
    r, c = ds.index(lon, lat)
    nodata_val = ds.nodata

    # Check bounds
    if r < 0 or r >= ds.height or c < 0 or c >= ds.width:
        return {
            "elevation_m": np.nan,
            "slope_deg": np.nan,
            "aspect_deg": np.nan,
            "relief_std_5x5_m": np.nan,
            "dem_tile": tile_key,
            "dem_nodata": nodata_val,
            "terrain_quality": "NODATA",
        }

    # Determine 5x5 window boundaries
    r_min = max(0, r - 2)
    r_max = min(ds.height, r + 3)
    c_min = max(0, c - 2)
    c_max = min(ds.width, c + 3)

    is_partial = (r < 2 or r >= ds.height - 2 or c < 2 or c >= ds.width - 2)

    # Read 5x5 (or partial) window
    win_data = ds.read(1, window=((r_min, r_max), (c_min, c_max)))

    # Center pixel offset in the read window
    center_r = r - r_min
    center_c = c - c_min
    center_elev = float(win_data[center_r, center_c])

    # Check nodata at center
    if nodata_val is not None and (center_elev == nodata_val or np.isnan(center_elev)):
        return {
            "elevation_m": np.nan,
            "slope_deg": np.nan,
            "aspect_deg": np.nan,
            "relief_std_5x5_m": np.nan,
            "dem_tile": tile_key,
            "dem_nodata": nodata_val,
            "terrain_quality": "NODATA",
        }

    # 1. Elevation
    elevation_m = center_elev

    # 2. Local Relief 5x5
    if nodata_val is not None:
        valid_cells = win_data[win_data != nodata_val]
    else:
        valid_cells = win_data[~np.isnan(win_data)]

    if len(valid_cells) >= MIN_VALID_CELLS_5X5:
        relief_std = float(np.std(valid_cells, ddof=0))
    else:
        relief_std = np.nan
        is_partial = True

    # 3. Slope and Aspect using Horn's 3x3 method
    # Check if 3x3 fits cleanly inside read window
    if center_r >= 1 and center_r + 1 < win_data.shape[0] and center_c >= 1 and center_c + 1 < win_data.shape[1]:
        w3 = win_data[center_r - 1 : center_r + 2, center_c - 1 : center_c + 2]
    else:
        # Edge case: pad with edge reflection for the 3x3
        pad_top = max(0, 1 - center_r)
        pad_bottom = max(0, (center_r + 2) - win_data.shape[0])
        pad_left = max(0, 1 - center_c)
        pad_right = max(0, (center_c + 2) - win_data.shape[1])
        padded = np.pad(win_data, ((pad_top, pad_bottom), (pad_left, pad_right)), mode="edge")
        pr = center_r + pad_top
        pc = center_c + pad_left
        w3 = padded[pr - 1 : pr + 2, pc - 1 : pc + 2]
        is_partial = True

    # Check for nodata inside 3x3
    if nodata_val is not None and (w3 == nodata_val).any():
        is_partial = True
        # If center is valid but neighbors have nodata, replace nodata with center elevation
        w3 = np.where(w3 == nodata_val, center_elev, w3)

    # Pixel dimensions in metres
    dlon_deg = float(ds.res[0])
    dlat_deg = float(ds.res[1])
    dx = dlon_deg * METRES_PER_DEGREE_LAT * math.cos(math.radians(lat))
    dy = dlat_deg * METRES_PER_DEGREE_LAT

    # Horn's partial derivatives
    # w3 layout:
    # [0,0]=NW, [0,1]=N, [0,2]=NE
    # [1,0]=W,  [1,1]=C, [1,2]=E
    # [2,0]=SW, [2,1]=S, [2,2]=SE
    p = ((w3[0, 2] + 2.0 * w3[1, 2] + w3[2, 2]) - (w3[0, 0] + 2.0 * w3[1, 0] + w3[2, 0])) / (8.0 * dx)
    q = ((w3[0, 0] + 2.0 * w3[0, 1] + w3[0, 2]) - (w3[2, 0] + 2.0 * w3[2, 1] + w3[2, 2])) / (8.0 * dy)

    slope_rad = math.atan(math.sqrt(p * p + q * q))
    slope_deg = math.degrees(slope_rad)

    # Aspect calculation: compass direction of downhill gradient (-p, -q)
    # 0 = North, 90 = East, 180 = South, 270 = West
    if p == 0.0 and q == 0.0:
        aspect_deg = np.nan
    else:
        aspect_deg = math.degrees(math.atan2(-p, -q))
        if aspect_deg < 0.0:
            aspect_deg += 360.0
        if aspect_deg >= 360.0:
            aspect_deg = 0.0

    terrain_quality = "PARTIAL_WINDOW" if is_partial else "OK"

    return {
        "elevation_m": elevation_m,
        "slope_deg": slope_deg,
        "aspect_deg": aspect_deg,
        "relief_std_5x5_m": relief_std,
        "dem_tile": tile_key,
        "dem_nodata": nodata_val,
        "terrain_quality": terrain_quality,
    }


def main():
    log("=" * 80)
    log("PHASE 8E.1 - DEM TERRAIN FEATURE EXTRACTION")
    log("=" * 80)

    start_time = time.time()

    # 1. Verify input CSV
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    log(f"Input dataset:       {INPUT_CSV}")
    log(f"Input row count:     {len(df)}")

    if len(df) != 4016:
        raise ValueError(f"Expected exactly 4,016 samples, found {len(df)}.")

    positives = (df["label"] == 1).sum()
    negatives = (df["label"] == 0).sum()
    log(f"Positive samples:    {positives}")
    log(f"Negative samples:    {negatives}")

    if positives != 2008 or negatives != 2008:
        raise ValueError(f"Expected 2,008 positives and 2,008 negatives. Found {positives} / {negatives}.")

    # 2. Verify all required DEM tiles exist
    required_tiles = set()
    for _, row in df.iterrows():
        key, path = get_tile_info(float(row["latitude"]), float(row["longitude"]))
        required_tiles.add((key, path))

    log(f"\nUnique DEM tiles required by samples: {len(required_tiles)}")
    missing_tiles = [key for key, path in required_tiles if not path.exists()]

    if missing_tiles:
        raise FileNotFoundError(f"Missing required DEM tiles ({len(missing_tiles)}): {missing_tiles}")

    log("All required DEM tiles verified present.")

    # 3. Process samples grouped by DEM tile for maximum efficiency
    df["_temp_tile_key"] = [
        get_tile_info(float(lat), float(lon))[0]
        for lat, lon in zip(df["latitude"], df["longitude"])
    ]

    tile_groups = df.groupby("_temp_tile_key")
    log(f"\nExtracting terrain features across {len(tile_groups)} active DEM tiles...")

    results = {}
    tiles_processed = 0

    for tile_key, group in tile_groups:
        tile_path = DEM_DIR / f"{tile_key}.tif"
        with rasterio.open(tile_path) as ds:
            for idx, row in group.iterrows():
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                feat = extract_features_for_point(ds, lat, lon, tile_key)
                results[idx] = feat

        tiles_processed += 1
        if tiles_processed % 10 == 0 or tiles_processed == len(tile_groups):
            log(f"  Processed {tiles_processed}/{len(tile_groups)} tiles...")

    df.drop(columns=["_temp_tile_key"], inplace=True)

    # 4. Attach extracted features
    feature_df = pd.DataFrame.from_dict(results, orient="index")

    for col in [
        "elevation_m",
        "slope_deg",
        "aspect_deg",
        "relief_std_5x5_m",
        "dem_tile",
        "dem_nodata",
        "terrain_quality",
    ]:
        df[col] = feature_df[col]

    elapsed = time.time() - start_time
    log(f"\nFeature extraction completed in {elapsed:.2f} seconds.")

    # 5. Validation & Integrity Checks
    log("\n" + "=" * 80)
    log("VALIDATION & INTEGRITY SUMMARY")
    log("=" * 80)

    # Check unchanged rows
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

    # Quality distribution
    quality_counts = df["terrain_quality"].value_counts().to_dict()
    log(f"\nTerrain quality distribution: {quality_counts}")

    # Feature statistics
    stats = {}
    for feat in ["elevation_m", "slope_deg", "aspect_deg", "relief_std_5x5_m"]:
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

    # 6. Save atomically
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tmp_csv = OUTPUT_CSV.with_suffix(".csv.tmp")
    df.to_csv(tmp_csv, index=False)
    tmp_csv.replace(OUTPUT_CSV)

    report = {
        "status": "PASS",
        "dataset_name": "Landslide Training Samples with DEM Terrain Features",
        "dem_source": "Copernicus DEM GLO-30 Public (30m nominal COG)",
        "dem_product_type": "Digital Surface Model (DSM)",
        "input_file": str(INPUT_CSV),
        "output_file": str(OUTPUT_CSV),
        "total_samples": len(df),
        "positive_samples": int((df["label"] == 1).sum()),
        "negative_samples": int((df["label"] == 0).sum()),
        "integrity_checks": {
            "row_count_preserved": len(df) == 4016,
            "coordinate_changes": int(coord_diff),
            "label_changes": int(label_diff),
            "slide_no_changes": int(slide_no_diff),
            "duplicate_rows": int(dup_rows),
        },
        "terrain_quality_counts": quality_counts,
        "feature_statistics": stats,
        "notes": [
            "Elevation source is Copernicus DEM GLO-30 Public (DSM).",
            "Slope is computed using Horn's 3x3 algorithm with metric dx and dy scaled by latitude.",
            "Aspect is compass azimuth 0-360 deg (0=North, 90=East, 180=South, 270=West). Flat slopes stored as NaN.",
            "Relief is population standard deviation (ddof=0) across a 5x5 window.",
            "All base landslide inventory attributes, IDs, coordinates, and labels are 100% preserved.",
        ],
    }

    tmp_json = REPORT_JSON.with_suffix(".json.tmp")
    tmp_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    tmp_json.replace(REPORT_JSON)

    log(f"\nSaved terrain-enriched CSV: {OUTPUT_CSV}")
    log(f"Saved audit report:         {REPORT_JSON}")
    log("\nPhase 8E.1 terrain extraction PASSED.")


if __name__ == "__main__":
    main()
