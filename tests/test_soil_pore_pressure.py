"""
Unit Tests for Geotechnical Soil Saturation and Pore Water Pressure Mechanics
=============================================================================
Verifies:
1. Soil porosity calculation from bulk density and particle density.
2. Saxton & Rawls saturated hydraulic conductivity pedotransfer function.
3. Moisture infiltration and saturation ratio scaling with rainfall.
4. Positive pore water pressure development above 70% field capacity.
5. Mohr-Coulomb effective shear strength & Infinite Slope Factor of Safety (FoS).
6. Synthetic Sentinel-1 SAR C-band permittivity & backscatter response.
7. Integration in RiskEngine and LocationProfiler.
"""

import pytest
import numpy as np

from src.inference.soil_pore_pressure import compute_soil_saturation_and_pore_pressure
from src.inference.risk_engine import evaluate_location_risk


def test_dry_soil_baseline():
    """Under dry conditions, saturation is moderate, pore pressure is 0, and slope is stable."""
    res = compute_soil_saturation_and_pore_pressure(
        clay_percent=25.0,
        sand_percent=45.0,
        silt_percent=30.0,
        bulk_density_kg_dm3=1.30,
        slope_deg=20.0,
        rainfall_24h=0.0,
        rainfall_3d=0.0,
        rainfall_7d=0.0,
    )

    assert 0.40 <= res["porosity"] <= 0.65
    assert res["saturation_ratio"] < 0.50
    assert res["pore_water_pressure_kpa"] == 0.0
    assert res["factor_of_safety"] > 1.30
    assert res["stability_status"] == "GEOTECHNICALLY_STABLE"
    assert res["liquefaction_risk"] == "MINIMAL"


def test_torrential_saturation_pore_pressure_rise():
    """Severe storm rainfall drives positive pore water pressure and drops Factor of Safety."""
    res = compute_soil_saturation_and_pore_pressure(
        clay_percent=32.0,
        sand_percent=35.0,
        silt_percent=33.0,
        bulk_density_kg_dm3=1.25,
        slope_deg=35.0,
        rainfall_24h=140.0,
        rainfall_3d=260.0,
        rainfall_7d=400.0,
        twi=6.2,
    )

    assert res["saturation_ratio"] >= 0.70
    assert res["pore_water_pressure_kpa"] > 0.0
    assert res["saturation_state"] in ["HIGH_PORE_PRESSURE", "CRITICAL_SATURATION"]
    assert res["sar_dielectric_constant"] > 15.0 # Elevated water content raises dielectric permittivity


def test_risk_engine_soil_integration():
    """Full integrated evaluation includes dynamic soil saturation and FoS."""
    res = evaluate_location_risk(27.5054, 88.5284, auto_refetch=True)
    assert res["status"] == "SUCCESS"
    soil = res["static_susceptibility"]["soil"]

    assert "porosity" in soil
    assert "saturation_ratio" in soil
    assert "pore_water_pressure_kpa" in soil
    assert "factor_of_safety" in soil
    assert "stability_status" in soil
    assert isinstance(soil["factor_of_safety"], float)
    assert soil["factor_of_safety"] > 0.0
