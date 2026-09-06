#!/usr/bin/env python3
"""
Batch Landslide Risk Evaluation CLI (Phase 8H)
==============================================
Evaluates operational risk for a batch CSV of locations.

Usage:
    python scripts/evaluate_locations_risk.py --input input.csv --output data/processed/inference/location_risk_profiles.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.risk_engine import RiskEngine

DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "inference" / "location_risk_profiles.csv"


def main():
    parser = argparse.ArgumentParser(description="Batch Operational Landslide Risk Evaluation")
    parser.add_argument("--input", type=str, required=True, help="Input CSV path (must contain latitude, longitude)")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_CSV), help="Output CSV path")
    parser.add_argument("--timestamp", type=str, default=None, help="Observation timestamp")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to process")

    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: Input file {in_path} does not exist.")
        sys.exit(1)

    df = pd.read_csv(in_path)
    if "latitude" not in df.columns or "longitude" not in df.columns:
        print("Error: Input CSV must contain 'latitude' and 'longitude' columns.")
        sys.exit(1)

    if args.limit:
        df = df.head(args.limit)

    print(f"Processing {len(df)} locations for operational risk evaluation...")
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    engine = RiskEngine()
    records = []

    start_t = time.time()
    for idx, row in df.iterrows():
        lat = float(row["latitude"])
        lon = float(row["longitude"])

        eval_res = engine.evaluate_risk(lat, lon, timestamp=args.timestamp)

        if eval_res.get("status") == "SUCCESS":
            susc = eval_res["static_susceptibility"]
            rf = eval_res["rainfall"]
            trig = eval_res["rainfall_trigger"]
            risk = eval_res["risk"]

            rec = {
                "latitude": lat,
                "longitude": lon,
                "state": eval_res["location"]["state"],
                "susceptibility_score": susc["score"],
                "susceptibility_category": susc["category"],
                "rainfall_source": rf.get("source"),
                "rainfall_station": rf.get("station"),
                "rainfall_distance_km": rf.get("distance_km"),
                "rainfall_1h": rf.get("rainfall_1h"),
                "rainfall_24h": rf.get("rainfall_24h"),
                "rainfall_3d": rf.get("rainfall_3d"),
                "rainfall_7d": rf.get("rainfall_7d"),
                "rainfall_quality": rf.get("quality"),
                "rainfall_trigger_level": trig.get("trigger_level"),
                "rainfall_trigger_reasons": "; ".join(r["code"] for r in trig.get("trigger_reasons", [])),
                "imd_macro_source": (rf.get("imd_macro_context") or {}).get("source"),
                "risk_level": risk["risk_level"],
                "operational_fusion_score": risk["operational_fusion_score"],
                "risk_score": risk["risk_score"],
                "risk_reasons": "; ".join(r["code"] for r in risk.get("reasons", [])),
            }
        else:
            rec = {
                "latitude": lat,
                "longitude": lon,
                "state": eval_res.get("location", {}).get("state", "OUTSIDE_NER"),
                "susceptibility_score": None,
                "susceptibility_category": "OUTSIDE_DOMAIN",
                "rainfall_source": None,
                "rainfall_station": None,
                "rainfall_distance_km": None,
                "rainfall_1h": None,
                "rainfall_24h": None,
                "rainfall_3d": None,
                "rainfall_7d": None,
                "rainfall_quality": "OUTSIDE_DOMAIN",
                "rainfall_trigger_level": "NO_DATA",
                "rainfall_trigger_reasons": "OUTSIDE_DOMAIN",
                "imd_macro_source": None,
                "risk_level": "UNKNOWN",
                "operational_fusion_score": None,
                "risk_score": None,
                "risk_reasons": eval_res.get("error", "Location outside domain"),
            }
        records.append(rec)

    out_df = pd.DataFrame(records)
    out_df.to_csv(out_path, index=False)
    elapsed = time.time() - start_t
    print(f"Successfully processed {len(records)} locations in {elapsed:.2f}s ({elapsed/len(records)*1000:.1f} ms/row).")
    print(f"Saved results to: {out_path}")


if __name__ == "__main__":
    main()
