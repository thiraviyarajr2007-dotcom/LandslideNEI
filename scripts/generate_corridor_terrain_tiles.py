"""
LANDSLIDENEI - Preprocessed Regional Terrain Cache Generator
============================================================
Extracts high-resolution 3D terrain meshes (elevation, Horn's slope, aspect)
from authoritative Copernicus GLO-30 rasters for the 6 primary operational corridors.
Saves lightweight cached JSON files into data/processed/dem/terrain_cache/
for offline, standalone desktop workstation packaging (<1 MB total).
"""

from __future__ import annotations

import gzip
import json
import math
import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEM_DIR = PROJECT_ROOT / "data" / "raw" / "dem" / "copernicus_glo30" / "downloads"
CACHE_DIR = PROJECT_ROOT / "data" / "processed" / "dem" / "terrain_cache"

# Authoritative Operational Corridors in Northeast India
PRIMARY_CORRIDORS = [
    {
        "id": "corridor_nagaland_kohima",
        "sector": "nagaland",
        "name": "Kohima & Zubza Axis (NH-29)",
        "state": "Nagaland",
        "latitude": 25.6740,
        "longitude": 94.1120,
        "radius_km": 10.0,
        "grid_size": 128,
        "description": "High-risk arterial freight corridor connecting Dimapur to Kohima along unstable shale/sandstone terrain.",
    },
    {
        "id": "corridor_sikkim_gangtok",
        "sector": "sikkim",
        "name": "Gangtok NH-10 Teesta Gorge Corridor",
        "state": "Sikkim",
        "latitude": 27.3389,
        "longitude": 88.6065,
        "radius_km": 10.0,
        "grid_size": 128,
        "description": "Vital lifeline corridor along the steep Teesta river gorge prone to debris flows and slope failures.",
    },
    {
        "id": "corridor_meghalaya_cherrapunji",
        "sector": "cherrapunji",
        "name": "Cherrapunji-Shella Escarpment",
        "state": "Meghalaya",
        "latitude": 25.2702,
        "longitude": 91.7323,
        "radius_km": 10.0,
        "grid_size": 128,
        "description": "High-precipitation plateau escarpment experiencing extreme monsoon rainfall and rotational slips.",
    },
    {
        "id": "corridor_arunachal_tawang",
        "sector": "tawang",
        "name": "Bhalukpong-Tawang Spur (Sela Pass)",
        "state": "Arunachal Pradesh",
        "latitude": 27.5861,
        "longitude": 91.8594,
        "radius_km": 12.0,
        "grid_size": 128,
        "description": "Strategic high-altitude Himalayan mountain corridor vulnerable to rockfalls and solifluction.",
    },
    {
        "id": "corridor_mizoram_aizawl",
        "sector": "aizawl",
        "name": "Aizawl Ridge",
        "state": "Mizoram",
        "latitude": 23.7271,
        "longitude": 92.7176,
        "radius_km": 10.0,
        "grid_size": 128,
        "description": "Anticlinal ridge settlement with steep eastern/western flanks and active urban anthropogenic cut-slopes.",
    },
    {
        "id": "corridor_assam_guwahati",
        "sector": "guwahati",
        "name": "Guwahati Urban Foothills",
        "state": "Assam",
        "latitude": 26.1445,
        "longitude": 91.7362,
        "radius_km": 10.0,
        "grid_size": 128,
        "description": "Brahmaputra alluvial plain junction and granitic hillocks with dense slope settlements.",
    },
]


