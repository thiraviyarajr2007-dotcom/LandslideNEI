#!/usr/bin/env python3
"""
CLI tool for Single-Location Landslide Risk Evaluation (Phase 8H)
================================================================
Usage:
    python scripts/evaluate_location_risk.py --lat 27.05 --lon 92.60
    python scripts/evaluate_location_risk.py --lat 26.1445 --lon 91.7362 --json
    python scripts/evaluate_location_risk.py --lat 27.5925 --lon 91.6087 --timestamp "2026-09-02 09:00:00"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.risk_engine import evaluate_location_risk


def format_terminal_output(res: dict) -> str:
    if res.get("status") != "SUCCESS":
        lines = [
            "=" * 60,
            "OPERATIONAL LANDSLIDE RISK ASSESSMENT — DOMAIN ERROR",
            "=" * 60,
            f"Requested Latitude:  {res.get('location', {}).get('latitude')}",
            f"Requested Longitude: {res.get('location', {}).get('longitude')}",
            f"Error: {res.get('error', 'Location cannot be evaluated.')}",
            "=" * 60,
        ]
        return "\n".join(lines)

    loc = res["location"]
    susc = res["static_susceptibility"]
    rf = res["rainfall"]
    trig = res["rainfall_trigger"]
    risk = res["risk"]
    obs_w = trig.get("observed_windows", {})

    def format_val(v, unit=" mm"):
        return f"{v:.1f}{unit}" if v is not None else "N/A"

    lines = [
        "=" * 65,
        "OPERATIONAL LANDSLIDE RISK ASSESSMENT REPORT",
        "=" * 65,
        "LOCATION CONTEXT",
        "-" * 65,
        f"  Coordinates:       {loc['latitude']:.4f}°N, {loc['longitude']:.4f}°E",
        f"  State:             {loc.get('state', 'Unknown')}, {loc.get('country', 'India')}",
        "",
        "STATIC SUSCEPTIBILITY (Phase 8F/8G Model A)",
        "-" * 65,
        f"  Susceptibility:    {susc['score']:.4f} ({susc['category_label']})",
        f"  Terrain Factors:   Elev: {susc['terrain']['elevation_m']}m | Slope: {susc['terrain']['slope_deg']}° | Aspect: {susc['terrain']['aspect_deg']}°",
        f"  Soil & Cover:      {susc['soil']['soil_class']} | {susc['landcover']['landcover_class']}",
        f"  Data Quality:      {susc['quality_status']}",
        "",
        "CURRENT RAINFALL TELEMETRY (Phase 8H Operational Tier)",
        "-" * 65,
        f"  Telemetry Source:  {rf.get('source', 'CWC')}",
        f"  Nearest Station:   {rf.get('station', 'N/A')} ({rf.get('distance_km', 'N/A')} km)",
        f"  Observation Time:  {rf.get('timestamp', 'N/A')}",
        f"  Rainfall 1h:       {format_val(obs_w.get('rainfall_1h'))}",
        f"  Rainfall 24h:      {format_val(obs_w.get('rainfall_24h'))}",
        f"  Rainfall 3d (72h): {format_val(obs_w.get('rainfall_3d'))}",
        f"  Rainfall 7d (168h):{format_val(obs_w.get('rainfall_7d'))}",
        f"  Telemetry Quality: {rf.get('quality', 'UNKNOWN')} ({rf.get('quality_notes', '')})",
        f"  Freshness Status:  {rf.get('freshness', {}).get('freshness_status', 'UNKNOWN')} (Age: {rf.get('freshness', {}).get('age_hours', 'N/A')}h)",
    ]

    imd_ctx = rf.get("imd_macro_context")
    if imd_ctx:
        lines.extend([
            f"  IMD Macro Context: {imd_ctx.get('source')} ({imd_ctx.get('scope')}) | State: {imd_ctx.get('state')} | "
            f"Actual: {imd_ctx.get('daily_actual_mm')}mm | Normal: {imd_ctx.get('daily_normal_mm')}mm | "
            f"Dep: {imd_ctx.get('daily_departure_pct')}% ({imd_ctx.get('category')})",
        ])

    lines.extend([
        "",
        "DYNAMIC RAINFALL TRIGGER",
        "-" * 65,
        f"  Trigger Level:     {trig['trigger_level']}",
        f"  Trigger Intensity: {trig['trigger_score'] if trig['trigger_score'] is not None else 'Unobserved'}",
        "  Trigger Reasons:",
    ])

    for tr in trig.get("trigger_reasons", []):
        lines.append(f"    * [{tr['code']}] {tr['description']}")
    if not trig.get("trigger_reasons"):
        lines.append("    * None (Rainfall accumulations within normal operational limits)")

    lines.extend([
        "",
        "FINAL OPERATIONAL RISK (Static Susceptibility + Dynamic Trigger)",
        "-" * 65,
        f"  OPERATIONAL LEVEL:        {risk['risk_level']} ({risk['risk_label']})",
        f"  Operational Fusion Score: {risk['operational_fusion_score']:.4f} (Mode: {risk['scoring_mode']})",
        f"  Score Semantics:          {risk.get('score_semantics', '')}",
        f"  Recommended Action:       {risk['operational_action']}",
        "  Decision Rationale:",
    ])

    for r in risk.get("reasons", []):
        lines.append(f"    * [{r['code']}] {r['description']}")

    lines.extend([
        "",
        "IMPORTANT SCIENTIFIC & OPERATIONAL LIMITATIONS",
        "-" * 65,
    ])
    for lim in res.get("scientific_limitations", []):
        lines.append(f"  {lim}")

    lines.append("=" * 65)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate Operational Landslide Risk for a Location")
    parser.add_argument("--lat", type=float, required=True, help="Latitude in decimal degrees")
    parser.add_argument("--lon", type=float, required=True, help="Longitude in decimal degrees")
    parser.add_argument("--timestamp", type=str, default=None, help="Observation timestamp (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--max-dist", type=float, default=None, help="Maximum telemetry station distance in km")
    parser.add_argument("--max-age", type=float, default=None, help="Maximum telemetry freshness age in hours")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    res = evaluate_location_risk(
        latitude=args.lat,
        longitude=args.lon,
        timestamp=args.timestamp,
        max_distance_km=args.max_dist,
        max_age_hours=args.max_age,
    )

    if args.json:
        print(json.dumps(res, indent=2, default=str))
    else:
        print(format_terminal_output(res))

    if res.get("status") != "SUCCESS":
        sys.exit(1)


if __name__ == "__main__":
    main()
