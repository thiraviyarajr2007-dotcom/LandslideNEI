"""
Micro-Topography & Village-Scale Terrain Analysis Engine
========================================================
Extracts micro-morphological terrain attributes from high-resolution DEM matrices:
- Profile Curvature (K_prof): Along-slope acceleration/deceleration of flow
- Planform Curvature (K_plan): Across-contour convergence/divergence of runoff
- Curvature Morphology Classification (e.g. Concave-Convergent Hollows)
- Terrain Ruggedness Index (TRI, Riley et al. 1999)
- Topographic Position Index (TPI, Weiss 2001) and Micro-Slope Position
- Topographic Wetness Index (TWI, Beven & Kirkby)
- Village Terrain Risk Multiplier (Engineering micro-catchment modifier)
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple
import numpy as np


def compute_micro_topography(
    w3: np.ndarray,
    dx: float,
    dy: float,
    center_elev: float,
    valid_cells_5x5: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Compute micro-topographic metrics from a 3x3 local DEM elevation window
    and an optional 5x5 neighborhood.

    Parameters
    ----------
    w3 : np.ndarray
        3x3 matrix of elevation values [meters] centered at coordinate.
    dx : float
        Horizontal grid cell spacing in meters (EW).
    dy : float
        Vertical grid cell spacing in meters (NS).
    center_elev : float
        Elevation at center point (w3[1, 1]).
    valid_cells_5x5 : Optional[np.ndarray]
        Flattened array of valid elevation values in 5x5 neighborhood for TPI calculation.

    Returns
    -------
    Dict[str, Any]
        Dictionary of micro-topographic parameters.
    """
    if w3.shape != (3, 3) or np.isnan(center_elev):
        return {
            "profile_curvature": np.nan,
            "plan_curvature": np.nan,
            "curvature_class": None,
            "terrain_ruggedness_index_m": np.nan,
            "topographic_position_index_m": np.nan,
            "slope_position": None,
            "topographic_wetness_index": np.nan,
            "village_terrain_risk_multiplier": 1.0,
        }

    # Extract 3x3 grid cells
    z11, z12, z13 = float(w3[0, 0]), float(w3[0, 1]), float(w3[0, 2])
    z21, z22, z23 = float(w3[1, 0]), float(w3[1, 1]), float(w3[1, 2])
    z31, z32, z33 = float(w3[2, 0]), float(w3[2, 1]), float(w3[2, 2])

    # First partial derivatives (Horn / Zevenbergen & Thorne)
    p = ((z13 + 2.0 * z23 + z33) - (z11 + 2.0 * z21 + z31)) / (8.0 * dx)
    q = ((z11 + 2.0 * z12 + z13) - (z31 + 2.0 * z32 + z33)) / (8.0 * dy)

    # Second partial derivatives (Zevenbergen & Thorne 1987)
    r_sec = (z21 - 2.0 * z22 + z23) / (dx * dx)
    t_sec = (z12 - 2.0 * z22 + z32) / (dy * dy)
    s_sec = (-z11 + z13 + z31 - z33) / (4.0 * dx * dy)

    p2 = p * p
    q2 = q * q
    p2_plus_q2 = p2 + q2
    slope_rad = math.atan(math.sqrt(p2_plus_q2))
    slope_deg = math.degrees(slope_rad)

    # Profile Curvature (units: rad / 100m)
    # Negative = concave (flow decelerates -> soil saturation / pore water accumulation)
    # Positive = convex (flow accelerates)
    if p2_plus_q2 > 1e-8:
        prof_num = -(p2 * r_sec + 2.0 * p * q * s_sec + q2 * t_sec)
        prof_denom = p2_plus_q2 * math.pow(1.0 + p2_plus_q2, 1.5)
        prof_curv = (prof_num / prof_denom) * 100.0
    else:
        prof_curv = 0.0

    # Planform Curvature (units: rad / 100m)
    # Negative = convergent (water funnels into hollow/gully -> high village debris risk)
    # Positive = divergent (water sheds away onto sides)
    if p2_plus_q2 > 1e-8:
        plan_num = -(q2 * r_sec - 2.0 * p * q * s_sec + p2 * t_sec)
        plan_denom = math.pow(p2_plus_q2, 1.5)
        plan_curv = (plan_num / plan_denom) * 100.0
    else:
        plan_curv = 0.0

    # Curvature Classification
    is_convergent = plan_curv < -0.05
    is_divergent = plan_curv > 0.05
    is_concave = prof_curv < -0.05
    is_convex = prof_curv > 0.05

    if is_convergent and is_concave:
        curv_class = "Concave-Convergent (Hollow / Extreme Accumulation Risk)"
    elif is_convergent and is_convex:
        curv_class = "Convex-Convergent (Channeled Drainage)"
    elif is_divergent and is_concave:
        curv_class = "Concave-Divergent (Decelerating Dispersal)"
    elif is_divergent and is_convex:
        curv_class = "Convex-Divergent (Shedding Ridge / Stable)"
    elif is_convergent:
        curv_class = "Convergent (Gully Channel)"
    elif is_divergent:
        curv_class = "Divergent (Nose / Ridge)"
    elif is_concave:
        curv_class = "Concave (Decelerating Slope)"
    elif is_convex:
        curv_class = "Convex (Accelerating Slope)"
    else:
        curv_class = "Planar (Uniform Slope)"

    # Terrain Ruggedness Index (TRI, Riley et al. 1999)
    # Mean root squared difference of 8 neighbors relative to center
    sq_diffs = [
        (float(w3[i, j]) - z22) ** 2
        for i in range(3)
        for j in range(3)
        if not (i == 1 and j == 1)
    ]
    tri = math.sqrt(sum(sq_diffs) / 8.0) if sq_diffs else 0.0

    # Topographic Position Index (TPI, Weiss 2001)
    if valid_cells_5x5 is not None and len(valid_cells_5x5) > 0:
        mean_elev = float(np.mean(valid_cells_5x5))
        tpi = center_elev - mean_elev
    else:
        # Fallback to 3x3 mean
        tpi = center_elev - float(np.mean(w3))

    # Slope Position Classification
    if tpi < -5.0:
        slope_position = "Valley Bottom / Deep Hollow"
    elif -5.0 <= tpi < -1.0:
        slope_position = "Foot-Slope / Toe Cut"
    elif -1.0 <= tpi <= 1.0:
        slope_position = "Mid-Slope" if slope_deg > 10.0 else "Flat Valley Terrace"
    elif 1.0 < tpi <= 5.0:
        slope_position = "Upper Slope / Shoulder"
    else:
        slope_position = "Ridge / Crest"

    # Topographic Wetness Index (TWI, Beven & Kirkby)
    # TWI = ln(a / tan(beta))
    eff_slope_rad = max(math.radians(0.5), slope_rad)
    convergence_factor = max(0.5, 1.0 - max(-2.0, min(2.0, plan_curv)) * 0.3)
    spec_catchment_area = max(dx, dx * convergence_factor)
    twi = math.log(spec_catchment_area / math.tan(eff_slope_rad))

    # Village-Level Terrain Risk Multiplier
    # Synthesizes micro-topography into an operational risk modifier [0.80 to 1.50]
    multiplier = 1.0
    if slope_deg >= 25.0:
        multiplier += 0.15
    if is_convergent:
        multiplier += 0.15  # Water and debris flow funnel into village
    if is_concave:
        multiplier += 0.10  # Soil pore-pressure saturation trap
    if slope_position in ["Foot-Slope / Toe Cut", "Valley Bottom / Deep Hollow"]:
        multiplier += 0.10  # Hillside toe cuts and runout impact zone

    village_risk_multiplier = round(min(1.50, max(0.80, multiplier)), 2)

    return {
        "profile_curvature": round(prof_curv, 4),
        "plan_curvature": round(plan_curv, 4),
        "curvature_class": curv_class,
        "terrain_ruggedness_index_m": round(tri, 2),
        "topographic_position_index_m": round(tpi, 2),
        "slope_position": slope_position,
        "topographic_wetness_index": round(twi, 2),
        "village_terrain_risk_multiplier": village_risk_multiplier,
    }
