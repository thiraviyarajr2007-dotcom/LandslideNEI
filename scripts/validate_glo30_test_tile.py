#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import rasterio


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tile", type=Path)
    ap.add_argument("--url", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    head = subprocess.run(["curl", "-sS", "-L", "-o", "/dev/null", "-w", "%{http_code}", args.url], check=True, capture_output=True, text=True)
    with rasterio.open(args.tile) as ds:
        arr = ds.read(1, masked=True)
        mask = np.ma.getmaskarray(arr)
        summary = {
            "validation_date": date.today().isoformat(),
            "source_url": args.url,
            "http_status": int(head.stdout.strip()),
            "file_exists": args.tile.exists(),
            "filename": str(args.tile),
            "file_size_bytes": args.tile.stat().st_size,
            "dataset": "Copernicus GLO-30 Public COG / COP-DEM_GLO-30-DGED",
            "product_type": "Digital Surface Model (DSM), not bare-earth DTM",
            "crs": ds.crs.to_string() if ds.crs else None,
            "width": ds.width,
            "height": ds.height,
            "pixel_resolution": [float(ds.res[0]), float(ds.res[1])],
            "bounds": [float(ds.bounds.left), float(ds.bounds.bottom), float(ds.bounds.right), float(ds.bounds.top)],
            "dtype": ds.dtypes[0],
            "nodata": None if ds.nodata is None else float(ds.nodata),
            "minimum_elevation_m": float(arr.min()),
            "maximum_elevation_m": float(arr.max()),
            "valid_pixel_count": int(mask.size - mask.sum()),
            "nodata_pixel_count": int(mask.sum()),
            "glo30_check": bool(ds.height == 3600 and abs(ds.res[0] - 1 / 3600) < 1e-9 and abs(ds.res[1] - 1 / 3600) < 1e-9),
            "validation_status": "PASS" if head.stdout.strip() == "200" and ds.crs and ds.height == 3600 and abs(ds.res[0] - 1 / 3600) < 1e-9 and abs(ds.res[1] - 1 / 3600) < 1e-9 else "FAIL",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["validation_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
