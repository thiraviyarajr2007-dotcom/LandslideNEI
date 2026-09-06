"""
Location Profiler & Static Susceptibility Inference Engine
==========================================================
Extracts multi-source environmental features (DEM terrain, SoilGrids, ESA WorldCover)
for arbitrary coordinates in Northeast India and evaluates static landslide susceptibility
using the Phase 8F Model A pipeline.
"""

from __future__ import annotations

import os
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.prepared import prep

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Asset paths
MODEL_PIPELINE_PATH = PROJECT_ROOT / "model" / "static_lsm_pipeline.joblib"
MODEL_METADATA_PATH = PROJECT_ROOT / "model" / "static_lsm_metadata.json"
GADM_JSON_PATH = PROJECT_ROOT / "data" / "inspection" / "landslide_validation" / "gadm41_IND_1.json"

DEM_DIR = PROJECT_ROOT / "data" / "raw" / "dem" / "copernicus_glo30" / "downloads"
SOIL_DIR = PROJECT_ROOT / "data" / "raw" / "soil"
WORLDCOVER_DIR = PROJECT_ROOT / "data" / "raw" / "worldcover" / "esa_worldcover_v200"

METRES_PER_DEGREE_LAT = 111320.0
MIN_VALID_CELLS_5X5 = 13

# Official WRB 30-class thematic mapping from SoilGrids MostProbable.vrt
WRB_CLASS_MAP = {
    0: "Acrisols",
    1: "Albeluvisols",
    2: "Alisols",
    3: "Andosols",
    4: "Arenosols",
    5: "Calcisols",
    6: "Cambisols",
    7: "Chernozems",
    8: "Cryosols",
    9: "Durisols",
    10: "Ferralsols",
    11: "Fluvisols",
    12: "Gleysols",
    13: "Gypsisols",
    14: "Histosols",
    15: "Kastanozems",
    16: "Leptosols",
    17: "Lixisols",
    18: "Luvisols",
    19: "Nitisols",
    20: "Phaeozems",
    21: "Planosols",
    22: "Plinthosols",
    23: "Podzols",
    24: "Regosols",
    25: "Solonchaks",
    26: "Solonetz",
    27: "Stagnosols",
    28: "Umbrisols",
    29: "Vertisols",
}

# Official ESA WorldCover v200 10m Legend
WORLDCOVER_LEGEND = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

# Supported Northeast India States in GADM41
NER_STATE_NAMES = {
    "ArunachalPradesh": "Arunachal Pradesh",
    "Assam": "Assam",
    "Manipur": "Manipur",
    "Meghalaya": "Meghalaya",
    "Mizoram": "Mizoram",
    "Nagaland": "Nagaland",
    "Sikkim": "Sikkim",
    "Tripura": "Tripura",
}

# Configurable Operational Susceptibility Categories
DEFAULT_SUSCEPTIBILITY_CATEGORIES = {
    "LOW": {"min": 0.0, "max": 0.25, "label": "Low Susceptibility"},
    "MODERATE": {"min": 0.25, "max": 0.50, "label": "Moderate Susceptibility"},
    "HIGH": {"min": 0.50, "max": 0.75, "label": "High Susceptibility"},
    "VERY_HIGH": {"min": 0.75, "max": 1.00, "label": "Very High Susceptibility"},
}


