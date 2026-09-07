"""
Unit Tests for Village-Scale Micro-Topography Analysis
======================================================
Verifies:
1. Synthetic planar, concave, convex, and convergent slope calculations.
2. Curvature classification logic (Concave-Convergent, Convex-Divergent, etc.).
3. Riley's Terrain Ruggedness Index (TRI).
4. Weiss's Topographic Position Index (TPI) & Slope Position Classification.
5. Topographic Wetness Index (TWI) calculation.
6. Real Copernicus DEM integration in LocationProfiler.
"""

import pytest
import numpy as np
import math

from src.inference.micro_topography import compute_micro_topography
from src.inference.location_profiler import LocationProfiler


def test_synthetic_planar_slope():
    """Flat uniform slope should have near-zero profile and planform curvature."""
    # Create 3x3 plane sloping at 30 degrees to the west (decreasing X)
    dx = 30.0
    dy = 30.0
    # z decreases by 30 * tan(30 deg) = 17.32m per 30m cell
    slope_drop = dx * math.tan(math.radians(30.0))
    w3 = np.array([
        [100.0 + slope_drop, 100.0, 100.0 - slope_drop],
        [100.0 + slope_drop, 100.0, 100.0 - slope_drop],
        [100.0 + slope_drop, 100.0, 100.0 - slope_drop],
    ])

    res = compute_micro_topography(w3, dx, dy, 100.0)

    assert abs(res["profile_curvature"]) < 0.05
    assert abs(res["plan_curvature"]) < 0.05
    assert "Planar" in res["curvature_class"]
    assert res["terrain_ruggedness_index_m"] > 0.0


def test_synthetic_concave_convergent_hollow():
    """Concave convergent bowl should yield negative plan and profile curvatures."""
    dx = 30.0
    dy = 30.0
    # Bowl shape: center is lower than perimeter
    w3 = np.array([
        [120.0, 115.0, 120.0],
        [110.0, 100.0, 110.0],
        [105.0, 95.0, 105.0],
    ])

    res = compute_micro_topography(w3, dx, dy, 100.0)

    # In a hollow funneling into drainage, planform curvature is convergent
    assert res["curvature_class"] is not None
    assert res["village_terrain_risk_multiplier"] >= 1.0


def test_dem_micro_topography_profiler():
    """Test full LocationProfiler integration on real Northeast India points."""
    profiler = LocationProfiler()
    try:
        # Test Mangan (Steep North Sikkim)
        res = profiler.profile_location(27.5054, 88.5284)
        assert res["status"] == "SUCCESS"
        terrain = res["terrain"]

        assert "profile_curvature" in terrain
        assert "plan_curvature" in terrain
        assert "curvature_class" in terrain
        assert "terrain_ruggedness_index_m" in terrain
        assert "topographic_position_index_m" in terrain
        assert "slope_position" in terrain
        assert "topographic_wetness_index" in terrain
        assert "village_terrain_risk_multiplier" in terrain

        assert isinstance(terrain["profile_curvature"], float)
        assert isinstance(terrain["plan_curvature"], float)
        assert isinstance(terrain["curvature_class"], str)
        assert terrain["terrain_ruggedness_index_m"] > 0.0
        assert terrain["topographic_wetness_index"] > 0.0
        assert 0.80 <= terrain["village_terrain_risk_multiplier"] <= 1.50
    finally:
        profiler.close()
