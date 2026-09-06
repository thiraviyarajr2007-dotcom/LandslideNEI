"""
Dynamic Rainfall Trigger Engine
===============================
Evaluates operational rainfall observations (1h, 24h, 3d, 7d) against configurable
thresholds to produce a dynamic trigger level and transparent reason codes.

IMPORTANT SCIENTIFIC NOTE:
The rainfall thresholds defined herein are CONFIGURABLE OPERATIONAL / DEMO DEFAULTS.
They are NOT scientifically calibrated landslide trigger thresholds learned from the
2014 historical inventory. They must NEVER be presented as empirical NER landslide
occurrence thresholds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "risk_thresholds.json"


class RainfallTriggerEngine:
    """Configurable rule-based rainfall trigger assessment engine."""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = Path(config_file or CONFIG_FILE)
        self.config = self._load_config()

        rf_cfg = self.config.get("rainfall", {})
        self.threshold_type = rf_cfg.get("threshold_type", "DEMO_OPERATIONAL_DEFAULT")
        self.disclaimer = rf_cfg.get(
            "disclaimer",
            "Operational demonstration thresholds — not calibrated against historical landslide event rainfall."
        )

        # Threshold windows
        self.thresh_1h = rf_cfg.get("1h_mm", {"watch": 20.0, "high": 40.0})
        self.thresh_24h = rf_cfg.get("24h_mm", {"watch": 50.0, "high": 100.0})
        self.thresh_3d = rf_cfg.get("3d_mm", {"watch": 100.0, "high": 200.0})
        self.thresh_7d = rf_cfg.get("7d_mm", {"watch": 150.0, "high": 300.0})

        self.thresholds = {
            "1h_mm": self.thresh_1h,
            "24h_mm": self.thresh_24h,
            "3d_mm": self.thresh_3d,
            "7d_mm": self.thresh_7d,
        }

    def _load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "rainfall": {
                "threshold_type": "DEMO_OPERATIONAL_DEFAULT",
                "disclaimer": "Operational demonstration thresholds — not calibrated against historical landslide event rainfall.",
                "1h_mm": {"watch": 20.0, "high": 40.0},
                "24h_mm": {"watch": 50.0, "high": 100.0},
                "3d_mm": {"watch": 100.0, "high": 200.0},
                "7d_mm": {"watch": 150.0, "high": 300.0},
            }
        }

    def evaluate_rainfall(self, rainfall_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate rainfall observation against thresholds.

        Parameters
        ----------
        rainfall_data : Dict[str, Any]
            Output from RainfallProvider.get_rainfall_for_location()
        """
        quality = rainfall_data.get("quality", "MISSING")
        status = rainfall_data.get("status", "MISSING")

        # 1. Unobserved / Missing Station Handling
        if quality in ["NO_RELIABLE_STATION", "MISSING"] or status == "NO_RELIABLE_LOCAL_STATION":
            reasons = []
            if quality == "NO_RELIABLE_STATION":
                reasons.append({
                    "code": "RAINFALL_NO_RELIABLE_STATION",
                    "description": rainfall_data.get("quality_notes", "No reliable station within acceptable distance.")
                })
            else:
                reasons.append({
                    "code": "RAINFALL_DATA_MISSING",
                    "description": "Rainfall sensor observation missing or unrecorded."
                })

            return {
                "trigger_level": "NO_DATA",
                "trigger_score": None,
                "trigger_score_normalized": None,
                "trigger_reasons": reasons,
                "observed_windows": {
                    "rainfall_1h": None,
                    "rainfall_24h": None,
                    "rainfall_3d": None,
                    "rainfall_7d": None,
                },
                "thresholds": self.thresholds,
                "threshold_type": self.threshold_type,
                "disclaimer": self.disclaimer,
                "data_quality": {
                    "status": quality,
                    "station": rainfall_data.get("station"),
                    "distance_km": rainfall_data.get("distance_km"),
                    "is_stale": False,
                }
            }

        # 2. Threshold Evaluation Across Windows
        observed = {
            "rainfall_1h": rainfall_data.get("rainfall_1h"),
            "rainfall_24h": rainfall_data.get("rainfall_24h"),
            "rainfall_3d": rainfall_data.get("rainfall_3d"),
            "rainfall_7d": rainfall_data.get("rainfall_7d"),
        }

        window_mapping = [
            ("rainfall_1h", "1h_mm", "1H", self.thresh_1h),
            ("rainfall_24h", "24h_mm", "24H", self.thresh_24h),
            ("rainfall_3d", "3d_mm", "3D", self.thresh_3d),
            ("rainfall_7d", "7d_mm", "7D", self.thresh_7d),
        ]

        high_hits = []
        watch_hits = []
        ratios = []
        reasons = []

        for field, key, label, cfg in window_mapping:
            val = observed[field]
            if val is not None and val >= 0.0:
                high_thresh = float(cfg["high"])
                watch_thresh = float(cfg["watch"])

                # Intensity ratio relative to high threshold
                ratio = val / high_thresh
                ratios.append(ratio)

                if val >= high_thresh:
                    high_hits.append(label)
                    reasons.append({
                        "code": f"RAINFALL_{label}_HIGH_THRESHOLD",
                        "description": (
                            f"{label} rainfall accumulation ({val:.1f} mm) exceeded High trigger threshold "
                            f"({high_thresh:.1f} mm)."
                        )
                    })
                elif val >= watch_thresh:
                    watch_hits.append(label)
                    reasons.append({
                        "code": f"RAINFALL_{label}_WATCH_THRESHOLD",
                        "description": (
                            f"{label} rainfall accumulation ({val:.1f} mm) exceeded Watch trigger threshold "
                            f"({watch_thresh:.1f} mm)."
                        )
                    })

        # 3. Trigger Level Assignment
        if high_hits:
            trigger_level = "HIGH"
        elif watch_hits:
            trigger_level = "WATCH"
        else:
            trigger_level = "NORMAL"

        # Continuous trigger score in [0.0, 1.0]
        if ratios:
            max_ratio = max(ratios)
            if trigger_level == "HIGH":
                trigger_score = round(min(1.0, 0.70 + min(0.30, (max_ratio - 1.0) * 0.15)), 4)
            elif trigger_level == "WATCH":
                trigger_score = round(0.40 + min(0.29, (max_ratio - 0.5) * 0.58), 4)
            else:
                trigger_score = round(min(0.39, max_ratio * 0.78), 4)
        else:
            trigger_score = 0.0

        # 4. Attach Data Quality & Freshness Context
        is_stale = (quality == "STALE")
        if is_stale:
            reasons.append({
                "code": "RAINFALL_DATA_STALE",
                "description": (
                    f"Rainfall observation is older than maximum freshness limit "
                    f"({rainfall_data.get('freshness', {}).get('max_acceptable_age_hours')}h). "
                    "Hazard assessment may not reflect real-time conditions."
                )
            })

        if quality == "PARTIAL":
            reasons.append({
                "code": "RAINFALL_DATA_PARTIAL",
                "description": (
                    "Rainfall observation window contains incomplete temporal telemetry (<75% coverage) "
                    "or review flags."
                )
            })

        return {
            "trigger_level": trigger_level,
            "trigger_score": trigger_score,
            "trigger_reasons": reasons,
            "observed_windows": observed,
            "thresholds": self.thresholds,
            "threshold_type": self.threshold_type,
            "disclaimer": self.disclaimer,
            "data_quality": {
                "status": quality,
                "station": rainfall_data.get("station"),
                "distance_km": rainfall_data.get("distance_km"),
                "is_stale": is_stale,
                "age_hours": rainfall_data.get("freshness", {}).get("age_hours"),
            }
        }


# Module level singleton
_TRIGGER_INSTANCE: Optional[RainfallTriggerEngine] = None


def get_rainfall_trigger_engine() -> RainfallTriggerEngine:
    global _TRIGGER_INSTANCE
    if _TRIGGER_INSTANCE is None:
        _TRIGGER_INSTANCE = RainfallTriggerEngine()
    return _TRIGGER_INSTANCE


def evaluate_rainfall_trigger(rainfall_data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate rainfall telemetry data using centralized trigger engine."""
    engine = get_rainfall_trigger_engine()
    return engine.evaluate_rainfall(rainfall_data)
