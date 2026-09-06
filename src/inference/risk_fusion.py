"""
Static Susceptibility & Dynamic Rainfall Risk Fusion Layer
==========================================================
Combines Phase 8G static terrain susceptibility with dynamic operational
rainfall triggers using a transparent, deterministic decision matrix.

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. STATIC SUSCEPTIBILITY != CURRENT HAZARD.
2. The static model reflects 2014 mapped terrain predisposition (slope, elevation, soil, LULC).
3. The dynamic trigger reflects real-time or operational telemetry (CWC 1h, 24h, 3d, 7d).
4. No additional ML model is trained for fusion; it uses an explicit, auditable rule matrix.
5. The operational risk score is NOT a calibrated probability of landslide occurrence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "risk_thresholds.json"

STANDARD_LIMITATIONS = [
    (
        "1. Static susceptibility is not an event-time warning: A high static score indicates terrain "
        "predisposition to failure based on historical baseline features, not that a landslide is occurring."
    ),
    (
        "2. Rainfall thresholds are operational/demo defaults: The rainfall thresholds (1h, 24h, 3d, 7d) are "
        "engineering demonstration defaults and are NOT calibrated against historical 2014 landslide events."
    ),
    (
        "3. Rainfall data represents telemetry station location: Sensor observations may differ from rainfall "
        "at the exact query coordinates due to montane micro-climates."
    ),
    (
        "4. Telemetry data may be incomplete or stale: Observations with <75% window coverage or age >6h "
        "introduce operational uncertainty into the dynamic trigger."
    ),
    (
        "5. Operational fusion score is not a calibrated event probability: The operational_fusion_score is "
        "an engineering synthesis score used for ordering and visualization, and must not be interpreted as "
        "a percentage likelihood or calibrated probability of slope failure. The categorical risk_level is "
        "the authoritative operational decision."
    ),
]


class RiskFusionEngine:
    """Transparent rule-based risk fusion engine."""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = Path(config_file or CONFIG_FILE)
        self.config = self._load_config()

        fusion_cfg = self.config.get("risk_fusion", {})
        self.matrix = fusion_cfg.get("matrix", {
            "LOW": {"NORMAL": "LOW", "WATCH": "WATCH", "HIGH": "WATCH", "NO_DATA": "LOW"},
            "MODERATE": {"NORMAL": "LOW", "WATCH": "WATCH", "HIGH": "HIGH", "NO_DATA": "WATCH"},
            "HIGH": {"NORMAL": "WATCH", "WATCH": "HIGH", "HIGH": "CRITICAL", "NO_DATA": "WATCH"},
            "VERY_HIGH": {"NORMAL": "WATCH", "WATCH": "HIGH", "HIGH": "CRITICAL", "NO_DATA": "HIGH"},
        })
        self.weights = fusion_cfg.get("scoring", {"susceptibility_weight": 0.5, "trigger_weight": 0.5})

    def _load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "risk_fusion": {
                "matrix": {
                    "LOW": {"NORMAL": "LOW", "WATCH": "WATCH", "HIGH": "WATCH", "NO_DATA": "LOW"},
                    "MODERATE": {"NORMAL": "LOW", "WATCH": "WATCH", "HIGH": "HIGH", "NO_DATA": "WATCH"},
                    "HIGH": {"NORMAL": "WATCH", "WATCH": "HIGH", "HIGH": "CRITICAL", "NO_DATA": "WATCH"},
                    "VERY_HIGH": {"NORMAL": "WATCH", "WATCH": "HIGH", "HIGH": "CRITICAL", "NO_DATA": "HIGH"},
                },
                "scoring": {"susceptibility_weight": 0.5, "trigger_weight": 0.5}
            }
        }

    def fuse_risk(
        self,
        static_profile: Dict[str, Any],
        rainfall_trigger: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Synthesize static susceptibility and dynamic rainfall trigger.

        Parameters
        ----------
        static_profile : Dict[str, Any]
            Output from LocationProfiler.profile_location().
        rainfall_trigger : Dict[str, Any]
            Output from RainfallTriggerEngine.evaluate_rainfall().
        """
        # 1. Extract static susceptibility
        susc_dict = static_profile.get("susceptibility", {})
        susc_score = float(susc_dict.get("score", 0.0))
        susc_category = str(susc_dict.get("category", "LOW")).upper()

        # 2. Extract dynamic trigger
        trigger_level = str(rainfall_trigger.get("trigger_level", "NO_DATA")).upper()
        trigger_score = rainfall_trigger.get("trigger_score")

        # 3. Rule Matrix Lookup
        cat_matrix = self.matrix.get(susc_category, {})
        risk_level = cat_matrix.get(trigger_level, "WATCH")

        # 4. Composite Operational Risk Score Calculation
        w_susc = float(self.weights.get("susceptibility_weight", 0.5))
        w_trig = float(self.weights.get("trigger_weight", 0.5))

        if trigger_score is not None:
            comp_score = (w_susc * susc_score) + (w_trig * float(trigger_score))
            operational_fusion_score = round(min(1.0, max(0.0, comp_score)), 4)
            scoring_mode = "DUAL_LAYER_WEIGHTED_SYNTHESIS"
        else:
            # When dynamic rainfall is unobserved, static susceptibility score serves as baseline
            operational_fusion_score = round(susc_score, 4)
            scoring_mode = "STATIC_BASELINE_ONLY_RAINFALL_UNOBSERVED"

        score_semantics = (
            "This is an engineering synthesis score used for ordering/visualization. "
            "It is not a probability, calibrated hazard score, or empirically validated landslide risk estimate."
        )

        # 5. Synthesize Transparent Reason Codes
        reasons: List[Dict[str, str]] = []

        # Static contribution
        reasons.append({
            "code": f"STATIC_{susc_category}_SUSCEPTIBILITY",
            "description": (
                f"Physical terrain factors (elevation, slope, aspect, relief, soil, LULC) indicate "
                f"{susc_category} static susceptibility (score: {susc_score:.4f})."
            )
        })

        # Dynamic contribution
        if trigger_level != "NO_DATA":
            reasons.append({
                "code": f"RAINFALL_{trigger_level}_TRIGGER",
                "description": (
                    f"Current meteorological telemetry indicates {trigger_level} operational rainfall trigger level."
                )
            })
        else:
            if susc_category in ["HIGH", "VERY_HIGH"]:
                reasons.append({
                    "code": f"STATIC_{susc_category}_SUSCEPTIBILITY_RAINFALL_UNOBSERVED",
                    "description": (
                        f"{susc_category} static susceptibility maintains elevated baseline vigilance "
                        "despite unobserved local rainfall."
                    )
                })

        # Forward all specific trigger reasons (threshold breaches, quality flags)
        for tr in rainfall_trigger.get("trigger_reasons", []):
            reasons.append(tr)

        # Risk tier label formatting
        tier_labels = {
            "LOW": "Low Operational Risk",
            "WATCH": "Watch Operational Risk",
            "HIGH": "High Operational Risk",
            "CRITICAL": "Critical Operational Risk",
        }

        tier_actions = {
            "LOW": "Routine monitoring; baseline susceptibility is low and no severe rainfall trigger observed.",
            "WATCH": "Advisory vigilance; elevated static terrain predisposition or moderate rainfall trigger.",
            "HIGH": "Operational alert; significant slope failure predisposition combined with active rainfall.",
            "CRITICAL": "Emergency alert; very high susceptibility terrain coupled with intense rainfall trigger.",
        }

        return {
            "risk_level": risk_level,
            "risk_label": tier_labels.get(risk_level, risk_level),
            "operational_fusion_score": operational_fusion_score,
            "risk_score": operational_fusion_score,  # Retained as backwards-compatible alias
            "score_semantics": score_semantics,
            "scoring_mode": scoring_mode,
            "susceptibility_score": susc_score,
            "susceptibility_category": susc_category,
            "rainfall_trigger_level": trigger_level,
            "rainfall_trigger_score": trigger_score,
            "reasons": reasons,
            "operational_action": tier_actions.get(risk_level, ""),
            "matrix_lookup": {
                "susceptibility_tier": susc_category,
                "rainfall_trigger_tier": trigger_level,
                "resulting_risk_tier": risk_level,
            },
            "scientific_limitations": STANDARD_LIMITATIONS,
        }


# Module level singleton
_FUSION_INSTANCE: Optional[RiskFusionEngine] = None


def get_risk_fusion_engine() -> RiskFusionEngine:
    global _FUSION_INSTANCE
    if _FUSION_INSTANCE is None:
        _FUSION_INSTANCE = RiskFusionEngine()
    return _FUSION_INSTANCE


def fuse_static_and_dynamic_risk(
    static_profile: Dict[str, Any],
    rainfall_trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """Module-level convenience function for static-dynamic risk fusion."""
    engine = get_risk_fusion_engine()
    return engine.fuse_risk(static_profile, rainfall_trigger)
