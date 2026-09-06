"""
Unit Tests for Static-Dynamic Risk Fusion Engine (Phase 8H)
===========================================================
Tests:
10. Low susceptibility + normal rainfall -> LOW
11. High susceptibility + normal rainfall -> WATCH
12. High susceptibility + rainfall watch -> HIGH
13. Very high susceptibility + rainfall high -> CRITICAL
14. Missing rainfall (NO_DATA) -> Precautionary tier with UNKNOWN/NO_DATA reasons
15. Stale rainfall -> Includes STALE reason code
16. Low susceptibility + high rainfall -> WATCH (not CRITICAL)
17. Full 16-combination matrix coverage
18. Operational risk score bounds [0.0, 1.0]
"""

import pytest
from src.inference.risk_fusion import RiskFusionEngine, fuse_static_and_dynamic_risk


@pytest.fixture
def fusion_engine():
    return RiskFusionEngine()


def _make_static(score: float, category: str):
    return {
        "susceptibility": {
            "score": score,
            "category": category,
            "category_label": f"{category.title()} Susceptibility",
        }
    }


def _make_trigger(level: str, score: float = None, is_stale: bool = False, reasons=None):
    r_list = list(reasons or [])
    if is_stale:
        r_list.append({"code": "RAINFALL_DATA_STALE", "description": "Rainfall data is stale."})
    return {
        "trigger_level": level,
        "trigger_score": score,
        "trigger_reasons": r_list,
        "data_quality": {"is_stale": is_stale},
    }


def test_low_susc_normal_rainfall(fusion_engine):
    # Rule 1: LOW susc + normal rain -> LOW
    static = _make_static(0.12, "LOW")
    trigger = _make_trigger("NORMAL", 0.10)
    res = fusion_engine.fuse_risk(static, trigger)

    assert res["risk_level"] == "LOW"
    assert 0.0 <= res["risk_score"] <= 1.0
    codes = [r["code"] for r in res["reasons"]]
    assert "STATIC_LOW_SUSCEPTIBILITY" in codes


def test_high_susc_normal_rainfall(fusion_engine):
    # High susceptibility retains baseline watchfulness even with normal rain -> WATCH
    static = _make_static(0.68, "HIGH")
    trigger = _make_trigger("NORMAL", 0.05)
    res = fusion_engine.fuse_risk(static, trigger)

    assert res["risk_level"] == "WATCH"
    codes = [r["code"] for r in res["reasons"]]
    assert "STATIC_HIGH_SUSCEPTIBILITY" in codes


def test_high_susc_rainfall_watch(fusion_engine):
    # Rule 3: HIGH susc + rainfall WATCH -> HIGH
    static = _make_static(0.72, "HIGH")
    trigger = _make_trigger("WATCH", 0.55)
    res = fusion_engine.fuse_risk(static, trigger)

    assert res["risk_level"] == "HIGH"
    codes = [r["code"] for r in res["reasons"]]
    assert "STATIC_HIGH_SUSCEPTIBILITY" in codes
    assert "RAINFALL_WATCH_TRIGGER" in codes


def test_very_high_susc_rainfall_high(fusion_engine):
    # Rule 4: VERY_HIGH susc + rainfall HIGH -> CRITICAL
    static = _make_static(0.88, "VERY_HIGH")
    trigger = _make_trigger("HIGH", 0.90)
    res = fusion_engine.fuse_risk(static, trigger)

    assert res["risk_level"] == "CRITICAL"
    codes = [r["code"] for r in res["reasons"]]
    assert "STATIC_VERY_HIGH_SUSCEPTIBILITY" in codes
    assert "RAINFALL_HIGH_TRIGGER" in codes


def test_missing_rainfall_scenarios(fusion_engine):
    # Rule 5: HIGH/VERY_HIGH susc + NO_DATA -> retain susceptibility-driven elevated concern
    static_high = _make_static(0.70, "HIGH")
    trigger_nodata = _make_trigger("NO_DATA", None)
    res_high = fusion_engine.fuse_risk(static_high, trigger_nodata)

    assert res_high["risk_level"] == "WATCH"
    assert res_high["risk_score"] == 0.70
    codes_high = [r["code"] for r in res_high["reasons"]]
    assert "STATIC_HIGH_SUSCEPTIBILITY_RAINFALL_UNOBSERVED" in codes_high

    static_vhigh = _make_static(0.92, "VERY_HIGH")
    res_vhigh = fusion_engine.fuse_risk(static_vhigh, trigger_nodata)
    assert res_vhigh["risk_level"] == "HIGH"
    codes_vhigh = [r["code"] for r in res_vhigh["reasons"]]
    assert "STATIC_VERY_HIGH_SUSCEPTIBILITY_RAINFALL_UNOBSERVED" in codes_vhigh


