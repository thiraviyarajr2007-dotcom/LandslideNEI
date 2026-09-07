"""
Geotechnical Soil Saturation & Pore Water Pressure Analysis Engine
==================================================================
Implements physical soil mechanics for village-scale landslide hazard:
1. Terzaghi Effective Stress Principle: sigma' = sigma - u
2. Mohr-Coulomb Shear Failure Criterion: tau_f = c' + (sigma - u) tan(phi')
3. Infinite Slope Limit Equilibrium Model: Factor of Safety (FoS)
4. Hydrological Soil Infiltration & Pore-Water Pressure Evolution
5. Synthetic Sentinel-1 SAR Dielectric Permittivity Backscatter Modeling
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional
import numpy as np


def compute_soil_saturation_and_pore_pressure(
    clay_percent: Optional[float],
    sand_percent: Optional[float],
    silt_percent: Optional[float],
    bulk_density_kg_dm3: Optional[float],
    slope_deg: Optional[float],
    rainfall_24h: Optional[float] = 0.0,
    rainfall_3d: Optional[float] = 0.0,
    rainfall_7d: Optional[float] = 0.0,
    twi: Optional[float] = 4.0,
    soil_depth_m: float = 1.2,
) -> Dict[str, Any]:
    """
    Compute geotechnical soil saturation ratio, transient pore water pressure,
    and the physical Factor of Safety (FoS) on a slope.

    Parameters
    ----------
    clay_percent : Optional[float]
        Soil clay mass fraction (0-100%).
    sand_percent : Optional[float]
        Soil sand mass fraction (0-100%).
    silt_percent : Optional[float]
        Soil silt mass fraction (0-100%).
    bulk_density_kg_dm3 : Optional[float]
        Dry bulk density (e.g. 1.2 - 1.6 kg/dm3).
    slope_deg : Optional[float]
        Local slope angle in degrees.
    rainfall_24h : Optional[float]
        24-hour antecedent rainfall [mm].
    rainfall_3d : Optional[float]
        3-day cumulative rainfall [mm].
    rainfall_7d : Optional[float]
        7-day cumulative rainfall [mm].
    twi : Optional[float]
        Topographic Wetness Index.
    soil_depth_m : float
        Estimated active regolith/colluvium depth in meters. Defaults to 1.2m.

    Returns
    -------
    Dict[str, Any]
        Dictionary of geotechnical soil saturation & pore pressure metrics.
    """
    # Safe defaults for imputations
    clay = 25.0 if (clay_percent is None or np.isnan(clay_percent)) else float(clay_percent)
    sand = 40.0 if (sand_percent is None or np.isnan(sand_percent)) else float(sand_percent)
    silt = 35.0 if (silt_percent is None or np.isnan(silt_percent)) else float(silt_percent)
    bdod = 1.30 if (bulk_density_kg_dm3 is None or np.isnan(bulk_density_kg_dm3)) else float(bulk_density_kg_dm3)
    slope = 15.0 if (slope_deg is None or np.isnan(slope_deg)) else float(slope_deg)
    slope_rad = math.radians(max(0.1, min(89.0, slope)))

    r24 = 0.0 if (rainfall_24h is None or np.isnan(rainfall_24h)) else max(0.0, float(rainfall_24h))
    r3d = r24 if (rainfall_3d is None or np.isnan(rainfall_3d)) else max(r24, float(rainfall_3d))
    r7d = r3d if (rainfall_7d is None or np.isnan(rainfall_7d)) else max(r3d, float(rainfall_7d))
    twi_val = 4.0 if (twi is None or np.isnan(twi)) else float(twi)

    # 1. Soil Porosity (n)
    # Mineral particle density rho_s is approx 2.65 g/cm3
    particle_density = 2.65
    porosity = max(0.25, min(0.70, 1.0 - (bdod / particle_density)))

    # 2. Saturated Hydraulic Conductivity (K_sat in mm/hr) - Saxton & Rawls
    ksat_approx = max(0.5, min(120.0, 10.0 * math.exp(0.03 * sand - 0.04 * clay)))

    # 3. Antecedent Moisture Balance & Saturation Ratio (Sr)
    # Effective recharge delivered to the soil column
    effective_recharge_mm = r24 * 0.90 + (r3d - r24) * 0.40 + (r7d - r3d) * 0.15
    # TWI convergence factor: concave hollows capture upslope flow
    twi_factor = max(0.8, min(1.8, 1.0 + (twi_val - 4.0) * 0.10))
    recharge_mm = effective_recharge_mm * twi_factor

    # Total pore water holding capacity of the soil column
    max_pore_capacity_mm = soil_depth_m * porosity * 1000.0

    # Baseline dry-season field capacity moisture (25% - 38%)
    baseline_saturation = 0.28 + (clay / 100.0) * 0.15
    storm_saturation = recharge_mm / max_pore_capacity_mm
    saturation_ratio = round(max(0.15, min(1.0, baseline_saturation + storm_saturation)), 3)

    # 4. Transient Pore Water Pressure (u, in kPa)
    # Above field capacity (Sr > 0.65), air bubbles occlude and positive pore water pressure develops
    unit_weight_water = 9.81  # kN/m3
    sat_unit_weight = bdod * 9.81 + porosity * unit_weight_water  # total saturated unit weight (18-20 kN/m3)

    if saturation_ratio > 0.65:
        # Transient water table height ratio m = hw / z
        m_water_table = (saturation_ratio - 0.65) / 0.35
        pore_pressure_kpa = round(
            m_water_table * unit_weight_water * soil_depth_m * (math.cos(slope_rad) ** 2), 2
        )
    else:
        m_water_table = 0.0
        pore_pressure_kpa = 0.0

    # 5. Geotechnical Strength Parameters: Effective Cohesion (c') and Friction Angle (phi')
    # Derived from USDA clay/sand percentages and root cohesion contribution
    cohesion_kpa = round(max(2.0, min(35.0, 5.0 + 0.35 * clay)), 1)
    friction_angle_deg = round(max(18.0, min(42.0, 24.0 + 0.22 * sand - 0.12 * clay)), 1)
    phi_rad = math.radians(friction_angle_deg)

    # 6. Infinite Slope Stability Model: Factor of Safety (FoS)
    # FoS = [c' + (gamma_sat * z - u) * cos^2(beta) * tan(phi)] / [gamma_sat * z * sin(beta) * cos(beta)]
    cos_b = math.cos(slope_rad)
    sin_b = math.sin(slope_rad)
    total_stress_normal = sat_unit_weight * soil_depth_m * (cos_b ** 2)
    effective_stress_normal = max(0.0, total_stress_normal - pore_pressure_kpa)

    resisting_shear_strength = cohesion_kpa + effective_stress_normal * math.tan(phi_rad)
    driving_shear_stress = max(0.5, sat_unit_weight * soil_depth_m * sin_b * cos_b)

    fos = round(min(5.0, max(0.20, resisting_shear_strength / driving_shear_stress)), 2)

    # 7. Sentinel-1 SAR C-Band Synthetic Permittivity Modeling
    # Dielectric permittivity epsilon_r increases sharply with volumetric water content
    volumetric_moisture = saturation_ratio * porosity
    dielectric_constant = round(3.5 + 32.0 * volumetric_moisture + 15.0 * (volumetric_moisture ** 2), 1)
    # Backscatter sigma0_vv in dB ranges from -17 dB (dry) to -8 dB (saturated)
    sar_backscatter_vv_db = round(-18.0 + 11.5 * saturation_ratio, 1)

    # 8. Operational Risk Classifications
    if saturation_ratio >= 0.85:
        saturation_state = "CRITICAL_SATURATION"
        liquefaction_risk = "HIGH"
    elif saturation_ratio >= 0.65:
        saturation_state = "HIGH_PORE_PRESSURE"
        liquefaction_risk = "ELEVATED"
    elif saturation_ratio >= 0.40:
        saturation_state = "MODERATE_MOISTURE"
        liquefaction_risk = "LOW"
    else:
        saturation_state = "DRY_STABLE"
        liquefaction_risk = "MINIMAL"

    if fos <= 1.00:
        stability_status = "ACTIVE_FAILURE_IMMINENT"
    elif fos <= 1.30:
        stability_status = "MARGINALLY_STABLE_WATCH"
    else:
        stability_status = "GEOTECHNICALLY_STABLE"

    return {
        "porosity": round(porosity, 3),
        "hydraulic_conductivity_mm_h": round(ksat_approx, 1),
        "saturation_ratio": saturation_ratio,
        "saturation_percent": round(saturation_ratio * 100.0, 1),
        "pore_water_pressure_kpa": pore_pressure_kpa,
        "effective_cohesion_kpa": cohesion_kpa,
        "friction_angle_deg": friction_angle_deg,
        "factor_of_safety": fos,
        "saturation_state": saturation_state,
        "liquefaction_risk": liquefaction_risk,
        "stability_status": stability_status,
        "sar_dielectric_constant": dielectric_constant,
        "sar_backscatter_vv_db": sar_backscatter_vv_db,
    }
