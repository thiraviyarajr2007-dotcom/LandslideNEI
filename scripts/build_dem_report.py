#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("validation", type=Path)
    ap.add_argument("--json", type=Path, required=True)
    ap.add_argument("--text", type=Path, required=True)
    args = ap.parse_args()
    v = json.loads(args.validation.read_text(encoding="utf-8"))
    files = [Path(r["filename"]).name for r in v["rasters"]]
    tiles = [name.replace("_DEM_DEM.tif", "_DEM") for name in files]
    report = {
        "source": "Copernicus DEM public COG bucket (AWS Open Data), sourced from COP-DEM_GLO-30-DGED",
        "source_url": "https://copernicus-dem-30m.s3.amazonaws.com/",
        "documentation_url": "https://copernicus-dem-30m.s3.amazonaws.com/readme.html",
        "dataset_name": "Copernicus DEM GLO-30 Public / COP-DEM_GLO-30-DGED",
        "product_type": "Digital Surface Model (DSM), not bare-earth Digital Terrain Model (DTM)",
        "resolution": "30 m nominal; 10 arc-second COG grid",
        "acquisition_method": "Downloaded exact required 1-degree COG objects over HTTPS from the public Copernicus DEM S3 bucket",
        "download_date": date.today().isoformat(),
        "downloaded_file_count": len(files),
        "downloaded_files": files,
        "tile_grid_ids": tiles,
        "crs": sorted({r["crs"] for r in v["rasters"]}),
        "raster_dimensions": sorted({(r["width"], r["height"]) for r in v["rasters"]}),
        "pixel_resolution": sorted({tuple(r["pixel_resolution"]) for r in v["rasters"]}),
        "dem_spatial_extent": v["dem_extent"],
        "nodata_values": sorted({r["nodata"] for r in v["rasters"]}, key=lambda x: str(x)),
        "elevation_units": "metres",
        "raster_validation": v["rasters"],
        "coverage_statistics": v["samples"],
        "validation_status": v["validation_status"],
        "terrain_extraction_performed": False,
        "model_training_performed": False,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    c = report["coverage_statistics"]
    lines = [
        "Copernicus GLO-30 DEM Acquisition Report",
        "=========================================",
        f"Source: {report['source']}",
        f"Dataset: {report['dataset_name']}",
        f"Product type: {report['product_type']}",
        f"Resolution: {report['resolution']}",
        f"Acquisition date: {report['download_date']}",
        f"Files downloaded: {report['downloaded_file_count']}",
        f"CRS: {', '.join(report['crs'])}",
        f"DEM extent [left, bottom, right, top]: {report['dem_spatial_extent']}",
        f"Elevation units: {report['elevation_units']}",
        "",
        "Coverage",
        "--------",
        f"Total samples: {c['total']}",
        f"Covered by DEM: {c['covered']}",
        f"Outside DEM: {c['outside']}",
        "",
        "State coverage",
        "--------------",
    ]
    for state, stats in c["by_state"].items():
        lines.append(f"{state}: total={stats['total']}, covered={stats['covered']}, outside={stats['outside']}")
    lines += ["", f"Validation status: {report['validation_status']}", "Terrain extraction performed: no", "Model training performed: no", ""]
    args.text.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