def extract_corridor_mesh(corridor: Dict[str, Any]) -> Dict[str, Any]:
    lat = corridor["latitude"]
    lon = corridor["longitude"]
    radius_km = corridor["radius_km"]
    grid_size = corridor["grid_size"]

    d_lat = radius_km / 111.32
    d_lon = radius_km / (111.32 * math.cos(math.radians(lat)))

    lat_f = int(math.floor(lat))
    lon_f = int(math.floor(lon))
    tile_name = f"Copernicus_DSM_COG_10_N{lat_f:02d}_00_E{lon_f:03d}_00_DEM.tif"
    tile_path = DEM_DIR / tile_name

    if not tile_path.exists():
        raise FileNotFoundError(f"DEM tile not found for corridor {corridor['id']}: {tile_path}")

    with rasterio.open(tile_path) as src:
        w = from_bounds(lon - d_lon, lat - d_lat, lon + d_lon, lat + d_lat, src.transform)
        data = src.read(1, window=w, out_shape=(grid_size, grid_size), resampling=Resampling.bilinear)
        nodata = src.nodata

    if nodata is not None:
        data = np.where(data == nodata, np.nan, data)

    # Compute metric cell dimensions for accurate slope and aspect calculation
    dx = (2 * d_lon * 111320.0 * math.cos(math.radians(lat))) / (grid_size - 1)
    dy = (2 * d_lat * 111320.0) / (grid_size - 1)

    dz_dx = (np.pad(data[:, 2:], ((0, 0), (0, 2)), mode="edge") - np.pad(data[:, :-2], ((0, 0), (2, 0)), mode="edge")) / (2 * dx)
    dz_dy = (np.pad(data[2:, :], ((0, 2), (0, 0)), mode="edge") - np.pad(data[:-2, :], ((2, 0), (0, 0)), mode="edge")) / (2 * dy)

    slope = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)) * (180.0 / math.pi)
    aspect = (np.arctan2(dz_dy, -dz_dx) * (180.0 / math.pi)) % 360.0

    valid_mask = ~np.isnan(data)
    min_elev = float(np.nanmin(data)) if np.any(valid_mask) else 0.0
    max_elev = float(np.nanmax(data)) if np.any(valid_mask) else 0.0
    mean_elev = float(np.nanmean(data)) if np.any(valid_mask) else 0.0

    elevations = [round(float(v), 1) if not np.isnan(v) else None for v in data.flatten()]
    slopes = [round(float(v), 1) if not np.isnan(v) else None for v in slope.flatten()]
    aspects = [round(float(v), 1) if not np.isnan(v) else None for v in aspect.flatten()]

    return {
        "id": corridor["id"],
        "sector": corridor["sector"],
        "name": corridor["name"],
        "state": corridor["state"],
        "description": corridor["description"],
        "status": "SUCCESS",
        "dem_source": "Copernicus DEM GLO-30 (COP-DEM_GLO-30-DGED)",
        "dem_tile": tile_name,
        "crs": "EPSG:4326",
        "center": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "bbox": [round(lon - d_lon, 5), round(lat - d_lat, 5), round(lon + d_lon, 5), round(lat + d_lat, 5)],
        "dimensions": {"width": grid_size, "height": grid_size},
        "resolution_m": round(float((dx + dy) / 2.0), 1),
        "elevation_stats": {
            "min_m": round(min_elev, 1),
            "max_m": round(max_elev, 1),
            "mean_m": round(mean_elev, 1),
            "relief_m": round(max_elev - min_elev, 1),
        },
        "elevations": elevations,
        "slopes": slopes,
        "aspects": aspects,
    }


def main():
    print("=" * 60)
    print("Generating Optimized Preprocessed 3D Terrain Corridor Cache")
    print("=" * 60)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    index = []
    total_uncompressed = 0
    total_compressed = 0

    for corridor in PRIMARY_CORRIDORS:
        print(f"Processing {corridor['name']} ({corridor['sector']})...")
        mesh_data = extract_corridor_mesh(corridor)

        json_bytes = json.dumps(mesh_data, separators=(",", ":")).encode("utf-8")
        out_json = CACHE_DIR / f"{corridor['id']}.json"
        with open(out_json, "wb") as f:
            f.write(json_bytes)

        # Also write compressed gzip for maximum packaging efficiency
        out_gz = CACHE_DIR / f"{corridor['id']}.json.gz"
        with gzip.open(out_gz, "wb") as f:
            f.write(json_bytes)

        size_raw = len(json_bytes)
        size_gz = os.path.getsize(out_gz)
        total_uncompressed += size_raw
        total_compressed += size_gz

        print(f"  -> Generated {out_json.name} ({size_raw / 1024:.1f} KB, GZ: {size_gz / 1024:.1f} KB)")
        print(f"     Elevation range: {mesh_data['elevation_stats']['min_m']} m to {mesh_data['elevation_stats']['max_m']} m")

        # Strip heavy arrays for lightweight manifest
        summary_item = {k: v for k, v in mesh_data.items() if k not in ["elevations", "slopes", "aspects"]}
        index.append(summary_item)

    manifest_path = CACHE_DIR / "corridors_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "dem_source": "Copernicus DEM GLO-30 Public (AWS Open Data)",
            "crs": "EPSG:4326",
            "nominal_resolution": "30 meters (1 arc-second)",
            "corridor_count": len(index),
            "corridors": index,
        }, f, indent=2)

    print("-" * 60)
    print(f"Manifest written to: {manifest_path}")
    print(f"Total raw cache size: {total_uncompressed / (1024 * 1024):.2f} MB")
    print(f"Total compressed size: {total_compressed / 1024:.1f} KB")
    print("Preprocessed corridor cache successfully created!")


if __name__ == "__main__":
    main()