class LocationProfiler:
    """Production inference and location profiling engine for static landslide susceptibility."""

    def __init__(
        self,
        model_path: Path = MODEL_PIPELINE_PATH,
        metadata_path: Path = MODEL_METADATA_PATH,
        gadm_path: Path = GADM_JSON_PATH,
        categories: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        self.gadm_path = Path(gadm_path)
        self.categories = categories or DEFAULT_SUSCEPTIBILITY_CATEGORIES

        # Load metadata and model
        self.metadata = self._load_metadata()
        self.pipeline = self._load_model()

        # Feature contract verification
        self.numeric_features = self.metadata["features"]["numeric"]
        self.categorical_features = self.metadata["features"]["categorical"]
        self.required_features = self.numeric_features + self.categorical_features

        # Initialize geographic boundaries
        self.raw_states, self.prepared_states, self.ner_union_geom = self._load_gadm_boundaries()

        # Raster caches
        self._dem_cache: Dict[str, rasterio.io.DatasetReader] = {}
        self._soil_cache: Dict[str, rasterio.io.DatasetReader] = {}
        self._worldcover_cache: Dict[str, rasterio.io.DatasetReader] = {}

    def _load_metadata(self) -> dict:
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Model metadata not found at {self.metadata_path}")
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_model(self) -> Any:
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model pipeline not found at {self.model_path}")
        return joblib.load(self.model_path)

    def _load_gadm_boundaries(self) -> Tuple[Dict[str, Any], Dict[str, Any], Any]:
        """Load GADM level 1 geometries for Northeast India and prepare for fast point-in-polygon."""
        if not self.gadm_path.exists():
            raise FileNotFoundError(f"GADM GeoJSON not found at {self.gadm_path}")

        with open(self.gadm_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        state_geoms: Dict[str, Any] = {}
        all_geoms = []

        for feat in data.get("features", []):
            name = feat["properties"].get("NAME_1", "")
            if name in NER_STATE_NAMES:
                canonical = NER_STATE_NAMES[name]
                geom = shape(feat["geometry"])
                all_geoms.append(geom)
                if canonical not in state_geoms:
                    state_geoms[canonical] = geom
                else:
                    state_geoms[canonical] = state_geoms[canonical].union(geom)

        prepared = {k: prep(v) for k, v in state_geoms.items()}
        from shapely.ops import unary_union
        union_geom = unary_union(all_geoms)
        ner_union = prep(union_geom)
        return state_geoms, prepared, ner_union

    def validate_coordinates(self, lat: float, lon: float) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate coordinates and identify state.
        Returns: (is_valid_domain, state_name_or_none, error_message_or_none)
        """
        if not (-90.0 <= lat <= 90.0):
            return False, None, f"Invalid latitude: {lat}. Must be between -90 and 90."
        if not (-180.0 <= lon <= 180.0):
            return False, None, f"Invalid longitude: {lon}. Must be between -180 and 180."

        pt = Point(lon, lat)

        # Match specific state
        for state_name, prep_geom in self.prepared_states.items():
            if prep_geom.contains(pt):
                return True, state_name, None

        # Check small 0.01 degree (~1km) border tolerance around NER states
        for state_name, raw_geom in self.raw_states.items():
            if raw_geom.buffer(0.01).contains(pt):
                return True, f"{state_name} (Border)", None

        return False, None, (
            f"Coordinates ({lat:.4f}, {lon:.4f}) lie outside the supported "
            f"Northeast India (NER) operational domain."
        )

    def _get_dem_features(self, lat: float, lon: float) -> Dict[str, Any]:
        """Extract elevation, slope, aspect, and 5x5 relief standard deviation from Copernicus DEM."""
        lat_f = int(math.floor(lat))
        lon_f = int(math.floor(lon))
        tile_key = f"Copernicus_DSM_COG_10_N{lat_f:02d}_00_E{lon_f:03d}_00_DEM"
        tile_path = DEM_DIR / f"{tile_key}.tif"

        if not tile_path.exists():
            return {
                "elevation_m": np.nan,
                "slope_deg": np.nan,
                "aspect_deg": np.nan,
                "relief_std_5x5_m": np.nan,
                "dem_tile": None,
                "dem_quality": "MISSING_TILE",
            }

        if tile_key not in self._dem_cache:
            self._dem_cache[tile_key] = rasterio.open(tile_path)

        ds = self._dem_cache[tile_key]
        r, c = ds.index(lon, lat)
        nodata_val = ds.nodata

        if r < 0 or r >= ds.height or c < 0 or c >= ds.width:
            return {
                "elevation_m": np.nan,
                "slope_deg": np.nan,
                "aspect_deg": np.nan,
                "relief_std_5x5_m": np.nan,
                "dem_tile": tile_key,
                "dem_quality": "OUT_OF_BOUNDS",
            }

        r_min = max(0, r - 2)
        r_max = min(ds.height, r + 3)
        c_min = max(0, c - 2)
        c_max = min(ds.width, c + 3)

        is_partial = (r < 2 or r >= ds.height - 2 or c < 2 or c >= ds.width - 2)
        win_data = ds.read(1, window=((r_min, r_max), (c_min, c_max)))

        center_r = r - r_min
        center_c = c - c_min
        center_elev = float(win_data[center_r, center_c])

        if nodata_val is not None and (center_elev == nodata_val or np.isnan(center_elev)):
            return {
                "elevation_m": np.nan,
                "slope_deg": np.nan,
                "aspect_deg": np.nan,
                "relief_std_5x5_m": np.nan,
                "dem_tile": tile_key,
                "dem_quality": "NODATA",
            }

        # 5x5 local relief
        if nodata_val is not None:
            valid_cells = win_data[win_data != nodata_val]
        else:
            valid_cells = win_data[~np.isnan(win_data)]

        if len(valid_cells) >= MIN_VALID_CELLS_5X5:
            relief_std = float(np.std(valid_cells, ddof=0))
        else:
            relief_std = np.nan
            is_partial = True

        # Horn's 3x3 slope & aspect
        if center_r >= 1 and center_r + 1 < win_data.shape[0] and center_c >= 1 and center_c + 1 < win_data.shape[1]:
            w3 = win_data[center_r - 1 : center_r + 2, center_c - 1 : center_c + 2]
        else:
            pad_top = max(0, 1 - center_r)
            pad_bottom = max(0, (center_r + 2) - win_data.shape[0])
            pad_left = max(0, 1 - center_c)
            pad_right = max(0, (center_c + 2) - win_data.shape[1])
            padded = np.pad(win_data, ((pad_top, pad_bottom), (pad_left, pad_right)), mode="edge")
            pr = center_r + pad_top
            pc = center_c + pad_left
            w3 = padded[pr - 1 : pr + 2, pc - 1 : pc + 2]
            is_partial = True

        if nodata_val is not None and (w3 == nodata_val).any():
            is_partial = True
            w3 = np.where(w3 == nodata_val, center_elev, w3)

        dlon_deg = float(ds.res[0])
        dlat_deg = float(ds.res[1])
        dx = dlon_deg * METRES_PER_DEGREE_LAT * math.cos(math.radians(lat))
        dy = dlat_deg * METRES_PER_DEGREE_LAT

        p = ((w3[0, 2] + 2.0 * w3[1, 2] + w3[2, 2]) - (w3[0, 0] + 2.0 * w3[1, 0] + w3[2, 0])) / (8.0 * dx)
        q = ((w3[0, 0] + 2.0 * w3[0, 1] + w3[0, 2]) - (w3[2, 0] + 2.0 * w3[2, 1] + w3[2, 2])) / (8.0 * dy)

        slope_deg = math.degrees(math.atan(math.sqrt(p * p + q * q)))

        if p == 0.0 and q == 0.0:
            aspect_deg = np.nan
        else:
            aspect_deg = math.degrees(math.atan2(-p, -q))
            if aspect_deg < 0.0:
                aspect_deg += 360.0
            if aspect_deg >= 360.0:
                aspect_deg = 0.0

        return {
            "elevation_m": round(center_elev, 2),
            "slope_deg": round(slope_deg, 2),
            "aspect_deg": round(aspect_deg, 2) if not np.isnan(aspect_deg) else np.nan,
            "relief_std_5x5_m": round(relief_std, 2) if not np.isnan(relief_std) else np.nan,
            "dem_tile": tile_key,
            "dem_quality": "PARTIAL_WINDOW" if is_partial else "OK",
        }

    def _get_soil_features(self, lat: float, lon: float) -> Dict[str, Any]:
        """Extract SoilGrids v2.0 physical properties and WRB classification."""
        layers = {
            "wrb": {"file": "wrb_most_probable_nei.tif", "is_homolosine": False, "nodata": 255},
            "clay": {"file": "clay_0-5cm_mean_nei.tif", "is_homolosine": True, "scale": 10.0, "nodata": -32768},
            "sand": {"file": "sand_0-5cm_mean_nei.tif", "is_homolosine": True, "scale": 10.0, "nodata": -32768},
            "silt": {"file": "silt_0-5cm_mean_nei.tif", "is_homolosine": True, "scale": 10.0, "nodata": -32768},
            "bdod": {"file": "bdod_0-5cm_mean_nei.tif", "is_homolosine": True, "scale": 100.0, "nodata": -32768},
        }

        results = {}
        has_missing = False

        for key, cfg in layers.items():
            tif_path = SOIL_DIR / cfg["file"]
            if not tif_path.exists():
                results[key] = np.nan
                has_missing = True
                continue

            if key not in self._soil_cache:
                self._soil_cache[key] = rasterio.open(tif_path)

            src = self._soil_cache[key]
            if cfg["is_homolosine"]:
                trans = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                hx, hy = trans.transform(lon, lat)
                pt = (hx, hy)
            else:
                pt = (lon, lat)

            sample_val = list(src.sample([pt]))[0][0]

            if sample_val == cfg["nodata"]:
                results[key] = np.nan
                has_missing = True
            elif key == "wrb":
                results["soil_class"] = WRB_CLASS_MAP.get(int(sample_val), np.nan)
            else:
                results[key] = round(float(sample_val / cfg["scale"]), 2)

        return {
            "soil_class": results.get("soil_class", np.nan),
            "clay_percent": results.get("clay", np.nan),
            "sand_percent": results.get("sand", np.nan),
            "silt_percent": results.get("silt", np.nan),
            "bulk_density_kg_dm3": results.get("bdod", np.nan),
            "soil_quality": "PARTIAL" if has_missing else "OK",
        }

    def _get_worldcover_features(self, lat: float, lon: float) -> Dict[str, Any]:
        """Extract ESA WorldCover 10m land-cover class and label."""
        tile_lat = int(math.floor(lat / 3.0) * 3)
        tile_lon = int(math.floor(lon / 3.0) * 3)
        tile_id = f"N{tile_lat:02d}E{tile_lon:03d}"
        tif_name = f"ESA_WorldCover_10m_2021_v200_{tile_id}_Map.tif"
        tif_path = WORLDCOVER_DIR / tif_name

        if not tif_path.exists():
            return {
                "landcover_class_code": np.nan,
                "landcover_class": np.nan,
                "lulc_quality": "MISSING_TILE",
            }

        if tile_id not in self._worldcover_cache:
            self._worldcover_cache[tile_id] = rasterio.open(tif_path)

        src = self._worldcover_cache[tile_id]
        raw_val = list(src.sample([(lon, lat)]))[0][0]

        if raw_val == 0 or raw_val not in WORLDCOVER_LEGEND:
            return {
                "landcover_class_code": int(raw_val) if raw_val != 0 else np.nan,
                "landcover_class": np.nan,
                "lulc_quality": "NODATA",
            }

        return {
            "landcover_class_code": int(raw_val),
            "landcover_class": WORLDCOVER_LEGEND[int(raw_val)],
            "lulc_quality": "OK",
        }

    def _assign_susceptibility_category(self, score: float) -> str:
        """Assign operational susceptibility category based on score."""
        for cat_name, cfg in self.categories.items():
            if cfg["min"] <= score < cfg["max"]:
                return cat_name
        if score >= 1.0:
            return "VERY_HIGH"
        return "LOW"

    def _generate_reason_codes(
        self, terrain: Dict[str, Any], soil: Dict[str, Any], lulc: Dict[str, Any], score: float
    ) -> List[Dict[str, str]]:
        """Generate transparent, deterministic reason codes based on feature values."""
        reasons = []

        slope = terrain.get("slope_deg")
        if slope is not None and not np.isnan(slope) and slope >= 25.0:
            reasons.append({
                "code": "TERRAIN_STEEP_SLOPE",
                "description": f"Slope gradient ({slope:.1f}°) exceeds 25°, contributing strong terrain gradient signal."
            })

        relief = terrain.get("relief_std_5x5_m")
        if relief is not None and not np.isnan(relief) and relief >= 25.0:
            reasons.append({
                "code": "HIGH_LOCAL_RELIEF",
                "description": f"Local 5x5 relief roughness ({relief:.1f} m) indicates significant topographic incision."
            })

        aspect = terrain.get("aspect_deg")
        if aspect is not None and not np.isnan(aspect) and 90.0 <= aspect <= 270.0:
            reasons.append({
                "code": "SOUTH_FACING_ASPECT_SIGNAL",
                "description": f"Slope aspect ({aspect:.1f}°) faces south-to-southwest, aligning with regional moisture intercept orientation."
            })

        elev = terrain.get("elevation_m")
        if elev is not None and not np.isnan(elev) and elev >= 1500.0:
            reasons.append({
                "code": "HIGH_ELEVATION_SIGNAL",
                "description": f"Elevation ({elev:.1f} m) places the location in an elevated montane zone."
            })

        lc_class = lulc.get("landcover_class")
        if lc_class in ["Bare / sparse vegetation", "Grassland"]:
            reasons.append({
                "code": "LOW_CANOPY_VEGETATION_SIGNAL",
                "description": f"Landcover is '{lc_class}', which exhibits lower root cohesion relative to closed forest."
            })

        clay = soil.get("clay_percent")
        if clay is not None and not np.isnan(clay) and clay >= 30.0:
            reasons.append({
                "code": "FINE_SOIL_TEXTURE_SIGNAL",
                "description": f"Soil clay fraction ({clay:.1f}%) indicates fine texture prone to moisture retention."
            })

        if not reasons:
            reasons.append({
                "code": "MODERATE_BASELINE_SIGNAL",
                "description": "Location exhibits moderate baseline topography and typical regional soil/vegetation characteristics."
            })

        return reasons

    def profile_location(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Execute full location profiling and static susceptibility inference.
        Returns a structured dictionary matching the JSON specification.
        """
        # 1. Geographic Domain Validation
        is_valid_domain, state_name, domain_error = self.validate_coordinates(lat, lon)
        if not is_valid_domain:
            return {
                "status": "OUTSIDE_SUPPORTED_DOMAIN",
                "location": {
                    "latitude": lat,
                    "longitude": lon,
                    "state": None,
                    "country": "India",
                    "supported_domain": False,
                },
                "error": domain_error,
                "supported_states": sorted(list(set(NER_STATE_NAMES.values()))),
            }

        # 2. Extract Features
        terrain = self._get_dem_features(lat, lon)
        soil = self._get_soil_features(lat, lon)
        lulc = self._get_worldcover_features(lat, lon)

        # 3. Assess Feature Completeness
        model_input_dict = {
            "elevation_m": terrain.get("elevation_m"),
            "slope_deg": terrain.get("slope_deg"),
            "aspect_deg": terrain.get("aspect_deg"),
            "relief_std_5x5_m": terrain.get("relief_std_5x5_m"),
            "clay_percent": soil.get("clay_percent"),
            "sand_percent": soil.get("sand_percent"),
            "silt_percent": soil.get("silt_percent"),
            "bulk_density_kg_dm3": soil.get("bulk_density_kg_dm3"),
            "soil_class": soil.get("soil_class"),
            "landcover_class": lulc.get("landcover_class"),
        }

        missing_features = [k for k, v in model_input_dict.items() if v is None or (isinstance(v, float) and np.isnan(v))]
        imputation_applied = len(missing_features) > 0

        if len(missing_features) == 0:
            quality_status = "OK"
        elif len(missing_features) <= 4:
            quality_status = "PARTIAL"
        else:
            quality_status = "INVALID"

        # 4. Model Inference
        # Pipeline expects DataFrame with matching column names
        df_input = pd.DataFrame([model_input_dict])
        score = float(self.pipeline.predict_proba(df_input)[0, 1])
        category = self._assign_susceptibility_category(score)

        # 5. Explainability
        reason_codes = self._generate_reason_codes(terrain, soil, lulc, score)

        top_model_features = [
            {"feature": "aspect_deg", "mean_roc_auc_drop": 0.10960, "note": "Slope orientation"},
            {"feature": "relief_std_5x5_m", "mean_roc_auc_drop": 0.06124, "note": "Local topographic roughness"},
            {"feature": "elevation_m", "mean_roc_auc_drop": 0.03880, "note": "Elevation relative to regional relief"},
            {"feature": "slope_deg", "mean_roc_auc_drop": 0.03659, "note": "Terrain gradient steepness"},
        ]

        profile = {
            "status": "SUCCESS",
            "location": {
                "latitude": lat,
                "longitude": lon,
                "state": state_name,
                "country": "India",
                "supported_domain": True,
            },
            "terrain": terrain,
            "soil": soil,
            "landcover": lulc,
            "susceptibility": {
                "score": round(score, 4),
                "score_range": [0.0, 1.0],
                "category": category,
                "category_label": self.categories.get(category, {}).get("label", category),
                "category_description": (
                    "Static terrain susceptibility estimate (uncalibrated Random Forest score; "
                    "not an event-time warning or percentage probability of occurrence)."
                ),
                "category_thresholds": {
                    k: [v["min"], v["max"]] for k, v in self.categories.items()
                },
            },
            "quality": {
                "status": quality_status,
                "available_features_count": len(model_input_dict) - len(missing_features),
                "total_required_features": len(model_input_dict),
                "missing_features": missing_features,
                "imputation_applied": imputation_applied,
            },
            "explainability": {
                "reason_codes": reason_codes,
                "model_level_top_features": top_model_features,
                "disclaimer": (
                    "Reason codes describe model feature associations based on held-out spatial importance. "
                    "They represent statistical reliance and do NOT constitute physical causal proof."
                ),
            },
            "model": {
                "name": self.metadata.get("model_name", "Static Landslide Susceptibility Model (LSM)"),
                "selected_model": self.metadata.get("selected_model", "Model A (Environmental Only)"),
                "features_used": len(self.required_features),
                "output_type": "Uncalibrated Random Forest susceptibility score",
                "training_samples_count": self.metadata.get("total_training_samples", 4016),
                "spatial_cv_roc_auc": self.metadata.get("spatial_cross_validation", {}).get("mean_spatial_roc_auc", 0.8062),
            },
        }

        return profile

    def close(self):
        """Close all cached raster dataset readers."""
        for ds in self._dem_cache.values():
            try:
                ds.close()
            except Exception:
                pass
        self._dem_cache.clear()

        for ds in self._soil_cache.values():
            try:
                ds.close()
            except Exception:
                pass
        self._soil_cache.clear()

        for ds in self._worldcover_cache.values():
            try:
                ds.close()
            except Exception:
                pass
        self._worldcover_cache.clear()


# Global reusable profiler instance for simple function calls
_GLOBAL_PROFILER: Optional[LocationProfiler] = None


def profile_location(lat: float, lon: float) -> Dict[str, Any]:
    """Top-level functional entry point for location profiling and static susceptibility inference."""
    global _GLOBAL_PROFILER
    if _GLOBAL_PROFILER is None:
        _GLOBAL_PROFILER = LocationProfiler()
    return _GLOBAL_PROFILER.profile_location(lat, lon)
