"""
Unit Tests for Hyper-Local Micro-Climate Rainfall & Doppler Weather Radar (DWR)
================================================================================
Verifies:
1. Orographic precipitation amplification on steep windward slopes.
2. Rain-shadow dampening on leeward orientations.
3. Marshall-Palmer Z-R reflectivity mapping (dBZ).
4. Cloudburst detection (>40 mm/hr or >=48 dBZ).
5. Intensity-Duration-Frequency (IDF) threshold breach detection.
6. Nearest DWR station proximity mapping across Northeast India.
7. Integration with RiskEngine.
"""

import pytest

from src.inference.micro_climate_rainfall import compute_micro_climate_rainfall
from src.inference.risk_engine import evaluate_location_risk


def test_windward_orographic_amplification():
    """South/Southwest facing mountain slope amplifies effective rainfall."""
    res = compute_micro_climate_rainfall(
        rainfall_1h=25.0,
        rainfall_24h=70.0,
        rainfall_7d=150.0,
        latitude=27.5054,
        longitude=88.5284,
        slope_deg=30.0,
        aspect_deg=200.0,  # Directly facing monsoon wind
        elevation_m=1200.0,
    )

    assert res["orographic_amplification_factor"] > 1.05
    assert res["precipitation_regime"] == "OROGRAPHIC_WINDWARD_AMPLIFIED"
    assert res["effective_micro_rainfall_1h"] > 25.0
    assert res["effective_micro_rainfall_24h"] > 70.0


def test_leeward_rain_shadow_dampening():
    """North/Northeast facing slope experiences leeward rain shadow."""
    res = compute_micro_climate_rainfall(
        rainfall_1h=25.0,
        rainfall_24h=70.0,
        rainfall_7d=150.0,
        latitude=27.5054,
        longitude=88.5284,
        slope_deg=30.0,
        aspect_deg=20.0,  # Leeward side opposite to monsoon
        elevation_m=1200.0,
    )

    assert res["orographic_amplification_factor"] < 1.0
    assert res["precipitation_regime"] == "OROGRAPHIC_LEEWARD_SHADOW"


def test_doppler_radar_cloudburst_detection():
    """Extreme convective cell generates >=48 dBZ reflectivity and flags cloudburst."""
    res = compute_micro_climate_rainfall(
        rainfall_1h=45.0,
        rainfall_24h=140.0,
        rainfall_7d=280.0,
        latitude=25.267,
        longitude=91.733,  # Cherrapunji
        slope_deg=22.0,
        aspect_deg=195.0,
        elevation_m=1300.0,
    )

    assert res["cloudburst_detected"] is True
    assert res["doppler_reflectivity_dbz"] >= 48.0
    assert res["precipitation_regime"] == "CLOUDBURST_TORRENT"
    assert res["idf_threshold_breached"] is True
    assert "Cherrapunji" in res["doppler_radar_name"]


def test_risk_engine_micro_climate_integration():
    """End-to-end evaluation incorporates micro-climate and Doppler attributes in rainfall block."""
    res = evaluate_location_risk(27.5054, 88.5284, auto_refetch=True)
    assert res["status"] == "SUCCESS"
    rf = res["rainfall"]

    assert "orographic_amplification_factor" in rf
    assert "precipitation_regime" in rf
    assert "doppler_radar_name" in rf
    assert "doppler_reflectivity_dbz" in rf
    assert isinstance(rf["orographic_amplification_factor"], float)
    assert isinstance(rf["doppler_reflectivity_dbz"], float)
