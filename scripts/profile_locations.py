"""
Batch Location Profiler for Static Landslide Susceptibility
===========================================================
Profiles batches of geographic coordinates from a CSV file and writes
complete static susceptibility outputs to an output CSV.

Usage:
    python scripts/profile_locations.py --input <input.csv> [--output <output.csv>] [--limit N]
"""

import sys
import time
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.location_profiler import LocationProfiler

DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "inference" / "location_profiles.csv"


def profile_batch(input_path: Path, output_path: Path, limit: int = None) -> pd.DataFrame:
    """Run batch location profiling on an input CSV with latitude and longitude columns."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df_in = pd.read_csv(input_path)

    # Normalize column names
    lat_col = None
    lon_col = None
    for c in df_in.columns:
        if c.lower() in ["latitude", "lat", "y"]:
            lat_col = c
        elif c.lower() in ["longitude", "lon", "lng", "x"]:
            lon_col = c

    if not lat_col or not lon_col:
        raise ValueError(
            f"Input CSV must contain latitude and longitude columns. Found: {list(df_in.columns)}"
        )

    if limit is not None and limit > 0:
        df_in = df_in.head(limit)

    total_rows = len(df_in)
    print(f"Starting batch profiling for {total_rows} coordinates...")
    t0 = time.time()

    profiler = LocationProfiler()
    results = []

    try:
        for idx, row in df_in.iterrows():
            lat = float(row[lat_col])
            lon = float(row[lon_col])

            res = profiler.profile_location(lat, lon)

            if res.get("status") == "OUTSIDE_SUPPORTED_DOMAIN":
                record = {
                    "latitude": lat,
                    "longitude": lon,
                    "state": "OUTSIDE_NER",
                    "elevation_m": np.nan,
                    "slope_deg": np.nan,
                    "aspect_deg": np.nan,
                    "relief_std_5x5_m": np.nan,
                    "soil_class": "UNKNOWN",
                    "clay_percent": np.nan,
                    "sand_percent": np.nan,
                    "silt_percent": np.nan,
                    "bulk_density_kg_dm3": np.nan,
                    "landcover_class": "UNKNOWN",
                    "susceptibility_score": np.nan,
                    "susceptibility_category": "OUTSIDE_DOMAIN",
                    "quality_status": "OUTSIDE_DOMAIN",
                }
            else:
                loc = res["location"]
                terrain = res["terrain"]
                soil = res["soil"]
                lulc = res["landcover"]
                susc = res["susceptibility"]
                qual = res["quality"]

                record = {
                    "latitude": lat,
                    "longitude": lon,
                    "state": loc["state"],
                    "elevation_m": terrain["elevation_m"],
                    "slope_deg": terrain["slope_deg"],
                    "aspect_deg": terrain["aspect_deg"],
                    "relief_std_5x5_m": terrain["relief_std_5x5_m"],
                    "soil_class": soil["soil_class"],
                    "clay_percent": soil["clay_percent"],
                    "sand_percent": soil["sand_percent"],
                    "silt_percent": soil["silt_percent"],
                    "bulk_density_kg_dm3": soil["bulk_density_kg_dm3"],
                    "landcover_class": lulc["landcover_class"],
                    "susceptibility_score": susc["score"],
                    "susceptibility_category": susc["category"],
                    "quality_status": qual["status"],
                }

            results.append(record)

            if (idx + 1) % 50 == 0 or (idx + 1) == total_rows:
                elapsed = time.time() - t0
                rate = (idx + 1) / elapsed
                print(f"  Processed {idx + 1}/{total_rows} locations ({rate:.1f} loc/sec)...")
    finally:
        profiler.close()

    df_out = pd.DataFrame(results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False)
    elapsed_total = time.time() - t0
    print(f"[OK] Batch profiling complete! Saved {len(df_out)} rows to {output_path} in {elapsed_total:.2f}s")
    return df_out


def main():
    parser = argparse.ArgumentParser(description="Batch profile coordinates for static susceptibility.")
    parser.add_argument("--input", type=str, required=True, help="Path to input CSV containing latitude/longitude")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_CSV), help="Path to output CSV")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of rows to process")

    args = parser.parse_args()

    profile_batch(Path(args.input), Path(args.output), args.limit)


if __name__ == "__main__":
    main()
