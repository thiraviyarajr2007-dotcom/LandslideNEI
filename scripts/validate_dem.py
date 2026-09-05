#!/usr/bin/env python3
"""Validate Copernicus GLO-30 rasters and training-sample spatial coverage."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer

EXPECTED_STATES = ["AR", "AS", "MN", "ML", "MZ", "NL", "SK", "TR"]


def raster_files(root: Path) -> list[Path]:
    return sorted([*root.rglob("*.tif"), *root.rglob("*.tiff")])


def is_approximately_30m(resolution: tuple[float, float], crs) -> bool:
    x, y = abs(resolution[0]), abs(resolution[1])
    if crs and crs.is_geographic:
        # 1 arc-second is approximately 30.9 m at the equator and less by latitude.
        return 0.00015 <= x <= 0.00035 and 0.00015 <= y <= 0.00035
    return 20 <= x <= 40 and 20 <= y <= 40


def raster_summary(path: Path) -> dict:
    try:
        with rasterio.open(path) as ds:
            if ds.count < 1:
                raise ValueError("raster has no bands")
            if ds.crs is None:
                raise ValueError("CRS is missing")
            if not is_approximately_30m(ds.res, ds.crs):
                raise ValueError(f"resolution {ds.res} is not approximately 30 m")
            if max(abs(v) for v in ds.res) > 0.001:
                raise ValueError("resolution suggests 90 m or coarser data")
            band = ds.read(1, masked=True)
            mask = np.ma.getmaskarray(band)
            valid = int(mask.size - mask.sum())
            nodata = int(mask.sum())
            min_elev = float(band.min()) if valid else None
            max_elev = float(band.max()) if valid else None
            return {
                "filename": str(path),
                "crs": ds.crs.to_string(),
                "width": ds.width,
                "height": ds.height,
                "pixel_resolution": [float(ds.res[0]), float(ds.res[1])],
                "bounds": [float(ds.bounds.left), float(ds.bounds.bottom), float(ds.bounds.right), float(ds.bounds.top)],
                "nodata": None if ds.nodata is None else float(ds.nodata),
                "dtype": ds.dtypes[0],
                "minimum_elevation_m": min_elev,
                "maximum_elevation_m": max_elev,
                "valid_pixels": valid,
                "nodata_pixels": nodata,
            }
    except Exception as exc:
        raise RuntimeError(f"cannot validate {path}: {exc}") from exc


def point_in_bounds(lon: float, lat: float, summary: dict) -> bool:
    left, bottom, right, top = summary["bounds"]
    return left <= lon <= right and bottom <= lat <= top


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem-dir", type=Path, default=Path("data/raw/dem/copernicus_glo30"))
    ap.add_argument("--samples", type=Path, default=Path("data/processed/landslides/landslide_training_samples_gadm_corrected.csv"))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    files = raster_files(args.dem_dir)
    if not files:
        raise RuntimeError(f"no GeoTIFF DEM files exist under {args.dem_dir}")
    df = pd.read_csv(args.samples)
    required = {"latitude", "longitude"}
    if not required.issubset(df.columns):
        raise RuntimeError(f"samples must contain {sorted(required)}")

    rasters = [raster_summary(p) for p in files]
    crs_set = {r["crs"] for r in rasters}
    transformer = None
    if crs_set != {"EPSG:4326"}:
        # Coverage checks are performed in the raster CRS when needed.
        transformer = {crs: Transformer.from_crs("EPSG:4326", crs, always_xy=True) for crs in crs_set}

    covered = []
    for _, row in df.iterrows():
        lon, lat = float(row.longitude), float(row.latitude)
        hit = False
        for r in rasters:
            x, y = lon, lat
            if r["crs"] != "EPSG:4326":
                x, y = transformer[r["crs"]].transform(lon, lat)
            left, bottom, right, top = r["bounds"]
            if left <= x <= right and bottom <= y <= top:
                hit = True
                break
        covered.append(hit)

    df["covered_by_dem"] = covered
    outside = df.loc[~df.covered_by_dem].copy()
    by_state = {}
    for state in EXPECTED_STATES:
        part = df[df["state_code"].astype(str) == state] if "state_code" in df else df.iloc[0:0]
        by_state[state] = {"total": int(len(part)), "covered": int(part.covered_by_dem.sum()), "outside": int((~part.covered_by_dem).sum())}

    all_bounds = [r["bounds"] for r in rasters]
    extent = [min(b[0] for b in all_bounds), min(b[1] for b in all_bounds), max(b[2] for b in all_bounds), max(b[3] for b in all_bounds)]
    result = {
        "validation_date": date.today().isoformat(),
        "dataset": "Copernicus DEM GLO-30 Public / COP-DEM_GLO-30-DGED",
        "resolution": "30 m nominal (10 arc-second COG)",
        "elevation_units": "metres",
        "raster_count": len(rasters),
        "dem_extent": extent,
        "rasters": rasters,
        "samples": {"total": int(len(df)), "covered": int(sum(covered)), "outside": int(len(df) - sum(covered)), "by_state": by_state},
        "outside_samples": df.loc[~df.covered_by_dem, [c for c in ["sample_id", "state_code", "latitude", "longitude"] if c in df]].to_dict("records"),
        "validation_status": "PASS" if not outside.shape[0] else "FAIL_SAMPLES_OUTSIDE_DEM",
    }
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not outside.shape[0] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"VALIDATION ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
