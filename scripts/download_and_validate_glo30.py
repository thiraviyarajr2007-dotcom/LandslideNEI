from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import rasterio
import requests

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEST_DIR = PROJECT_ROOT / "data" / "raw" / "dem" / "copernicus_glo30" / "downloads"
REPORT_FILE = PROJECT_ROOT / "data" / "raw" / "dem" / "copernicus_glo30" / "dem_acquisition_report.json"

BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com/"

REQUIRED_TILES = [
    "N21_E092",
    "N22_E092", "N22_E093",
    "N23_E091", "N23_E092", "N23_E093", "N23_E094",
    "N24_E091", "N24_E092", "N24_E093", "N24_E094",
    "N25_E089", "N25_E090", "N25_E091", "N25_E092", "N25_E093", "N25_E094",
    "N26_E089", "N26_E090", "N26_E091", "N26_E092", "N26_E093", "N26_E094", "N26_E095",
    "N27_E088", "N27_E091", "N27_E092", "N27_E093", "N27_E094", "N27_E095", "N27_E096", "N27_E097",
    "N28_E092", "N28_E093", "N28_E094", "N28_E095", "N28_E096", "N28_E097",
    "N29_E094", "N29_E095", "N29_E096",
]

MAX_WORKERS = 4
MAX_RETRIES = 5
CHUNK_SIZE = 1024 * 1024  # 1 MB


def get_tile_url_and_filename(tile_id: str) -> tuple[str, str]:
    parts = tile_id.split("_")
    lat_str = f"{parts[0]}_00"
    lon_str = f"{parts[1]}_00"
    key = f"Copernicus_DSM_COG_10_{lat_str}_{lon_str}_DEM"
    filename = f"{key}.tif"
    url = f"{BASE_URL}{key}/{filename}"
    return url, filename


def download_single_tile(tile_id: str) -> dict:
    url, filename = get_tile_url_and_filename(tile_id)
    target_path = DEST_DIR / filename
    tmp_path = DEST_DIR / f"{filename}.tmp"

    result = {
        "tile_id": tile_id,
        "filename": filename,
        "url": url,
        "status": "PENDING",
        "http_status": None,
        "bytes_downloaded": 0,
        "error": None,
    }

    # If already downloaded and valid, skip
    if target_path.exists() and target_path.stat().st_size > 1000:
        try:
            with rasterio.open(target_path) as src:
                if src.width == 3600 and src.height == 3600:
                    result["status"] = "ALREADY_EXISTS"
                    result["http_status"] = 200
                    result["bytes_downloaded"] = target_path.stat().st_size
                    print(f"[{tile_id}] Already exists and valid ({result['bytes_downloaded'] / (1024*1024):.1f} MB)", flush=True)
                    return result
        except Exception:
            pass  # Re-download if corrupted

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                result["http_status"] = r.status_code
                if r.status_code == 404:
                    result["status"] = "NOT_FOUND_404"
                    result["error"] = f"HTTP 404 Not Found at {url}"
                    print(f"[{tile_id}] ERROR 404: Tile not found at {url}", flush=True)
                    return result

                r.raise_for_status()

                total_length = int(r.headers.get("content-length", 0))
                downloaded = 0

                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                if total_length > 0 and downloaded != total_length:
                    raise IOError(f"Incomplete download: {downloaded}/{total_length} bytes")

                # Atomic rename
                if tmp_path.exists():
                    tmp_path.replace(target_path)

                result["status"] = "DOWNLOADED"
                result["bytes_downloaded"] = downloaded
                print(f"[{tile_id}] Downloaded successfully ({downloaded / (1024*1024):.1f} MB)", flush=True)
                return result

        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            if attempt < MAX_RETRIES:
                wait_sec = attempt * 3
                print(f"[{tile_id}] Attempt {attempt} failed: {e}. Retrying in {wait_sec}s...", flush=True)
                time.sleep(wait_sec)
            else:
                result["status"] = "FAILED"
                result["error"] = str(e)
                print(f"[{tile_id}] FAILED after {MAX_RETRIES} attempts: {e}", flush=True)
                return result

    return result


def validate_single_raster(tile_id: str, filepath: Path) -> dict:
    info = {
        "tile_id": tile_id,
        "filename": filepath.name,
        "filepath": str(filepath),
        "file_size_bytes": filepath.stat().st_size if filepath.exists() else 0,
        "readable_by_rasterio": False,
        "crs": None,
        "width": None,
        "height": None,
        "resolution": None,
        "bounds": None,
        "dtype": None,
        "nodata": None,
        "min_elevation_m": None,
        "max_elevation_m": None,
        "error": None,
    }

    if not filepath.exists():
        info["error"] = "File does not exist on disk"
        return info

    try:
        with rasterio.open(filepath) as ds:
            info["readable_by_rasterio"] = True
            info["crs"] = str(ds.crs)
            info["width"] = ds.width
            info["height"] = ds.height
            info["resolution"] = [float(res) for res in ds.res]
            info["bounds"] = [float(b) for b in ds.bounds]
            info["dtype"] = str(ds.dtypes[0])
            info["nodata"] = float(ds.nodata) if ds.nodata is not None else None

            # Read first band and compute min/max excluding nodata
            data = ds.read(1, masked=True)
            info["min_elevation_m"] = float(data.min()) if data.count() > 0 else None
            info["max_elevation_m"] = float(data.max()) if data.count() > 0 else None

    except Exception as e:
        info["error"] = str(e)

    return info


