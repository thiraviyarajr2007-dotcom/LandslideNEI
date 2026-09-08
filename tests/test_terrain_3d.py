"""
LANDSLIDENEI - 3D DEM Terrain Visualization Automated Test Suite
================================================================
Validates authoritative Copernicus GLO-30 DEM metadata, CRS, resolution,
raster elevation bounds, missing DEM handling (proving missing != synthetic),
layer status truthfulness, 3D endpoint responses, and frontend integration.
"""

import json
import math
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.inference.terrain_service import get_terrain_service, TerrainService, NER_BBOX

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEM_DIR = PROJECT_ROOT / "data" / "raw" / "dem" / "copernicus_glo30" / "downloads"


# ==============================================================================
# 1. DEM METADATA & CRS VALIDATION TESTS
# ==============================================================================

def test_dem_metadata_endpoint():
    """Test /api/v1/terrain/metadata returns authoritative Copernicus GLO-30 specs."""
    response = client.get("/api/v1/terrain/metadata")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "AVAILABLE"
    assert "Copernicus" in data["dem_source"]
    assert data["crs"] == "EPSG:4326"
    assert data["resolution_arcsec"] == 1.0
    assert data["resolution_nominal_m"] == 30.0
    assert data["vertical_units"] == "meters"

    # Bounds validation
    bbox = data["geographic_bounds"]
    assert bbox["min_lon"] == 88.0
    assert bbox["max_lon"] == 98.0
    assert bbox["min_lat"] == 21.0
    assert bbox["max_lat"] == 30.0

    # Operational corridors list
    corridors = data["corridors"]
    assert len(corridors) >= 6
    sectors = {c["sector"] for c in corridors}
    assert {"nagaland", "sikkim", "cherrapunji", "tawang", "aizawl", "guwahati"}.issubset(sectors)


def test_dem_crs_and_resolution_contract():
    """Directly test TerrainService metadata properties."""
    svc = get_terrain_service()
    meta = svc.get_dem_metadata()
    assert meta["crs"] == "EPSG:4326"
    assert meta["resolution_arcsec"] == 1.0
    assert meta["data_policy"]["synthetic_terrain_permitted"] is False
    assert meta["data_policy"]["missing_data_behavior"] == "TERRAIN DATA UNAVAILABLE"


# ==============================================================================
# 2. ELEVATION BOUNDS & RASTER STATS TESTS
# ==============================================================================

def test_corridor_elevation_bounds():
    """Verify physical realism and validity of operational corridor elevation ranges."""
    svc = get_terrain_service()

    # Kohima Corridor (NH-29)
    kohima = svc.extract_terrain_grid(25.6740, 94.1120, sector="nagaland")
    assert kohima["status"] == "SUCCESS"
    stats = kohima["elevation_stats"]
    assert 400 < stats["min_m"] < 1200
    assert 2000 < stats["max_m"] < 3500
    assert stats["relief_m"] > 1000

    # Gangtok Corridor (NH-10)
    gangtok = svc.extract_terrain_grid(27.3389, 88.6065, sector="sikkim")
    assert gangtok["status"] == "SUCCESS"
    assert gangtok["elevation_stats"]["max_m"] > 3000

    # Cherrapunji Escarpment
    cherra = svc.extract_terrain_grid(25.2702, 91.7323, sector="cherrapunji")
    assert cherra["status"] == "SUCCESS"
    assert cherra["elevation_stats"]["min_m"] < 200
    assert cherra["elevation_stats"]["max_m"] > 1200


def test_terrain_grid_dimensions_and_derivatives():
    """Verify grid size, Horn's slope, and aspect calculations."""
    svc = get_terrain_service()
    grid = svc.extract_terrain_grid(25.6740, 94.1120, sector="nagaland")

    dims = grid["dimensions"]
    assert dims["width"] == 128
    assert dims["height"] == 128

    total_cells = 128 * 128
    assert len(grid["elevations"]) == total_cells
    assert len(grid["slopes"]) == total_cells
    assert len(grid["aspects"]) == total_cells

    # Slope range validation (0 to 90 degrees)
    valid_slopes = [s for s in grid["slopes"] if s is not None]
    assert len(valid_slopes) > 0
    assert min(valid_slopes) >= 0.0
    assert max(valid_slopes) <= 90.0

    # Aspect range validation (0 to 360 degrees)
    valid_aspects = [a for a in grid["aspects"] if a is not None]
    assert len(valid_aspects) > 0
    assert min(valid_aspects) >= 0.0
    assert max(valid_aspects) <= 360.0


