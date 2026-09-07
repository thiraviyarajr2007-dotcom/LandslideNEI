"""
Hyper-Local Micro-Climate Rainfall & Doppler Weather Radar (DWR) Engine
========================================================================
Implements mountain-scale micro-meteorological dynamics for village early warning:
1. Orographic Precipitation Amplification (Windward vs Leeward rain shadow)
2. Doppler Weather Radar (DWR) Reflectivity & Marshall-Palmer Z-R conversion
3. Localized Cloudburst Detection (R > 40 mm/h or Z >= 48 dBZ)
4. Caine/Guzzetti Intensity-Duration-Frequency (IDF) Flash Threshold Modeling
5. Micro-Catchment Rational Runoff Discharge Estimation (Q_peak in m3/s)
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

# Active IMD Doppler Weather Radar (DWR) network in Northeast India
DWR_RADAR_STATIONS = [
    {"name": "Cherrapunji (Sohra) DWR", "lat": 25.267, "lon": 91.733, "range_km": 250.0},
    {"name": "Guwahati DWR", "lat": 26.106, "lon": 91.586, "range_km": 250.0},
    {"name": "Agartala DWR", "lat": 23.887, "lon": 91.240, "range_km": 250.0},
    {"name": "Mohanbari (Dibrugarh) DWR", "lat": 27.483, "lon": 95.017, "range_km": 250.0},
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points on Earth in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def compute_micro_climate_rainfall(
    rainfall_1h: Optional[float],
    rainfall_24h: Optional[float],
    rainfall_7d: Optional[float],
    latitude: float,
    longitude: float,
    slope_deg: Optional[float],
    aspect_deg: Optional[float],
    elevation_m: Optional[float],
    plan_curvature: Optional[float] = 0.0,
    twi: Optional[float] = 4.0,
) -> Dict[str, Any]:
    """
    Compute micro-climate precipitation metrics for high-resolution village early warning.

    Parameters
    ----------
    rainfall_1h : Optional[float]
        1-hour rainfall observation [mm].
    rainfall_24h : Optional[float]
        24-hour rainfall observation [mm].
    rainfall_7d : Optional[float]
        7-day cumulative rainfall observation [mm].
    latitude : float
        Target latitude.
    longitude : float
        Target longitude.
    slope_deg : Optional[float]
        Local slope angle in degrees.
    aspect_deg : Optional[float]
        Slope azimuth orientation in degrees (0=N, 90=E, 180=S, 270=W).
    elevation_m : Optional[float]
        Elevation in meters.
    plan_curvature : Optional[float]
        Planform curvature (convergent vs divergent).
    twi : Optional[float]
        Topographic Wetness Index.

    Returns
    -------
    Dict[str, Any]
        Dictionary of micro-climate and Doppler radar rainfall metrics.
    """
    r1h = max(0.0, float(rainfall_1h or 0.0))
    r24 = max(r1h, float(rainfall_24h or 0.0))
    r7d = max(r24, float(rainfall_7d or 0.0))
    elev = max(0.0, float(elevation_m or 500.0))
    slope = max(0.0, min(89.0, float(slope_deg or 15.0)))
    aspect = float(aspect_deg or 180.0)
    plan_curv = float(plan_curvature or 0.0)

    # 1. Orographic Precipitation Amplification Factor
    # Prevailing Bay of Bengal monsoon wind vector has azimuth ~200 deg (SSW)
    wind_azimuth = 200.0
    aspect_diff_rad = math.radians(aspect - wind_azimuth)
    windward_exposure = max(0.0, math.cos(aspect_diff_rad))
    slope_factor = math.sin(math.radians(slope))
    elevation_factor = min(1.5, elev / 1200.0)

    # Amplification ranges between 0.82 (leeward rain shadow) to 1.45 (steep windward ridge)
    if windward_exposure > 0.3 and slope > 12.0:
        orographic_mult = 1.0 + windward_exposure * slope_factor * elevation_factor * 0.45
        regime = "OROGRAPHIC_WINDWARD_AMPLIFIED"
    elif math.cos(aspect_diff_rad) < -0.3 and slope > 15.0:
        orographic_mult = max(0.82, 1.0 - abs(math.cos(aspect_diff_rad)) * 0.18)
        regime = "OROGRAPHIC_LEEWARD_SHADOW"
    else:
        orographic_mult = 1.0
        regime = "NORMAL_CONVECTIVE"

    orographic_mult = round(min(1.45, max(0.80, orographic_mult)), 2)
    micro_r1h = round(r1h * orographic_mult, 2)
    micro_r24 = round(r24 * orographic_mult, 2)

    # 2. Nearest Doppler Weather Radar (DWR)
    nearest_dwr = min(
        DWR_RADAR_STATIONS,
        key=lambda d: _haversine_km(latitude, longitude, d["lat"], d["lon"])
    )
    dwr_dist = round(_haversine_km(latitude, longitude, nearest_dwr["lat"], nearest_dwr["lon"]), 1)

    # Marshall-Palmer Z-R relation: Z = 200 * R^1.6 -> dBZ = 10 * log10(Z)
    eff_rate = max(0.1, micro_r1h)
    z_lin = 200.0 * math.pow(eff_rate, 1.6)
    dbz = round(min(65.0, max(10.0, 10.0 * math.log10(z_lin))), 1)

    cloudburst = micro_r1h >= 40.0 or dbz >= 48.0
    if cloudburst:
        regime = "CLOUDBURST_TORRENT"

    # 3. Caine/Guzzetti Intensity-Duration-Frequency (IDF) Threshold
    # I_thresh = 14.82 * D^(-0.39) for Eastern Himalayas
    # 1h threshold = 14.82 mm/h, 24h threshold = 103 mm/day
    idf_1h_thresh = 14.82
    idf_24h_thresh = 103.0
    idf_breached = (micro_r1h >= idf_1h_thresh) or (micro_r24 >= idf_24h_thresh)

    # 4. Rational Peak Runoff Flow into Village (Q = C * I * A / 360)
    runoff_coeff = 0.70
    catchment_ha = max(1.0, 5.0 * (1.0 - min(1.0, plan_curv * 0.2)))
    q_peak_m3_s = round((runoff_coeff * micro_r1h * catchment_ha) / 360.0, 3)

    return {
        "orographic_amplification_factor": orographic_mult,
        "precipitation_regime": regime,
        "effective_micro_rainfall_1h": micro_r1h,
        "effective_micro_rainfall_24h": micro_r24,
        "doppler_radar_name": nearest_dwr["name"],
        "doppler_radar_distance_km": dwr_dist,
        "doppler_reflectivity_dbz": dbz,
        "within_radar_horizon": dwr_dist <= nearest_dwr["range_km"],
        "cloudburst_detected": cloudburst,
        "idf_threshold_breached": idf_breached,
        "micro_runoff_peak_m3_s": q_peak_m3_s,
    }
