"""
CLI Location Profiler for Static Landslide Susceptibility
=========================================================
Accepts a geographic location (latitude, longitude) and returns a complete
environmental profile and static susceptibility assessment for Northeast India.

Usage:
    python scripts/profile_location.py --lat 27.5925 --lon 91.6087
    python scripts/profile_location.py --lat 27.5925 --lon 91.6087 --json
"""

import sys
import json
import argparse
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.location_profiler import LocationProfiler


def format_human_readable(profile: dict) -> str:
    """Format structured profile into a clean terminal report."""
    if profile.get("status") == "OUTSIDE_SUPPORTED_DOMAIN":
        loc = profile.get("location", {})
        lines = [
            "=" * 60,
            "STATIC SUSCEPTIBILITY LOCATION PROFILE — DOMAIN ERROR",
            "=" * 60,
            f"Requested Latitude:  {loc.get('latitude')}",
            f"Requested Longitude: {loc.get('longitude')}",
            f"Error: {profile.get('error')}",
            "",
            "Supported States in Model Domain:",
            ", ".join(profile.get("supported_states", [])),
            "=" * 60,
        ]
        return "\n".join(lines)

    loc = profile["location"]
    terrain = profile["terrain"]
    soil = profile["soil"]
    lulc = profile["landcover"]
    susc = profile["susceptibility"]
    qual = profile["quality"]
    exp = profile["explainability"]
    model = profile["model"]

    lines = [
        "=" * 60,
        "STATIC SUSCEPTIBILITY LOCATION PROFILE",
        "=" * 60,
        "Location:",
        f"  Latitude:          {loc['latitude']:.4f}°N",
        f"  Longitude:         {loc['longitude']:.4f}°E",
        f"  State:             {loc['state']}",
        f"  Country:           {loc['country']}",
        "",
        "Terrain (Copernicus DEM 30m):",
        f"  Elevation:         {terrain['elevation_m']} m",
        f"  Slope:             {terrain['slope_deg']}°",
        f"  Aspect:            {terrain['aspect_deg']}°",
        f"  Relief (5x5 std):  {terrain['relief_std_5x5_m']} m",
        f"  Tile:              {terrain['dem_tile']}",
        "",
        "Soil (ISRIC SoilGrids v2.0):",
        f"  WRB Soil Class:    {soil['soil_class']}",
        f"  Clay Content:      {soil['clay_percent']}%",
        f"  Sand Content:      {soil['sand_percent']}%",
        f"  Silt Content:      {soil['silt_percent']}%",
        f"  Bulk Density:      {soil['bulk_density_kg_dm3']} kg/dm³",
        "",
        "Land Cover (ESA WorldCover 10m):",
        f"  Class Code:        {lulc['landcover_class_code']}",
        f"  Class Description: {lulc['landcover_class']}",
        "",
        "Static Susceptibility Assessment:",
        f"  Susceptibility Score:  {susc['score']:.4f} (range 0.00 to 1.00)",
        f"  Susceptibility Tier:   {susc['category']} ({susc['category_label']})",
        f"  Interpretation:        {susc['category_description']}",
        "",
        "Key Contributing Factors (Model Associations):",
    ]

    for r in exp.get("reason_codes", []):
        lines.append(f"  * [{r['code']}] {r['description']}")

    lines.extend([
        "",
        "Data Quality & Completeness:",
        f"  Status:            {qual['status']}",
        f"  Features Observed: {qual['available_features_count']} / {qual['total_required_features']}",
        f"  Imputation Used:   {'Yes' if qual['imputation_applied'] else 'No'}",
        "",
        "Model Lineage:",
        f"  Architecture:      {model['name']}",
        f"  Selection:         {model['selected_model']}",
        f"  Spatial CV AUC:    {model['spatial_cv_roc_auc']:.4f}",
        f"  Output Mode:       {model['output_type']}",
        "=" * 60,
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Profile location and compute static landslide susceptibility score."
    )
    parser.add_argument("--lat", type=float, required=True, help="Latitude in decimal degrees")
    parser.add_argument("--lon", type=float, required=True, help="Longitude in decimal degrees")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON only")

    args = parser.parse_args()

    profiler = LocationProfiler()
    try:
        profile = profiler.profile_location(args.lat, args.lon)
    finally:
        profiler.close()

    if args.json:
        print(json.dumps(profile, indent=2))
    else:
        print(format_human_readable(profile))

    if profile.get("status") == "OUTSIDE_SUPPORTED_DOMAIN":
        sys.exit(1)


if __name__ == "__main__":
    main()