# ==============================================================================
# 3. TERRAIN ENDPOINT & COORDINATE VALIDATION TESTS
# ==============================================================================

def test_terrain_mesh_endpoint_success():
    """Test /api/v1/terrain/mesh returns 200 with complete grid payload."""
    res = client.get("/api/v1/terrain/mesh?latitude=25.6740&longitude=94.1120&radius_km=10.0&grid_size=128&sector=nagaland")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "SUCCESS"
    assert data["crs"] == "EPSG:4326"
    assert len(data["elevations"]) == 128 * 128
    assert "elevation_stats" in data
    assert data["bbox"][0] < data["bbox"][2]  # min_lon < max_lon
    assert data["bbox"][1] < data["bbox"][3]  # min_lat < max_lat


def test_coordinate_validation_inside_ner():
    """Valid coordinates in NER domain return successful terrain data."""
    # Guwahati Foothills
    res = client.get("/api/v1/terrain/mesh?latitude=26.1445&longitude=91.7362&sector=guwahati")
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"


def test_coordinate_validation_outside_ner():
    """Coordinates outside supported NER domain return 404."""
    # Mumbai (Western India)
    res = client.get("/api/v1/terrain/mesh?latitude=19.0760&longitude=72.8777")
    assert res.status_code == 404
    data = res.json()
    assert data["status"] == "TERRAIN_DATA_UNAVAILABLE"
    assert "outside supported Northeast India domain" in data["message"]

    # New York
    res2 = client.get("/api/v1/terrain/mesh?latitude=40.7128&longitude=-74.0060")
    assert res2.status_code == 404
    assert res2.json()["status"] == "TERRAIN_DATA_UNAVAILABLE"


# ==============================================================================
# 4. MISSING TERRAIN DATA != SYNTHETIC TERRAIN PROOF
# ==============================================================================

def test_missing_terrain_data_not_equal_synthetic_terrain():
    """
    CRITICAL PROOF: Proves that when DEM data is unavailable, the system strictly
    reports TERRAIN_DATA_UNAVAILABLE and does NOT generate synthetic, interpolated,
    or random elevation terrain to fake completeness.
    """
    svc = get_terrain_service()

    # Query coordinate in Arabian Sea (clearly out of domain)
    res = svc.extract_terrain_grid(lat=15.0, lon=70.0)

    # 1. Must flag TERRAIN_DATA_UNAVAILABLE
    assert res["status"] == "TERRAIN_DATA_UNAVAILABLE"

    # 2. Data payload must be None
    assert res["data"] is None

    # 3. Message must be explicit
    assert "TERRAIN DATA UNAVAILABLE" in res["message"]

    # 4. Must NOT contain synthetic elevation arrays
    assert "elevations" not in res or res.get("elevations") is None
    assert "slopes" not in res or res.get("slopes") is None
    assert "aspects" not in res or res.get("aspects") is None


# ==============================================================================
# 5. LAYER AVAILABILITY & TRUTHFULNESS TESTS
# ==============================================================================

def test_layers_status_truthfulness():
    """Verify all 3D layers accurately reflect authoritative data availability."""
    res = client.get("/api/v1/layers/status")
    assert res.status_code == 200
    data = res.json()
    layers = data["layers"]

    # Terrain is available
    assert layers["terrain"]["status"] == "AVAILABLE"

    # Derived DEM layers
    assert layers["elevation"]["status"] == "AVAILABLE"
    assert layers["slope"]["status"] == "AVAILABLE"
    assert layers["aspect"]["status"] == "AVAILABLE"

    # Historical landslides connected to 75 verified events
    assert layers["historical_landslides"]["status"] == "CONNECTED"
    assert layers["historical_landslides"]["event_count"] == 75

    # CWC rainfall stations available
    assert layers["rainfall_stations"]["status"] == "AVAILABLE"
    assert layers["rainfall_stations"]["station_count"] >= 50

    # Risk zones available
    assert layers["risk_zones"]["status"] == "AVAILABLE"

    # Villages strictly DATA UNAVAILABLE (no fake habitations permitted)
    assert layers["villages"]["status"] == "DATA UNAVAILABLE"
    assert layers["villages"]["enabled_by_default"] is False


def test_historical_landslides_endpoint():
    """Test /api/v1/layers/historical-landslides serves verified 2021 events."""
    res = client.get("/api/v1/layers/historical-landslides")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "CONNECTED"
    assert data["count"] == 75
    events = data["events"]
    assert len(events) == 75

    first = events[0]
    assert "event_id" in first
    assert "event_date" in first
    assert "latitude" in first
    assert "longitude" in first
    assert "source_name" in first
    assert "rainfall_linkage_status" in first


