"""
Phase 8E.2.1 - Soil Feature Extraction from ISRIC SoilGrids v2.0
================================================================
Source:
  Official ISRIC SoilGrids 2020 v2.0 (250m global mosaics)
  URL: https://files.isric.org/soilgrids/latest/data/

Extracted Soil Variables:
  - soil_class: WRB (World Reference Base) Most Probable Reference Soil Group
  - clay_percent: Clay content (0-2 µm) at 0-5 cm depth (%)
  - sand_percent: Sand content (50-2000 µm) at 0-5 cm depth (%)
  - silt_percent: Silt content (2-50 µm) at 0-5 cm depth (%)
  - bulk_density_kg_dm3: Bulk density of fine earth fraction at 0-5 cm depth (kg/dm3)
  - soil_quality: Quality flag ("OK" or "MISSING" for water/nodata)

Strict Preservation:
  - 4,016 samples (2,008 positive Bhuvan landslides, 2,008 GADM ADM1 spatial negatives)
  - 0 coordinate alterations, 0 label changes, 0 duplicate rows
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer

# ==============================================================================
# CONFIGURATION & PATHS
# ==============================================================================

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

RAW_SOIL_DIR = PROJECT_ROOT / "data" / "raw" / "soil"

# SoilGrids VRT Endpoints
VRT_BASE = "https://files.isric.org/soilgrids/latest/data"

SOIL_LAYERS = {
    "clay": {
        "url": f"/vsicurl/{VRT_BASE}/clay/clay_0-5cm_mean.vrt",
        "local_tif": RAW_SOIL_DIR / "clay_0-5cm_mean_nei.tif",
        "d_factor": 10.0,
        "round_digits": 2,
        "col_name": "clay_percent",
        "nodata_val": -32768,
        "is_homolosine": True,
    },
    "sand": {
        "url": f"/vsicurl/{VRT_BASE}/sand/sand_0-5cm_mean.vrt",
        "local_tif": RAW_SOIL_DIR / "sand_0-5cm_mean_nei.tif",
        "d_factor": 10.0,
        "round_digits": 2,
        "col_name": "sand_percent",
        "nodata_val": -32768,
        "is_homolosine": True,
    },
    "silt": {
        "url": f"/vsicurl/{VRT_BASE}/silt/silt_0-5cm_mean.vrt",
        "local_tif": RAW_SOIL_DIR / "silt_0-5cm_mean_nei.tif",
        "d_factor": 10.0,
        "round_digits": 2,
        "col_name": "silt_percent",
        "nodata_val": -32768,
        "is_homolosine": True,
    },
    "bdod": {
        "url": f"/vsicurl/{VRT_BASE}/bdod/bdod_0-5cm_mean.vrt",
        "local_tif": RAW_SOIL_DIR / "bdod_0-5cm_mean_nei.tif",
        "d_factor": 100.0,
        "round_digits": 3,
        "col_name": "bulk_density_kg_dm3",
        "nodata_val": -32768,
        "is_homolosine": True,
    },
    "wrb": {
        "url": f"/vsicurl/{VRT_BASE}/wrb/MostProbable.vrt",
        "local_tif": RAW_SOIL_DIR / "wrb_most_probable_nei.tif",
        "col_name": "soil_class",
        "nodata_val": 255,
        "is_homolosine": False,
    },
}

# Official WRB 30-class thematic mapping from MostProbable.vrt
WRB_CLASS_MAP = {
    0: "Acrisols",
    1: "Albeluvisols",
    2: "Alisols",
    3: "Andosols",
    4: "Arenosols",
    5: "Calcisols",
    6: "Cambisols",
    7: "Chernozems",
    8: "Cryosols",
    9: "Durisols",
    10: "Ferralsols",
    11: "Fluvisols",
    12: "Gleysols",
    13: "Gypsisols",
    14: "Histosols",
    15: "Kastanozems",
    16: "Leptosols",
    17: "Lixisols",
    18: "Luvisols",
    19: "Nitisols",
    20: "Phaeozems",
    21: "Planosols",
    22: "Plinthosols",
    23: "Podzols",
    24: "Regosols",
    25: "Solonchaks",
    26: "Solonetz",
    27: "Stagnosols",
    28: "Umbrisols",
    29: "Vertisols",
}


def log(msg=""):
    print(msg, flush=True)


def acquire_regional_tif(layer_key: str, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Path:
    """Download/crop the Northeast India region raster from ISRIC VRT if not locally cached."""
    cfg = SOIL_LAYERS[layer_key]
    out_tif = cfg["local_tif"]
    if out_tif.exists() and out_tif.stat().st_size > 100_000:
        log(f"  [OK] Found local cached raster: {out_tif.name} ({out_tif.stat().st_size / (1024*1024):.2f} MB)")
        return out_tif

    log(f"  Fetching {layer_key} window from remote VRT: {cfg['url']}...")
    t0 = time.time()
    RAW_SOIL_DIR.mkdir(parents=True, exist_ok=True)

    with rasterio.open(cfg["url"]) as src:
        if cfg["is_homolosine"]:
            trans = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            xs, ys = trans.transform([min_lon, max_lon, min_lon, max_lon], [min_lat, min_lat, max_lat, max_lat])
            b_min_x, b_max_x = min(xs), max(xs)
            b_min_y, b_max_y = min(ys), max(ys)
            window = from_bounds(b_min_x, b_min_y, b_max_x, b_max_y, transform=src.transform)
        else:
            window = from_bounds(min_lon, min_lat, max_lon, max_lat, transform=src.transform)

        data = src.read(1, window=window)
        win_transform = rasterio.windows.transform(window, src.transform)

        meta = src.meta.copy()
        meta.update({
            "driver": "GTiff",
            "height": data.shape[0],
            "width": data.shape[1],
            "transform": win_transform,
            "compress": "deflate",
            "predictor": 2 if cfg["is_homolosine"] else 1,
        })

        tmp_tif = out_tif.with_suffix(".tif.tmp")
        with rasterio.open(tmp_tif, "w", **meta) as dst:
            dst.write(data, 1)
        tmp_tif.replace(out_tif)

    size_mb = out_tif.stat().st_size / (1024 * 1024)
    log(f"  [OK] Saved regional GeoTIFF {out_tif.name} ({size_mb:.2f} MB) in {time.time()-t0:.2f}s")
    return out_tif


def sample_raster_points(tif_path: Path, lons: np.ndarray, lats: np.ndarray, is_homolosine: bool) -> np.ndarray:
    """Sample points from a local GeoTIFF."""
    with rasterio.open(tif_path) as src:
        if is_homolosine:
            trans = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            xs, ys = trans.transform(lons, lats)
            pts = list(zip(xs, ys))
        else:
            pts = list(zip(lons, lats))
        vals = np.array([v[0] for v in src.sample(pts)])
    return vals


def main():
    log("=" * 80)
    log("PHASE 8E.2.1 - SOIL FEATURE EXTRACTION (ISRIC SOILGRIDS v2.0)")
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

    # Compute study area bounding box with 0.1 degree buffer
    min_lon = float(df["longitude"].min() - 0.1)
    min_lat = float(df["latitude"].min() - 0.1)
    max_lon = float(df["longitude"].max() + 0.1)
    max_lat = float(df["latitude"].max() + 0.1)
    log(f"Study area extent:   [{min_lon:.4f}, {min_lat:.4f}] to [{max_lon:.4f}, {max_lat:.4f}]")

    # 2. Acquire regional rasters
    log("\nAcquiring / verifying regional SoilGrids rasters (250m)...")
    for key in ["clay", "sand", "silt", "bdod", "wrb"]:
        acquire_regional_tif(key, min_lon, min_lat, max_lon, max_lat)

    # 3. Sample all layers for 4,016 coordinates
    log("\nSampling soil layers at sample coordinates...")
    lons = df["longitude"].values
    lats = df["latitude"].values

    # Physical properties
    raw_samples = {}
    for key in ["clay", "sand", "silt", "bdod"]:
        cfg = SOIL_LAYERS[key]
        vals = sample_raster_points(cfg["local_tif"], lons, lats, cfg["is_homolosine"])
        raw_samples[key] = vals
        log(f"  Sampled {key.upper()}: {len(vals)} points (raw min={vals.min()}, max={vals.max()})")

    # Classification
    wrb_cfg = SOIL_LAYERS["wrb"]
    raw_wrb = sample_raster_points(wrb_cfg["local_tif"], lons, lats, wrb_cfg["is_homolosine"])
    log(f"  Sampled WRB: {len(raw_wrb)} points (raw unique={len(set(raw_wrb))})")

    # 4. Map values and create features
    log("\nProcessing feature columns and quality flags...")
    
    # Check for nodata
    clay_raw = raw_samples["clay"]
    sand_raw = raw_samples["sand"]
    silt_raw = raw_samples["silt"]
    bdod_raw = raw_samples["bdod"]

    is_missing = (
        (clay_raw == SOIL_LAYERS["clay"]["nodata_val"])
        | (sand_raw == SOIL_LAYERS["sand"]["nodata_val"])
        | (silt_raw == SOIL_LAYERS["silt"]["nodata_val"])
        | (bdod_raw == SOIL_LAYERS["bdod"]["nodata_val"])
        | (raw_wrb == SOIL_LAYERS["wrb"]["nodata_val"])
    )

    soil_classes = [
        WRB_CLASS_MAP.get(int(code), None) if code != SOIL_LAYERS["wrb"]["nodata_val"] else None
        for code in raw_wrb
    ]

    df["soil_class"] = soil_classes
    df["clay_percent"] = np.where(clay_raw != -32768, np.round(clay_raw / 10.0, 2), np.nan)
    df["sand_percent"] = np.where(sand_raw != -32768, np.round(sand_raw / 10.0, 2), np.nan)
    df["silt_percent"] = np.where(silt_raw != -32768, np.round(silt_raw / 10.0, 2), np.nan)
    df["bulk_density_kg_dm3"] = np.where(bdod_raw != -32768, np.round(bdod_raw / 100.0, 3), np.nan)
    df["soil_quality"] = np.where(is_missing, "MISSING", "OK")

    # 5. Strict Preservation & Integrity Checks
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

    # Scientific comparison: Landslides vs Negatives
    log("\n" + "=" * 80)
    log("SCIENTIFIC FEATURE SEPARATION: LANDSLIDES (1) vs NEGATIVES (0)")
    log("=" * 80)
    for feat in ["clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3"]:
        mean_pos = df[df["label"] == 1][feat].mean()
        mean_neg = df[df["label"] == 0][feat].mean()
        log(f"{feat:22s} | Landslides: {mean_pos:.2f} | Spatial Negatives: {mean_neg:.2f}")

    # 6. Save output CSV atomically
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_csv = OUTPUT_CSV.with_suffix(".csv.tmp")
    df.to_csv(tmp_csv, index=False)
    tmp_csv.replace(OUTPUT_CSV)

    # 7. Save audit report
    report = {
        "status": "PASS",
        "dataset_name": "Landslide Training Samples with SoilGrids Features",
        "source": "ISRIC SoilGrids 2020 v2.0 (250m resolution)",
        "source_base_url": VRT_BASE,
        "extraction_timestamp_utc": extraction_timestamp,
        "input_file": str(INPUT_CSV),
        "output_file": str(OUTPUT_CSV),
        "input_rows": len(original_df),
        "output_rows": len(df),
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
        "feature_separation_by_label": {
            feat: {
                "landslide_mean": float(df[df["label"] == 1][feat].mean()),
                "negative_mean": float(df[df["label"] == 0][feat].mean()),
            }
            for feat in ["clay_percent", "sand_percent", "silt_percent", "bulk_density_kg_dm3"]
        },
        "top_wrb_soil_classes": {str(k): int(v) for k, v in class_counts.items()},
        "scientific_notes": [
            "Soil data extracted from ISRIC SoilGrids 2020 v2.0 (250m resolution).",
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
    log(f"Total pipeline elapsed:   {time.time()-start_time:.2f}s")
    log("\nPhase 8E.2.1 soil extraction PASSED.")


if __name__ == "__main__":
    main()
