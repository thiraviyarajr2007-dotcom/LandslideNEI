"""
Anthropogenic & Human Activity Factor Engine (Phase 8K - Pillar ④)
===================================================================
Models hyper-local village landslide vulnerability resulting from human engineering
interventions, deforestation, toe excavations, and drainage modifications:

1. Road Cut Slope Geometry (Toe Excavation & Cut-Slope Steepening):
   - Unsupported road cuts into mountain toes steepen natural slope angle
     (\\beta_{natural} \\rightarrow \\beta_{cut} \\approx 60^\\circ - 75^\\circ).
   - Massive reduction in passive toe resistance and doubling of shear driving stress.

2. Drainage Congestion & Perched Hydrostatic Surcharge:
   - Silted culverts, blocked roadside ditches, and unlined municipal runoff pool
     water at slope crowns, creating perched hydrostatic head (u_h \\approx 3.5 kPa).

3. Root Tensile Cohesion Depletion (Wu & Waldron Model):
   - Natural tree forest roots contribute c_r \\approx 8 - 15 kPa of apparent cohesion.
   - Deforestation, road clearing, or jhum slash-and-burn depletes c_r \\rightarrow 0 kPa.

4. Retaining Structure Mitigation:
   - Engineered gabion crates, weep-holed retaining walls, or soil nails provide
     buttress resisting strength (T_{wall} \\approx 12.0 kPa) and pore pressure relief.

5. Modified Geotechnical Limit-Equilibrium Factor of Safety (FoS_{modified}):
   - Fuses geotechnical soil mechanics (Pillar ②) with anthropogenic alterations.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def compute_anthropogenic_impact(
    natural_slope_deg: Optional[float] = 20.0,
    landcover_class: Optional[str] = "Tree cover",
    base_cohesion_kpa: Optional[float] = 12.0,
    friction_angle_deg: Optional[float] = 30.0,
    pore_water_pressure_kpa: Optional[float] = 0.0,
    slope_position: Optional[str] = "Foot-Slope / Toe Cut",
    road_cut_present: bool = False,
    cut_slope_deg: Optional[float] = None,
    drainage_blocked: bool = False,
    unsupported_excavation: bool = False,
    deforestation_observed: bool = False,
    has_retaining_wall: bool = False,
    soil_depth_m: float = 1.2,
) -> Dict[str, Any]:
    """
    Compute anthropogenic impact metrics, modified slope stability, and engineering mitigations.

    Parameters
    ----------
    natural_slope_deg : float
        Natural undisturbed hill slope angle from high-res DEM.
    landcover_class : str
        ESA WorldCover 10m land cover class.
    base_cohesion_kpa : float
        Soil effective cohesion from pedotransfer (SoilGrids).
    friction_angle_deg : float
        Internal angle of shearing resistance (degrees).
    pore_water_pressure_kpa : float
        Pore-water pressure from dynamic hydrologic infiltration (Pillar ②).
    slope_position : str
        Topographic position index classification (e.g. Foot-Slope / Toe Cut).
    road_cut_present : bool
        Whether a road cut is present at the slope base.
    cut_slope_deg : Optional[float]
        Measured or estimated slope angle of the excavated face.
    drainage_blocked : bool
        Whether road or village drainage ditches/culverts are clogged.
    unsupported_excavation : bool
        Whether hillside construction excavation lacks retaining support.
    deforestation_observed : bool
        Whether recent forest clearing / jhum slash-and-burn occurred.
    has_retaining_wall : bool
        Whether an engineered retaining wall (gabion/masonry) is installed.
    soil_depth_m : float
        Estimated active colluvial soil mantle depth (default: 1.2 m).
    """
    nat_slope = float(natural_slope_deg if natural_slope_deg is not None and not math.isnan(natural_slope_deg) else 20.0)
    c_base = float(base_cohesion_kpa if base_cohesion_kpa is not None else 12.0)
    phi = float(friction_angle_deg if friction_angle_deg is not None else 30.0)
    u_soil = float(pore_water_pressure_kpa if pore_water_pressure_kpa is not None else 0.0)

    unit_weight_soil = 18.5  # kN/m3
    phi_rad = math.radians(phi)

    # 1. Vegetation Root Cohesion (Wu & Waldron Model)
    lc = (landcover_class or "").lower()
    if "tree" in lc or "forest" in lc:
        root_cohesion = 10.0
    elif "shrub" in lc:
        root_cohesion = 4.0
    elif "grass" in lc:
        root_cohesion = 2.0
    elif "cropland" in lc:
        root_cohesion = 1.0
    else:
        root_cohesion = 0.0

    if deforestation_observed:
        root_cohesion = 0.0

    # 2. Road Cut & Cut-Slope Geometry
    is_cut = bool(road_cut_present or unsupported_excavation)
    if is_cut:
        effective_slope = float(cut_slope_deg) if cut_slope_deg is not None and cut_slope_deg > 0 else min(75.0, nat_slope + 25.0)
        cut_severity = "SEVERE" if effective_slope >= 60.0 else "MODERATE"
    elif slope_position in ["Foot-Slope / Toe Cut", "Valley Bottom / Deep Hollow"] and nat_slope >= 20.0:
        effective_slope = nat_slope
        cut_severity = "POTENTIAL_TOE_EXPOSURE"
    else:
        effective_slope = nat_slope
        cut_severity = "NONE"

    eff_slope_rad = math.radians(effective_slope)

    # 3. Drainage Hydrostatic Surcharge
    if drainage_blocked:
        drainage_condition = "BLOCKED_CONCENTRATED_RUNOFF"
        hydrostatic_surcharge_kpa = 3.5  # ~0.35m perched water column
    else:
        drainage_condition = "NORMAL_SURFACE_DRAINAGE"
        hydrostatic_surcharge_kpa = 0.0

    total_pore_pressure = u_soil + hydrostatic_surcharge_kpa

    # 4. Retaining Structure Mitigation
    retaining_wall_status = (
        "ENGINEERED_RETAINING_WALL"
        if has_retaining_wall
        else ("UNSUPPORTED_EXCAVATION" if is_cut else "NATURAL_SLOPE")
    )

    # 5. Anthropogenic Hazard Multiplier
    multiplier = 1.0
    if is_cut:
        multiplier += 0.45 if cut_severity == "SEVERE" else 0.25
    if drainage_blocked:
        multiplier += 0.30
    if deforestation_observed:
        multiplier += 0.20
    if has_retaining_wall:
        multiplier -= 0.35

    anthropogenic_multiplier = round(min(2.50, max(0.70, multiplier)), 2)

    # 6. Modified Geotechnical Factor of Safety (FoS)
    cos_b = math.cos(eff_slope_rad)
    sin_b = math.sin(eff_slope_rad)
    total_stress = unit_weight_soil * soil_depth_m * (cos_b ** 2)
    effective_stress = max(0.0, total_stress - total_pore_pressure)

    total_cohesion = c_base + root_cohesion
    resisting_strength = total_cohesion + effective_stress * math.tan(phi_rad)
    driving_stress = max(0.5, unit_weight_soil * soil_depth_m * sin_b * cos_b)

    # If engineered retaining wall is present, add structural buttress resistance
    if has_retaining_wall:
        resisting_strength += 12.0

    fos_modified = round(min(5.0, max(0.15, resisting_strength / driving_stress)), 2)

    if fos_modified <= 1.0:
        verdict = "CRITICAL_INSTABILITY"
    elif fos_modified <= 1.30:
        verdict = "MARGINAL_EQUILIBRIUM"
    else:
        verdict = "STABLE"

    # 7. Actionable Civil & Bio-Engineering Mitigations
    recommendations: List[str] = []
    if is_cut and not has_retaining_wall:
        recommendations.append("Construct weep-holed gabion or reinforced masonry retaining wall at cut toe.")
    if drainage_blocked:
        recommendations.append("Install lined storm runoff interceptor drain and clear blocked culverts.")
    if deforestation_observed or root_cohesion < 3.0:
        recommendations.append("Plant deep-rooting vetiver grass and endemic alder trees for bio-slope reinforcement.")
    if fos_modified <= 1.0:
        recommendations.append("IMMEDIATE: Restrict heavy vehicle movement and evacuate dwellings directly below unsupported cut-face.")

    if not recommendations:
        recommendations.append("Maintain routine seasonal drainage clearance and slope inspection.")

    return {
        "road_cut_present": is_cut,
        "road_cut_severity": cut_severity,
        "cut_slope_deg": round(effective_slope, 1) if is_cut else None,
        "effective_slope_deg": round(effective_slope, 1),
        "drainage_condition": drainage_condition,
        "hydrostatic_surcharge_kpa": round(hydrostatic_surcharge_kpa, 2),
        "retaining_wall_status": retaining_wall_status,
        "root_cohesion_kpa": round(root_cohesion, 1),
        "deforestation_observed": bool(deforestation_observed),
        "anthropogenic_hazard_multiplier": anthropogenic_multiplier,
        "modified_factor_of_safety": fos_modified,
        "stability_verdict": verdict,
        "recommended_mitigations": recommendations,
    }