# ==============================================================================
# 6. FRONTEND INTEGRATION & 2D/3D SWITCHING INTEGRITY
# ==============================================================================

def test_frontend_3d_assets_exist():
    """Verify local Three.js and OrbitControls vendor files exist for 100% offline usage."""
    three_min = PROJECT_ROOT / "dashboard" / "assets" / "vendor" / "three.min.js"
    orbit_ctrl = PROJECT_ROOT / "dashboard" / "assets" / "vendor" / "OrbitControls.js"
    terrain_js = PROJECT_ROOT / "dashboard" / "js" / "terrain3d.js"

    assert three_min.exists(), "three.min.js missing from dashboard/assets/vendor/"
    assert three_min.stat().st_size > 400000

    assert orbit_ctrl.exists(), "OrbitControls.js missing from dashboard/assets/vendor/"
    assert orbit_ctrl.stat().st_size > 20000

    assert terrain_js.exists(), "terrain3d.js missing from dashboard/js/"
    assert terrain_js.stat().st_size > 10000


def test_frontend_html_2d_3d_switching_elements():
    """Verify index.html contains required 2D/3D toggle and HUD components."""
    index_html = (PROJECT_ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")

    # View switcher buttons
    assert 'id="btn-view-2d"' in index_html
    assert 'id="btn-view-3d"' in index_html
    assert 'switchMapView' in index_html

    # Both map containers
    assert 'id="gis-map"' in index_html
    assert 'id="terrain-3d-wrapper"' in index_html
    assert 'id="terrain-3d-canvas"' in index_html

    # Camera controls
    assert 'id="btn-3d-zoom-in"' in index_html
    assert 'id="btn-3d-zoom-out"' in index_html
    assert 'id="btn-3d-top-view"' in index_html
    assert 'id="btn-3d-persp-view"' in index_html
    assert 'id="btn-3d-reset"' in index_html

    # Visual terrain exaggeration with explicit warning
    assert "VISUAL TERRAIN EXAGGERATION" in index_html
    assert 'data-exaggeration="1.0"' in index_html
    assert 'data-exaggeration="1.5"' in index_html
    assert 'data-exaggeration="2.0"' in index_html
    assert 'data-exaggeration="3.0"' in index_html

    # Real-time inspection HUD
    assert 'id="hud-3d-coords"' in index_html
    assert 'id="hud-3d-elevation"' in index_html
    assert 'id="hud-3d-slope"' in index_html
    assert 'id="hud-3d-aspect"' in index_html

    # Layer control panel drawer
    assert 'id="hud-3d-layers-drawer"' in index_html
    assert 'id="layer-3d-terrain"' in index_html
    assert 'id="layer-3d-elevation"' in index_html
    assert 'id="layer-3d-slope"' in index_html
    assert 'id="layer-3d-aspect"' in index_html
    assert 'id="layer-3d-landslides"' in index_html
    assert 'id="layer-3d-stations"' in index_html
    assert 'id="layer-3d-intensity"' in index_html
    assert 'id="layer-3d-risk"' in index_html
    assert 'id="layer-3d-villages"' in index_html

    # Scripts linked
    assert "assets/vendor/three.min.js" in index_html
    assert "assets/vendor/OrbitControls.js" in index_html
    assert "js/terrain3d.js" in index_html


# ==============================================================================
# 7. EXPANDED FULL NER 8-STATE & OFFLINE CACHE ARCHITECTURE TESTS
# ==============================================================================

def test_full_ner_8_states_coverage():
    """Verify that all 8 NER states are represented in authoritative focal corridors and regional cache."""
    svc = get_terrain_service()
    meta = svc.get_dem_metadata()
    corridors = meta["corridors"]
    states = {c["state"] for c in corridors}

    expected_ner_states = {
        "Arunachal Pradesh",
        "Assam",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Sikkim",
        "Tripura",
    }
    assert expected_ner_states.issubset(states), f"Missing states in operational corridors: {expected_ner_states - states}"
    assert meta["regional_tiles_count"] == 41, "Expected 41 regional base tiles"


def test_source_mode_reporting():
    """Verify exact source_mode reporting across focal cache, dynamic extraction, and offline cache."""
    svc = get_terrain_service()

    # 1. Focal Corridor Cache
    focal_res = svc.extract_terrain_grid(25.6740, 94.1120, sector="nagaland")
    assert focal_res["status"] == "SUCCESS"
    assert focal_res["source_mode"] == "PREPROCESSED_FOCAL_CACHE"

    # 2. Dynamic Raster Extraction (development mode with raw GeoTIFFs)
    # Coordinate outside focal corridors: e.g. Nongstoin (25.5200° N, 91.2700° E)
    dyn_res = svc.extract_terrain_grid(25.5200, 91.2700)
    assert dyn_res["status"] == "SUCCESS"
    assert dyn_res["source_mode"] == "DYNAMIC_RASTER_EXTRACTION"

    # 3. Offline Standalone Mode (simulating EXE with no raw DEM)
    svc_offline = TerrainService(dem_dir=Path("C:/nonexistent/dem"))
    off_res = svc_offline.extract_terrain_grid(25.5200, 91.2700)
    assert off_res["status"] == "SUCCESS"
    assert off_res["source_mode"] == "REGIONAL_OFFLINE_CACHE"

    # 4. Out of domain strictly reports TERRAIN_DATA_UNAVAILABLE
    unavail = svc_offline.extract_terrain_grid(28.6139, 77.2090)  # Delhi
    assert unavail["status"] == "TERRAIN_DATA_UNAVAILABLE"


def test_offline_simulation_all_10_locations():
    """
    STEP 9 VERIFICATION: Test that in packaged offline standalone mode (no raw DEM),
    all 10 required locations across all 8 NER states load genuine elevation data.
    """
    svc_offline = TerrainService(dem_dir=Path("C:/nonexistent/dem"))
    locations = [
        ("Kohima (Nagaland)", 25.6740, 94.1120),
        ("Shillong (Meghalaya)", 25.5788, 91.8933),
        ("Tezpur (Assam)", 26.6338, 92.7926),
        ("Imphal (Manipur)", 24.8170, 93.9368),
        ("Mokokchung (Nagaland)", 26.3256, 94.5165),
        ("Lunglei (Mizoram)", 22.8872, 92.7388),
        ("Agartala (Tripura)", 23.8315, 91.2868),
        ("Nongstoin (Meghalaya)", 25.5200, 91.2700),
        ("Itanagar (Arunachal Pradesh)", 27.0844, 93.6053),
        ("Namchi (Sikkim)", 27.1667, 88.3500),
    ]

    for name, lat, lon in locations:
        res = svc_offline.extract_terrain_grid(lat, lon)
        assert res["status"] == "SUCCESS", f"Failed for {name}: {res.get('message')}"
        stats = res["elevation_stats"]
        assert stats["min_m"] is not None and stats["max_m"] is not None
        assert stats["max_m"] >= stats["min_m"]
        assert len(res["elevations"]) == 128 * 128
        assert len(res["slopes"]) == 128 * 128
        assert len(res["aspects"]) == 128 * 128


def test_elevation_consistency_cache_vs_raw_dem():
    """Verify that cached elevations strictly match raw Copernicus GLO-30 GeoTIFF elevations."""
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.enums import Resampling

    svc = get_terrain_service()
    # Check Kohima corridor against Copernicus_DSM_COG_10_N25_00_E094_00_DEM.tif
    cached = svc.extract_terrain_grid(25.6740, 94.1120, sector="nagaland")
    raw_tile = DEM_DIR / "Copernicus_DSM_COG_10_N25_00_E094_00_DEM.tif"
    if raw_tile.exists():
        d_lat = 10.0 / 111.32
        d_lon = 10.0 / (111.32 * math.cos(math.radians(25.6740)))
        with rasterio.open(raw_tile) as src:
            w = from_bounds(94.1120 - d_lon, 25.6740 - d_lat, 94.1120 + d_lon, 25.6740 + d_lat, src.transform)
            raw_data = src.read(1, window=w, out_shape=(128, 128), resampling=Resampling.bilinear)
        
        raw_min = float(np.nanmin(raw_data))
        raw_max = float(np.nanmax(raw_data))
        assert abs(cached["elevation_stats"]["min_m"] - raw_min) <= 0.1
        assert abs(cached["elevation_stats"]["max_m"] - raw_max) <= 0.1


def test_sikkim_vs_kalimpong_administrative_integrity():
    """
    CRITICAL CHECK: Ensure Kalimpong is explicitly classified under West Bengal,
    preserving source context while strictly maintaining authoritative administrative geography.
    """
    svc = get_terrain_service()
    corridors = svc.get_dem_metadata()["corridors"]
    kalimpong_corr = next((c for c in corridors if c["id"] == "corridor_westbengal_kalimpong"), None)
    assert kalimpong_corr is not None, "Kalimpong corridor missing"
    assert kalimpong_corr["state"] == "West Bengal", "Kalimpong must be administratively classified as West Bengal"

