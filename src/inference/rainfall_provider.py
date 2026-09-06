"""
Rainfall Observation Provider & Spatial Location Matching
==========================================================
Retrieves current and operational rainfall observations from CWC
telemetry stations for requested geographic coordinates in Northeast India,
with secondary IMD gridded macro-level contextual integration.

Key Architectural Safeguards & Provenance Rules:
1. CWC station rainfall is the preferred primary operational telemetry source
   for exact point coordinates within the operational domain.
2. Distance from query point to nearest station is always explicitly calculated
   and returned in the response payload.
3. If the nearest station exceeds MAX_CWC_DISTANCE_KM (default 50 km), status
   NO_RELIABLE_LOCAL_STATION is returned. Distant observations (>50 km) are
   NEVER silently assumed to represent local slope conditions.
4. Missing rainfall values are NEVER replaced with zero. Missing != 0.0 mm.
5. Telemetry quality is strictly audited: GOOD, PARTIAL, MISSING, STALE,
   or NO_RELIABLE_STATION.
6. Rainfall observations older than MAX_RAINFALL_AGE_HOURS (default 6h) are
   explicitly flagged STALE. Stale != Normal.
7. IMD district and state-level observations are integrated where legitimate
   administrative and date relationships exist, but no unvalidated
   station-to-IMD coordinate mapping is assumed.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "risk_thresholds.json"
CWC_FEATURES_FILE = PROJECT_ROOT / "data" / "processed" / "cwc_rainfall_features.csv"
INTEGRATED_FILE = PROJECT_ROOT / "data" / "processed" / "rainfall" / "rainfall_daily_integrated.csv"
IMD_STATEWISE_FILE = PROJECT_ROOT / "data" / "processed" / "imd" / "imd_statewise_ner.csv"
IMD_DISTRICTWISE_FILE = PROJECT_ROOT / "data" / "processed" / "imd" / "imd_districtwise_ner.csv"

# Haversine Distance (Kilometres)
EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two points in kilometres."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_KM * c


def haversine_vectorized_km(lat1: float, lon1: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Vectorized Haversine calculation against array of station coordinates."""
    phi1 = np.radians(lat1)
    phi2 = np.radians(lats)
    dphi = np.radians(lats - lat1)
    dlam = np.radians(lons - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    c = 2.0 * np.atan2(np.sqrt(a), np.sqrt(np.maximum(0.0, 1.0 - a)))
    return EARTH_RADIUS_KM * c


def _normalize_name(value: Any) -> str:
    """Normalize administrative state/district string."""
    if value is None or pd.isna(value):
        return ""
    val = str(value).strip().upper()
    return " ".join(val.split()).replace("\r", "").replace("\n", "")


def _parse_num(val: Any) -> Optional[float]:
    """Parse numeric float from string or number."""
    if val is None or pd.isna(val):
        return None
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None


def _parse_pct(val: Any) -> Optional[float]:
    """Parse percentage departure into signed float."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip().replace("%", "").replace(",", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


class RainfallProvider:
    """In-memory operational rainfall provider with spatial indexing and IMD integration."""

    def __init__(
        self,
        cwc_file: Optional[Path] = None,
        config_file: Optional[Path] = None,
        imd_state_file: Optional[Path] = None,
        imd_district_file: Optional[Path] = None,
    ):
        self.config_file = Path(config_file or CONFIG_FILE)
        self.cwc_file = Path(cwc_file or CWC_FEATURES_FILE)
        self.imd_state_file = Path(imd_state_file or IMD_STATEWISE_FILE)
        self.imd_district_file = Path(imd_district_file or IMD_DISTRICTWISE_FILE)
        self.config = self._load_config()

        # Operational Defaults
        rf_cfg = self.config.get("rainfall", {})
        self.default_max_distance_km = float(rf_cfg.get("max_station_distance_km", 50.0))
        self.default_max_age_hours = float(rf_cfg.get("max_rainfall_age_hours", 6.0))
        self.min_coverage_ratio = float(rf_cfg.get("min_coverage_ratio", 0.75))

        # Station and data registries
        self._stations_df: Optional[pd.DataFrame] = None
        self._station_lats: Optional[np.ndarray] = None
        self._station_lons: Optional[np.ndarray] = None
        self._station_records: Dict[str, pd.DataFrame] = {}
        self._station_latest: Dict[str, Dict[str, Any]] = {}

        # IMD macro registries
        self._imd_state_records: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._imd_district_records: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self._initialized = False

        self._initialize()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "rainfall": {
                "max_station_distance_km": 50.0,
                "max_rainfall_age_hours": 6.0,
                "min_coverage_ratio": 0.75,
            }
        }

    def _initialize(self):
        """Load CWC telemetry features and IMD macro tables."""
        if not self.cwc_file.exists():
            raise FileNotFoundError(f"CWC features dataset not found at {self.cwc_file}")

        cols = [
            "station_key", "station", "state", "district",
            "latitude", "longitude", "timestamp",
            "rainfall_1h", "rainfall_24h", "rainfall_3d", "rainfall_7d",
            "coverage_24h", "coverage_3d", "coverage_7d",
            "missing_24h", "missing_3d", "missing_7d",
            "rainfall_quality", "quality_flag", "source_period"
        ]

        df = pd.read_csv(self.cwc_file, usecols=cols, low_memory=False)
        df["dt"] = pd.to_datetime(df["timestamp"], errors="coerce")

        # Extract unique stations
        st_cols = ["station_key", "station", "state", "district", "latitude", "longitude"]
        self._stations_df = df[st_cols].drop_duplicates().reset_index(drop=True)
        self._station_lats = self._stations_df["latitude"].to_numpy(dtype=float)
        self._station_lons = self._stations_df["longitude"].to_numpy(dtype=float)

        # Index CWC records by station for fast query
        for key, group in df.groupby("station_key"):
            grp_sorted = group.sort_values("dt").reset_index(drop=True)
            self._station_records[str(key)] = grp_sorted
            latest_row = grp_sorted.iloc[-1].to_dict()
            self._station_latest[str(key)] = latest_row

        # Index IMD Statewise records if available
        if self.imd_state_file.exists():
            try:
                df_st = pd.read_csv(self.imd_state_file, low_memory=False)
                state_col = "State_Normalized" if "State_Normalized" in df_st.columns else "State"
                df_st["state_norm"] = df_st[state_col].map(_normalize_name)
                df_st["date_str"] = pd.to_datetime(df_st["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

                for _, r in df_st.iterrows():
                    s_norm = r["state_norm"]
                    d_str = r["date_str"]
                    if s_norm and d_str:
                        self._imd_state_records[(s_norm, d_str)] = {
                            "source": "IMD",
                            "granularity": "STATE",
                            "state": s_norm,
                            "date": d_str,
                            "daily_actual_mm": _parse_num(r.get("Daily Actual")),
                            "daily_normal_mm": _parse_num(r.get("Daily Normal")),
                            "daily_departure_pct": _parse_pct(r.get("Daily Departure Per")),
                            "category": str(r.get("Daily Category", "")).strip().replace("\r", ""),
                            "integration_level": "STATE_DATE",
                        }
            except Exception as e:
                print(f"Warning: Failed to index IMD statewise data: {e}")

        # Index IMD Districtwise records if available
        if self.imd_district_file.exists():
            try:
                df_dt = pd.read_csv(self.imd_district_file, low_memory=False)
                state_col = "State_Normalized" if "State_Normalized" in df_dt.columns else "State"
                df_dt["state_norm"] = df_dt[state_col].map(_normalize_name)
                df_dt["dist_norm"] = df_dt["District"].map(_normalize_name)
                df_dt["date_str"] = pd.to_datetime(df_dt["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

                for _, r in df_dt.iterrows():
                    s_norm = r["state_norm"]
                    dt_norm = r["dist_norm"]
                    d_str = r["date_str"]
                    if s_norm and dt_norm and d_str:
                        self._imd_district_records[(s_norm, dt_norm, d_str)] = {
                            "source": "IMD",
                            "granularity": "DISTRICT",
                            "state": s_norm,
                            "district": dt_norm,
                            "date": d_str,
                            "daily_actual_mm": _parse_num(r.get("Daily Actual")),
                            "daily_normal_mm": _parse_num(r.get("Daily Normal")),
                            "daily_departure_pct": _parse_pct(r.get("Daily Departure Per")),
                            "category": str(r.get("Daily Category", "")).strip().replace("\r", ""),
                            "integration_level": "DISTRICT_DATE",
                        }
            except Exception as e:
                print(f"Warning: Failed to index IMD districtwise data: {e}")

        self._initialized = True

    @property
    def stations_count(self) -> int:
        return len(self._stations_df) if self._stations_df is not None else 0

    @property
    def imd_state_records_count(self) -> int:
        return len(self._imd_state_records)

    @property
    def imd_district_records_count(self) -> int:
        return len(self._imd_district_records)

    def find_nearest_station(self, lat: float, lon: float) -> Tuple[Dict[str, Any], float]:
        """Find nearest CWC telemetry station and distance in km."""
        if not self._initialized or self._stations_df is None:
            raise RuntimeError("RainfallProvider not initialized.")

        dists = haversine_vectorized_km(lat, lon, self._station_lats, self._station_lons)
        min_idx = int(np.argmin(dists))
        nearest_row = self._stations_df.iloc[min_idx].to_dict()
        return nearest_row, float(dists[min_idx])

    def get_imd_macro_rainfall(self, state: str, date: Any) -> Optional[Dict[str, Any]]:
        """
        Retrieve macro state-level IMD rainfall observation for a given state and date.

        Parameters
        ----------
        state : str
            State name in Northeast India (e.g. 'Assam', 'Arunachal Pradesh').
        date : str or datetime or date
            Observation date.
        """
        if not self._initialized:
            raise RuntimeError("RainfallProvider not initialized.")

        s_norm = _normalize_name(state)
        d_str = pd.to_datetime(date, errors="coerce").strftime("%Y-%m-%d") if date is not None else ""
        return self._imd_state_records.get((s_norm, d_str))

    def get_imd_district_rainfall(self, state: str, district: str, date: Any) -> Optional[Dict[str, Any]]:
        """
        Retrieve district-level IMD rainfall observation for a given state, district, and date.

        Parameters
        ----------
        state : str
            State name in Northeast India.
        district : str
            District name (e.g. 'Cachar', 'Papum Pare').
        date : str or datetime or date
            Observation date.
        """
        if not self._initialized:
            raise RuntimeError("RainfallProvider not initialized.")

        s_norm = _normalize_name(state)
        dt_norm = _normalize_name(district)
        d_str = pd.to_datetime(date, errors="coerce").strftime("%Y-%m-%d") if date is not None else ""
        return self._imd_district_records.get((s_norm, dt_norm, d_str))

    def get_rainfall_for_location(
        self,
        latitude: float,
        longitude: float,
        timestamp: Optional[Any] = None,
        max_distance_km: Optional[float] = None,
        max_age_hours: Optional[float] = None,
        reference_time: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve best available CWC operational rainfall observation for a given location,
        with optional IMD macro contextual enrichment.

        Parameters
        ----------
        latitude : float
            Query latitude in decimal degrees.
        longitude : float
            Query longitude in decimal degrees.
        timestamp : Optional[str or datetime]
            Specific observation timestamp to query. If None, queries latest available.
        max_distance_km : Optional[float]
            Maximum acceptable station distance. Defaults to config (50 km).
        max_age_hours : Optional[float]
            Maximum acceptable observation age before flagged STALE. Defaults to config (6h).
        reference_time : Optional[str or datetime]
            Reference time for computing observation age in operational freshness evaluation.
        """
        eff_max_dist = float(max_distance_km if max_distance_km is not None else self.default_max_distance_km)
        eff_max_age = float(max_age_hours if max_age_hours is not None else self.default_max_age_hours)

        # 1. Spatial station matching
        nearest_st, dist_km = self.find_nearest_station(latitude, longitude)
        dist_km_rounded = round(dist_km, 2)
        st_key = str(nearest_st["station_key"])

        # Check distance threshold
        if dist_km > eff_max_dist:
            return {
                "status": "NO_RELIABLE_LOCAL_STATION",
                "source": "CWC",
                "station": nearest_st["station"],
                "station_key": st_key,
                "state": nearest_st["state"],
                "district": nearest_st["district"],
                "distance_km": dist_km_rounded,
                "max_acceptable_distance_km": eff_max_dist,
                "timestamp": None,
                "rainfall_1h": None,
                "rainfall_24h": None,
                "rainfall_3d": None,
                "rainfall_7d": None,
                "coverage_24h": None,
                "coverage_3d": None,
                "coverage_7d": None,
                "quality": "NO_RELIABLE_STATION",
                "quality_notes": (
                    f"Nearest telemetry station ({nearest_st['station']}) is {dist_km_rounded} km away, "
                    f"exceeding the maximum acceptable operational distance limit of {eff_max_dist} km. "
                    "Rainfall unobserved at local scale. IMD district/state observations are retained as an "
                    "available macro operational source, but the current exact-location provider uses CWC "
                    "station observations because no unvalidated station-to-IMD spatial mapping is assumed."
                ),
                "freshness": {
                    "observation_timestamp": None,
                    "reference_timestamp": str(reference_time) if reference_time else None,
                    "age_hours": None,
                    "freshness_status": "UNAVAILABLE",
                    "max_acceptable_age_hours": eff_max_age,
                },
                "imd_macro_context": None,
            }

        # 2. Retrieve observation record
        st_data = self._station_records.get(st_key)
        if st_data is None or len(st_data) == 0:
            return {
                "status": "MISSING",
                "source": "CWC",
                "station": nearest_st["station"],
                "station_key": st_key,
                "state": nearest_st["state"],
                "district": nearest_st["district"],
                "distance_km": dist_km_rounded,
                "max_acceptable_distance_km": eff_max_dist,
                "timestamp": None,
                "rainfall_1h": None,
                "rainfall_24h": None,
                "rainfall_3d": None,
                "rainfall_7d": None,
                "coverage_24h": None,
                "coverage_3d": None,
                "coverage_7d": None,
                "quality": "MISSING",
                "quality_notes": "No telemetry observations recorded for station.",
                "freshness": {
                    "observation_timestamp": None,
                    "reference_timestamp": str(reference_time) if reference_time else None,
                    "age_hours": None,
                    "freshness_status": "UNAVAILABLE",
                    "max_acceptable_age_hours": eff_max_age,
                },
                "imd_macro_context": None,
            }

        if timestamp is not None:
            target_dt = pd.to_datetime(timestamp)
            time_diffs = (st_data["dt"] - target_dt).abs()
            best_idx = int(time_diffs.argmin())
            obs = st_data.iloc[best_idx].to_dict()
            ref_dt = pd.to_datetime(reference_time) if reference_time is not None else target_dt
        else:
            obs = self._station_latest[st_key]
            if reference_time is not None:
                ref_dt = pd.to_datetime(reference_time)
            else:
                ref_dt = pd.to_datetime(obs["timestamp"])

        obs_dt = pd.to_datetime(obs["timestamp"])
        age_hours = round(abs((ref_dt - obs_dt).total_seconds()) / 3600.0, 2)
        is_stale = age_hours > eff_max_age

        # 3. Extract and sanitize values
        def sanitize_val(val: Any) -> Optional[float]:
            if val is None or pd.isna(val) or (isinstance(val, float) and np.isnan(val)):
                return None
            return round(float(val), 2)

        r_1h = sanitize_val(obs.get("rainfall_1h"))
        r_24h = sanitize_val(obs.get("rainfall_24h"))
        r_3d = sanitize_val(obs.get("rainfall_3d"))
        r_7d = sanitize_val(obs.get("rainfall_7d"))

        cov_24h = sanitize_val(obs.get("coverage_24h"))
        cov_3d = sanitize_val(obs.get("coverage_3d"))
        cov_7d = sanitize_val(obs.get("coverage_7d"))

        r_quality_raw = str(obs.get("rainfall_quality", "MISSING")).upper()

        # 4. Assess Data Quality
        if is_stale:
            quality = "STALE"
            status = "STALE"
            quality_notes = (
                f"Observation timestamp ({obs['timestamp']}) is {age_hours} hours old relative to "
                f"reference time ({ref_dt}), exceeding operational freshness limit of {eff_max_age} hours."
            )
        elif r_quality_raw == "MISSING" or (r_1h is None and r_24h is None and r_3d is None and r_7d is None):
            quality = "MISSING"
            status = "MISSING"
            quality_notes = "Observation has missing rainfall sensor records."
        elif (
            (cov_24h is not None and cov_24h < self.min_coverage_ratio)
            or obs.get("missing_24h", False)
            or r_quality_raw in ["HIGH_REVIEW", "EXTREME_REVIEW"]
        ):
            quality = "PARTIAL"
            status = "OK"
            quality_notes = (
                f"Observation has partial temporal coverage ({round((cov_24h or 0)*100, 1)}% in 24h window) "
                f"or review flag ({r_quality_raw}). Retained but marked PARTIAL."
            )
        else:
            quality = "GOOD"
            status = "OK"
            quality_notes = "Observation meets full 75%+ temporal coverage and quality criteria."

        # 5. Check IMD Macro Context (if date and state align)
        obs_date_str = obs_dt.strftime("%Y-%m-%d")
        st_name = str(obs.get("state", ""))
        dist_name = str(obs.get("district", ""))

        imd_macro = self.get_imd_macro_rainfall(st_name, obs_date_str)
        imd_dist = self.get_imd_district_rainfall(st_name, dist_name, obs_date_str)

        imd_macro_context = None
        if imd_dist is not None:
            imd_macro_context = {
                "source": "IMD",
                "scope": "DISTRICT",
                "state": imd_dist["state"],
                "district": imd_dist["district"],
                "date": obs_date_str,
                "daily_actual_mm": imd_dist["daily_actual_mm"],
                "daily_normal_mm": imd_dist["daily_normal_mm"],
                "daily_departure_pct": imd_dist["daily_departure_pct"],
                "category": imd_dist["category"],
                "integration_level": "DISTRICT_DATE",
            }
        elif imd_macro is not None:
            imd_macro_context = {
                "source": "IMD",
                "scope": "STATE",
                "state": imd_macro["state"],
                "district": dist_name if dist_name else None,
                "date": obs_date_str,
                "daily_actual_mm": imd_macro["daily_actual_mm"],
                "daily_normal_mm": imd_macro["daily_normal_mm"],
                "daily_departure_pct": imd_macro["daily_departure_pct"],
                "category": imd_macro["category"],
                "integration_level": "STATE_DATE",
            }

        return {
            "status": status,
            "source": "CWC",
            "station": obs["station"],
            "station_key": st_key,
            "state": obs["state"],
            "district": obs["district"],
            "distance_km": dist_km_rounded,
            "max_acceptable_distance_km": eff_max_dist,
            "timestamp": str(obs["timestamp"]),
            "rainfall_1h": r_1h,
            "rainfall_24h": r_24h,
            "rainfall_3d": r_3d,
            "rainfall_7d": r_7d,
            "coverage_24h": cov_24h,
            "coverage_3d": cov_3d,
            "coverage_7d": cov_7d,
            "quality": quality,
            "quality_notes": quality_notes,
            "freshness": {
                "observation_timestamp": str(obs["timestamp"]),
                "reference_timestamp": ref_dt.isoformat() if hasattr(ref_dt, "isoformat") else str(ref_dt),
                "age_hours": age_hours,
                "freshness_status": "STALE" if is_stale else "FRESH",
                "max_acceptable_age_hours": eff_max_age,
            },
            "imd_macro_context": imd_macro_context,
        }

    def close(self):
        """Free cached objects."""
        self._stations_df = None
        self._station_records.clear()
        self._station_latest.clear()
        self._imd_state_records.clear()
        self._imd_district_records.clear()


_PROVIDER_INSTANCE: Optional[RainfallProvider] = None


def get_rainfall_provider() -> RainfallProvider:
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is None:
        _PROVIDER_INSTANCE = RainfallProvider()
    return _PROVIDER_INSTANCE


def get_rainfall_for_location(
    latitude: float,
    longitude: float,
    timestamp: Optional[Any] = None,
    max_distance_km: Optional[float] = None,
    max_age_hours: Optional[float] = None,
    reference_time: Optional[Any] = None,
) -> Dict[str, Any]:
    """Module-level convenience function for location rainfall query."""
    provider = get_rainfall_provider()
    return provider.get_rainfall_for_location(
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        max_distance_km=max_distance_km,
        max_age_hours=max_age_hours,
        reference_time=reference_time,
    )


def get_imd_macro_rainfall(state: str, date: Any) -> Optional[Dict[str, Any]]:
    """Module-level convenience function for IMD state macro rainfall query."""
    provider = get_rainfall_provider()
    return provider.get_imd_macro_rainfall(state=state, date=date)


def get_imd_district_rainfall(state: str, district: str, date: Any) -> Optional[Dict[str, Any]]:
    """Module-level convenience function for IMD district macro rainfall query."""
    provider = get_rainfall_provider()
    return provider.get_imd_district_rainfall(state=state, district=district, date=date)