def test_stale_rainfall_flagging(fusion_engine):
    static = _make_static(0.65, "HIGH")
    trigger_stale = _make_trigger("WATCH", 0.50, is_stale=True)
    res = fusion_engine.fuse_risk(static, trigger_stale)

    codes = [r["code"] for r in res["reasons"]]
    assert "RAINFALL_DATA_STALE" in codes


def test_low_susc_high_rainfall(fusion_engine):
    # Rule 6: LOW susc + high rainfall -> WATCH (dampened, NOT CRITICAL)
    static = _make_static(0.10, "LOW")
    trigger = _make_trigger("HIGH", 0.85)
    res = fusion_engine.fuse_risk(static, trigger)

    assert res["risk_level"] == "WATCH"
    assert res["risk_level"] != "CRITICAL"


def test_full_matrix_combinations(fusion_engine):
    expected_matrix = {
        ("LOW", "NORMAL"): "LOW",
        ("LOW", "WATCH"): "WATCH",
        ("LOW", "HIGH"): "WATCH",
        ("LOW", "NO_DATA"): "LOW",
        ("MODERATE", "NORMAL"): "LOW",
        ("MODERATE", "WATCH"): "WATCH",
        ("MODERATE", "HIGH"): "HIGH",
        ("MODERATE", "NO_DATA"): "WATCH",
        ("HIGH", "NORMAL"): "WATCH",
        ("HIGH", "WATCH"): "HIGH",
        ("HIGH", "HIGH"): "CRITICAL",
        ("HIGH", "NO_DATA"): "WATCH",
        ("VERY_HIGH", "NORMAL"): "WATCH",
        ("VERY_HIGH", "WATCH"): "HIGH",
        ("VERY_HIGH", "HIGH"): "CRITICAL",
        ("VERY_HIGH", "NO_DATA"): "HIGH",
    }

    scores = {"LOW": 0.1, "MODERATE": 0.35, "HIGH": 0.65, "VERY_HIGH": 0.85}
    trig_scores = {"NORMAL": 0.1, "WATCH": 0.5, "HIGH": 0.8, "NO_DATA": None}

    for (susc_cat, trig_lvl), expected_risk in expected_matrix.items():
        s = _make_static(scores[susc_cat], susc_cat)
        t = _make_trigger(trig_lvl, trig_scores[trig_lvl])
        res = fusion_engine.fuse_risk(s, t)
        assert res["risk_level"] == expected_risk, f"Failed for {susc_cat} + {trig_lvl}"
        assert 0.0 <= res["risk_score"] <= 1.0


def test_scoring_modes(fusion_engine):
    # Mode 1: Dual Layer
    res1 = fusion_engine.fuse_risk(_make_static(0.60, "HIGH"), _make_trigger("WATCH", 0.40))
    assert res1["scoring_mode"] == "DUAL_LAYER_WEIGHTED_SYNTHESIS"
    assert res1["operational_fusion_score"] == 0.50
    assert res1["risk_score"] == 0.50  # Backwards compatibility alias

    # Mode 2: Static Baseline Only
    res2 = fusion_engine.fuse_risk(_make_static(0.60, "HIGH"), _make_trigger("NO_DATA", None))
    assert res2["scoring_mode"] == "STATIC_BASELINE_ONLY_RAINFALL_UNOBSERVED"
    assert res2["operational_fusion_score"] == 0.60
    assert res2["risk_score"] == 0.60


def test_operational_fusion_score_semantics(fusion_engine):
    static = _make_static(0.75, "HIGH")
    trigger = _make_trigger("WATCH", 0.50)
    res = fusion_engine.fuse_risk(static, trigger)

    assert "operational_fusion_score" in res
    assert "risk_score" in res
    assert res["operational_fusion_score"] == res["risk_score"]
    assert 0.0 <= res["operational_fusion_score"] <= 1.0

    assert "score_semantics" in res
    assert "engineering synthesis score used for ordering/visualization" in res["score_semantics"]
    assert "not a probability" in res["score_semantics"]

    # Check limitation #5 updated
    lim5 = res["scientific_limitations"][4]
    assert "Operational fusion score is not a calibrated event probability" in lim5