def main():
    print("=" * 80)
    print("COPERNICUS DEM GLO-30 PUBLIC COG (30M) DOWNLOAD AND VALIDATION PIPELINE")
    print("=" * 80)
    print(f"Target directory: {DEST_DIR}")
    print(f"Total tiles requested: {len(REQUIRED_TILES)}")
    print()

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # Step 1: Download tiles
    print("Starting download of 41 tiles (ThreadPoolExecutor max_workers=4)...")
    download_results = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_tile = {
            executor.submit(download_single_tile, tile_id): tile_id
            for tile_id in REQUIRED_TILES
        }
        for future in as_completed(future_to_tile):
            res = future.result()
            download_results[res["tile_id"]] = res

    elapsed_download = time.time() - start_time
    print(f"\nDownload phase finished in {elapsed_download:.1f} seconds.")

    # Check for any failures
    failed_downloads = [
        res for res in download_results.values()
        if res["status"] not in ("DOWNLOADED", "ALREADY_EXISTS")
    ]

    if failed_downloads:
        print("\nERROR: One or more tiles failed to download:")
        for f in failed_downloads:
            print(f"  - {f['tile_id']}: {f['status']} | {f['error']}")
        sys.exit(1)

    # Step 2: Rasterio Integrity Check
    print("\n" + "=" * 80)
    print("RUNNING RASTERIO INTEGRITY VALIDATION")
    print("=" * 80)

    validation_results = []
    total_bytes = 0
    unreadable_files = []

    print(f"{'TILE':<10} {'FILENAME':<44} {'SIZE (MB)':<10} {'CRS':<10} {'DIMS':<12} {'ELEV MIN (m)':<13} {'ELEV MAX (m)':<13}")
    print("-" * 115)

    for tile_id in sorted(REQUIRED_TILES):
        _, filename = get_tile_url_and_filename(tile_id)
        filepath = DEST_DIR / filename
        v = validate_single_raster(tile_id, filepath)
        validation_results.append(v)

        total_bytes += v["file_size_bytes"]

        if not v["readable_by_rasterio"]:
            unreadable_files.append(v)
            print(f"{tile_id:<10} {filename:<44} {'ERROR':<10} {'UNREADABLE':<10} {'N/A':<12} {'N/A':<13} {'N/A':<13}")
        else:
            dims = f"{v['width']}x{v['height']}"
            size_mb = f"{v['file_size_bytes'] / (1024*1024):.1f}"
            emin = f"{v['min_elevation_m']:.1f}" if v['min_elevation_m'] is not None else "None"
            emax = f"{v['max_elevation_m']:.1f}" if v['max_elevation_m'] is not None else "None"
            print(f"{tile_id:<10} {filename:<44} {size_mb:<10} {v['crs']:<10} {dims:<12} {emin:<13} {emax:<13}")

    # Check for missing tiles
    downloaded_filenames = {f.name for f in DEST_DIR.glob("*.tif")}
    expected_filenames = {get_tile_url_and_filename(t)[1] for t in REQUIRED_TILES}
    missing = expected_filenames - downloaded_filenames
    duplicates = len(downloaded_filenames) - len(expected_filenames) if len(downloaded_filenames) > len(expected_filenames) else 0

    print("\n" + "=" * 80)
    print("INTEGRITY SUMMARY")
    print("=" * 80)
    print(f"Total required tiles:       {len(REQUIRED_TILES)}")
    print(f"Total downloaded TIFFs:     {len(downloaded_filenames)}")
    print(f"Total downloaded bytes:     {total_bytes:,} bytes ({total_bytes / (1024**3):.2f} GB)")
    print(f"Missing tiles:              {len(missing)}")
    print(f"Duplicate tiles:            {duplicates}")
    print(f"Unreadable files:           {len(unreadable_files)}")

    report_data = {
        "status": "PASS" if len(missing) == 0 and len(unreadable_files) == 0 else "FAIL",
        "dataset": "Copernicus DEM GLO-30 Public (30m COG)",
        "source_url": BASE_URL,
        "destination": str(DEST_DIR),
        "total_required_tiles": len(REQUIRED_TILES),
        "total_downloaded_tiffs": len(downloaded_filenames),
        "total_downloaded_bytes": total_bytes,
        "total_downloaded_gb": round(total_bytes / (1024**3), 3),
        "missing_tiles": list(missing),
        "unreadable_files": [u["filename"] for u in unreadable_files],
        "tiles": validation_results,
    }

    REPORT_FILE.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"\nAudit report saved to: {REPORT_FILE}")

    if len(missing) == 0 and len(unreadable_files) == 0:
        print("\nSUCCESS: All 41 Copernicus GLO-30 DEM tiles downloaded and verified.")
    else:
        print("\nFAILURE: Some tiles failed verification.")
        sys.exit(1)


if __name__ == "__main__":
    main()
