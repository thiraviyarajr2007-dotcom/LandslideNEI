"""
Quality-Control (QC) and Station Analysis Engine for CWC Telemetry Rainfall Datasets.
Vectorized for fast execution across all raw datasets.
"""

from collections import defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

NE_LAT_MIN, NE_LAT_MAX = 21.5, 30.0
NE_LON_MIN, NE_LON_MAX = 88.0, 98.0

CANONICAL_COLUMNS = [
    "SlNo", "Station", "Agency", "State LGD Code", "State",
    "District LGD Code", "District", "Tehsil", "Block", "Village",
    "River", "Basin", "Tributary", "Subtributary", "SubSubtributary",
    "Local River", "Latitude", "Longitude", "Data Acquisition Time",
    "Telemetry Hourly Rainfall (mm)"
]


def calculate_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def run_cwc_qc(root_dir: str = "data/raw/cwc_telemetry_hourly") -> Dict[str, Any]:
    root = Path(root_dir)
    if not root.exists():
        print(f"Error: Directory '{root_dir}' not found.")
        return {}

    csv_paths = sorted(root.rglob("*.csv"))
    print(f"Discovered {len(csv_paths)} raw CWC CSV files under '{root_dir}'.\n")

    # 1. Check duplicate files by SHA256
    hash_to_files: Dict[str, List[str]] = defaultdict(list)
    file_hashes: Dict[str, str] = {}
    for p in csv_paths:
        h = calculate_sha256(p)
        hash_to_files[h].append(str(p))
        file_hashes[str(p)] = h

    duplicate_files = [paths for paths in hash_to_files.values() if len(paths) > 1]

    # 2. Audit each file
    file_reports: List[Dict[str, Any]] = []
    loaded_dfs: List[pd.DataFrame] = []

    for path in csv_paths:
        file_size = path.stat().st_size
        rel_path = str(path)

        try:
            df = pd.read_csv(path)
        except Exception as exc:
            file_reports.append({
                "file": rel_path,
                "size_bytes": file_size,
                "error": str(exc),
                "rows": 0,
            })
            continue

        row_count = len(df)
        col_count = len(df.columns)
        is_empty = (row_count == 0)
        schema_matches = (list(df.columns) == CANONICAL_COLUMNS)

        if is_empty:
            file_reports.append({
                "file": rel_path,
                "size_bytes": file_size,
                "sha256": file_hashes[rel_path],
                "rows": 0,
                "columns": col_count,
                "is_empty": True,
                "schema_matches": schema_matches,
                "missing_rainfall_count": 0,
                "missing_rainfall_pct": 0.0,
                "duplicate_rows": 0,
                "max_rainfall_mm": None,
                "spikes_gt_100mm": 0,
            })
            continue

        rainfall_col = "Telemetry Hourly Rainfall (mm)"
        missing_count = int(df[rainfall_col].isna().sum()) if rainfall_col in df else 0
        missing_pct = round((missing_count / row_count) * 100, 2)
        dup_rows = int(df.duplicated().sum())

        # Numeric values
        rf_numeric = pd.to_numeric(df[rainfall_col], errors="coerce")
        valid_rf = rf_numeric.dropna()
        max_rf = float(valid_rf.max()) if not valid_rf.empty else None
        min_rf = float(valid_rf.min()) if not valid_rf.empty else None
        spikes_100 = int((valid_rf > 100).sum())

        df["_source_file"] = rel_path
        loaded_dfs.append(df)

        file_reports.append({
            "file": rel_path,
            "size_bytes": file_size,
            "sha256": file_hashes[rel_path],
            "rows": row_count,
            "columns": col_count,
            "is_empty": False,
            "schema_matches": schema_matches,
            "missing_rainfall_count": missing_count,
            "missing_rainfall_pct": missing_pct,
            "duplicate_rows": dup_rows,
            "min_rainfall_mm": min_rf,
            "max_rainfall_mm": max_rf,
            "negative_count": int((valid_rf < 0).sum()),
            "spikes_gt_100mm": spikes_100,
        })

    # Combine all loaded dataframes for high-speed aggregated analysis
    if loaded_dfs:
        all_data = pd.concat(loaded_dfs, ignore_index=True)
    else:
        all_data = pd.DataFrame()

    total_rows = len(all_data)
    rainfall_col = "Telemetry Hourly Rainfall (mm)"
    all_rf = pd.to_numeric(all_data[rainfall_col], errors="coerce") if not all_data.empty else pd.Series()
    total_missing = int(all_rf.isna().sum())
    valid_rf_all = all_rf.dropna()
    total_zeros = int((valid_rf_all == 0).sum())
    total_positives = int((valid_rf_all > 0).sum())
    total_negatives = int((valid_rf_all < 0).sum())
    spikes_gt_50 = int((valid_rf_all > 50).sum())
    spikes_gt_100 = int((valid_rf_all > 100).sum())
    spikes_gt_300 = int((valid_rf_all > 300).sum())

    # Station-level aggregated summary
    station_summary_list = []
    if not all_data.empty and "Station" in all_data.columns:
        grouped = all_data.groupby("Station")
        for stn_name, grp in grouped:
            stn_rf = pd.to_numeric(grp[rainfall_col], errors="coerce")
            stn_valid_rf = stn_rf.dropna()
            max_val = float(stn_valid_rf.max()) if not stn_valid_rf.empty else 0.0
            stn_state = str(grp["State"].iloc[0]) if "State" in grp else ""
            stn_dist = str(grp["District"].iloc[0]) if "District" in grp else ""
            stn_lat = float(grp["Latitude"].dropna().iloc[0]) if not grp["Latitude"].dropna().empty else None
            stn_lon = float(grp["Longitude"].dropna().iloc[0]) if not grp["Longitude"].dropna().empty else None
            
            station_summary_list.append({
                "station": str(stn_name),
                "state": stn_state,
                "district": stn_dist,
                "latitude": stn_lat,
                "longitude": stn_lon,
                "total_records": len(grp),
                "missing_records": int(stn_rf.isna().sum()),
                "zero_records": int((stn_valid_rf == 0).sum()),
                "positive_records": int((stn_valid_rf > 0).sum()),
                "max_rainfall_mm": max_val,
                "spikes_gt_100": int((stn_valid_rf > 100).sum())
            })

    # Extreme records extraction
    extreme_records = []
    if not all_data.empty:
        ext_mask = all_rf > 100
        if ext_mask.any():
            ext_df = all_data[ext_mask].copy()
            ext_df["rf_num"] = all_rf[ext_mask]
            ext_df = ext_df.sort_values(by="rf_num", ascending=False)
            for _, r in ext_df.head(20).iterrows():
                extreme_records.append({
                    "station": str(r.get("Station", "")),
                    "state": str(r.get("State", "")),
                    "district": str(r.get("District", "")),
                    "time": str(r.get("Data Acquisition Time", "")),
                    "rainfall_mm": float(r["rf_num"]),
                    "file": str(r.get("_source_file", ""))
                })

    # Output Console Report
    print("=" * 100)
    print(" CWC TELEMETRY RAINFALL QUALITY-CONTROL & STATION AUDIT REPORT")
    print("=" * 100)

    # 1. Duplicate files
    print("\n1. DUPLICATE FILE AUDIT (BY SHA256 CHECKSUM):")
    print("-" * 100)
    if duplicate_files:
        for group in duplicate_files:
            h = file_hashes[group[0]]
            print(f" [DUPLICATE DETECTED] SHA256: {h}")
            for g in group:
                print(f"   -> {g}")
    else:
        print("  No duplicate files detected.")

    # 2. Per-file breakdown
    print("\n2. PER-FILE AUDIT BREAKDOWN:")
    print("-" * 100)
    fmt_h = "{:<55} | {:>8} | {:>10} | {:>7} | {:>10} | {:>10}"
    print(fmt_h.format("File Name", "Rows", "Missing", "Miss %", "Max (mm)", "Spikes>100"))
    print("-" * 100)
    for rep in file_reports:
        f_name = Path(rep["file"]).name
        f_folder = Path(rep["file"]).parent.name
        display_name = f"{f_folder}/{f_name}"
        if rep.get("is_empty"):
            print(fmt_h.format(display_name, "0 (EMPTY)", "-", "-", "-", "-"))
        else:
            max_rf_display = f"{rep['max_rainfall_mm']:.1f}" if rep["max_rainfall_mm"] is not None else "-"
            print(fmt_h.format(
                display_name,
                f"{rep['rows']:,}",
                f"{rep['missing_rainfall_count']:,}",
                f"{rep['missing_rainfall_pct']}%",
                max_rf_display,
                str(rep["spikes_gt_100mm"])
            ))

    # 3. Overall Summary
    print("\n3. OVERALL CWC DATASET SUMMARY:")
    print("-" * 100)
    print(f" Total Raw Files Audited      : {len(csv_paths)}")
    print(f" Total Records Across Files   : {total_rows:,}")
    print(f" Total Missing (NaN) Values   : {total_missing:,} ({total_missing/max(1, total_rows)*100:.2f}%)")
    print(f" Total Positive Rainfall Obs  : {total_positives:,} ({total_positives/max(1, total_rows)*100:.2f}%)")
    print(f" Total Zero Rainfall Obs      : {total_zeros:,} ({total_zeros/max(1, total_rows)*100:.2f}%)")
    print(f" Total Negative Records       : {total_negatives}")
    print(f" Spikes > 50 mm/hr            : {spikes_gt_50:,}")
    print(f" Spikes > 100 mm/hr           : {spikes_gt_100:,}")
    print(f" Spikes > 300 mm/hr           : {spikes_gt_300:,}")
    print(f" Total Unique Stations        : {len(station_summary_list)}")

    # 4. Extreme observations
    print("\n4. TOP EXTREME OBSERVATIONS (>100 mm/hr):")
    print("-" * 100)
    if extreme_records:
        fmt_ext = "  {:<15} | {:<16} | {:<18} | {:>10} mm | {:<30}"
        print(fmt_ext.format("Station", "State", "Acquisition Time", "Rainfall", "Source Folder/File"))
        print("  " + "-" * 96)
        for rec in extreme_records[:15]:
            folder_file = f"{Path(rec['file']).parent.name}/{Path(rec['file']).name}"
            print(fmt_ext.format(
                rec["station"][:15],
                rec["state"][:16],
                rec["time"],
                f"{rec['rainfall_mm']:.1f}",
                folder_file[:30]
            ))

    # 5. Station Inventory
    print("\n5. STATION INVENTORY & COORDINATE VALIDATION:")
    print("-" * 100)
    fmt_stn = "{:<20} | {:<15} | {:<15} | {:>9} | {:>9} | {:>8} | {:>10}"
    print(fmt_stn.format("Station Name", "State", "District", "Latitude", "Longitude", "Records", "Max (mm)"))
    print("-" * 100)
    for stn in sorted(station_summary_list, key=lambda x: (x["state"], x["station"])):
        lat_str = f"{stn['latitude']:.4f}" if stn['latitude'] is not None else "N/A"
        lon_str = f"{stn['longitude']:.4f}" if stn['longitude'] is not None else "N/A"
        print(fmt_stn.format(
            stn["station"][:20],
            stn["state"][:15],
            stn["district"][:15],
            lat_str,
            lon_str,
            f"{stn['total_records']:,}",
            f"{stn['max_rainfall_mm']:.1f}"
        ))

    print("\n" + "=" * 100)
    print(" END OF QUALITY-CONTROL REPORT")
    print("=" * 100)

    # Save to JSON
    qc_output_path = Path("data/cwc_qc_report.json")
    try:
        with qc_output_path.open("w", encoding="utf-8") as f:
            json.dump({
                "audit_timestamp": datetime.utcnow().isoformat(),
                "total_files": len(csv_paths),
                "total_records": total_rows,
                "total_missing": total_missing,
                "duplicate_file_groups": duplicate_files,
                "file_reports": file_reports,
                "stations": station_summary_list
            }, f, indent=2)
        print(f"\nMachine-readable QC summary saved to: {qc_output_path}")
    except Exception as e:
        print(f"Warning: Could not save JSON report: {e}")

    return {
        "total_files": len(csv_paths),
        "total_records": total_rows,
        "duplicate_files": duplicate_files,
        "file_reports": file_reports,
        "station_count": len(station_summary_list)
    }


if __name__ == "__main__":
    run_cwc_qc()
