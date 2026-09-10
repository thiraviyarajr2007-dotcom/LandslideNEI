import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.inference.rainfall_trigger import RainfallTriggerEngine
from src.inference.risk_fusion import RiskFusionEngine

def run_phase5_boundary_audit():
    print("=== PHASE 5: DYNAMIC RAINFALL ENGINE BOUNDARY AUDIT ===")
    engine = RainfallTriggerEngine()
    test_vals = [0, 19.99, 20, 39.99, 40, 49.99, 50, 99.99, 100, 199.99, 200, 299.99, 300]

    def make_rf_data(rf1=None, rf24=None, rf3d=None, rf7d=None, quality="VALID", status="OK"):
        return {
            "quality": quality,
            "status": status,
            "rainfall_1h": rf1,
            "rainfall_24h": rf24,
            "rainfall_3d": rf3d,
            "rainfall_7d": rf7d,
            "station": "TEST_STN",
            "distance_km": 10.0,
            "freshness": {"age_hours": 1.0, "max_acceptable_age_hours": 6.0}
        }

    print("\n--- 1h Window (WATCH: 20.0 mm, HIGH: 40.0 mm) ---")
    for v in test_vals:
        res = engine.evaluate_rainfall(make_rf_data(rf1=v))
        print(f"  1h = {v:6.2f} mm -> Trigger Level: {res['trigger_level']:6} | Trigger Score: {res['trigger_score']}")

    print("\n--- 24h Window (WATCH: 50.0 mm, HIGH: 100.0 mm) ---")
    for v in test_vals:
        res = engine.evaluate_rainfall(make_rf_data(rf24=v))
        print(f"  24h = {v:6.2f} mm -> Trigger Level: {res['trigger_level']:6} | Trigger Score: {res['trigger_score']}")

    print("\n--- 3d Window (WATCH: 100.0 mm, HIGH: 200.0 mm) ---")
    for v in test_vals:
        res = engine.evaluate_rainfall(make_rf_data(rf3d=v))
        print(f"  3d = {v:6.2f} mm -> Trigger Level: {res['trigger_level']:6} | Trigger Score: {res['trigger_score']}")

    print("\n--- 7d Window (WATCH: 150.0 mm, HIGH: 300.0 mm) ---")
    for v in test_vals:
        res = engine.evaluate_rainfall(make_rf_data(rf7d=v))
        print(f"  7d = {v:6.2f} mm -> Trigger Level: {res['trigger_level']:6} | Trigger Score: {res['trigger_score']}")

    print("\n--- Edge / Missing Conditions ---")
    res_none = engine.evaluate_rainfall(make_rf_data())
    print(f"  All windows None -> Trigger: {res_none['trigger_level']} | Score: {res_none['trigger_score']}")

    res_missing = engine.evaluate_rainfall(make_rf_data(quality="MISSING", status="NO_RELIABLE_LOCAL_STATION"))
    print(f"  Quality MISSING / NO_RELIABLE_LOCAL_STATION -> Trigger: {res_missing['trigger_level']} | Score: {res_missing['trigger_score']}")

    res_stale = engine.evaluate_rainfall({
        "quality": "STALE", "status": "OK", "rainfall_1h": 25.0, "rainfall_24h": None,
        "rainfall_3d": None, "rainfall_7d": None, "station": "STALE_STN", "distance_km": 15.0,
        "freshness": {"age_hours": 12.0, "max_acceptable_age_hours": 6.0}
    })
    print(f"  Quality STALE with 25mm 1h -> Trigger: {res_stale['trigger_level']} | is_stale: {res_stale['data_quality']['is_stale']} | reasons: {[r['code'] for r in res_stale['trigger_reasons']]}")


def run_phase6_fusion_audit():
    print("\n=== PHASE 6: STATIC ML + DYNAMIC RAINFALL FUSION AUDIT ===")
    fusion = RiskFusionEngine()
    static_levels = ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    rainfall_statuses = ["NORMAL", "WATCH", "HIGH", "NO_DATA"]

    expected_matrix = {
        "LOW": {"NORMAL": "LOW", "WATCH": "WATCH", "HIGH": "WATCH", "NO_DATA": "LOW"},
        "MODERATE": {"NORMAL": "LOW", "WATCH": "WATCH", "HIGH": "HIGH", "NO_DATA": "WATCH"},
        "HIGH": {"NORMAL": "WATCH", "WATCH": "HIGH", "HIGH": "CRITICAL", "NO_DATA": "WATCH"},
        "VERY_HIGH": {"NORMAL": "WATCH", "WATCH": "HIGH", "HIGH": "CRITICAL", "NO_DATA": "HIGH"},
    }

    print("Checking exact 4x4 matrix against expected specifications:")
    all_matched = True
    for s_lvl in static_levels:
        for r_stat in rainfall_statuses:
            exp = expected_matrix[s_lvl][r_stat]
            s_profile = {
                "susceptibility": {
                    "score": {"LOW": 0.15, "MODERATE": 0.40, "HIGH": 0.65, "VERY_HIGH": 0.85}[s_lvl],
                    "category": s_lvl
                }
            }
            r_trig = {
                "trigger_level": r_stat,
                "trigger_score": 0.60 if r_stat != "NO_DATA" else None,
                "trigger_reasons": []
            }
            res = fusion.fuse_risk(s_profile, r_trig)
            act = res["risk_level"]
            match = (act == exp)
            if not match:
                all_matched = False
                print(f"  FAILED: {s_lvl:9} + {r_stat:7} -> got {act}, expected {exp}")
            else:
                print(f"  PASSED: {s_lvl:9} + {r_stat:7} -> {act:8} | op_fusion_score={res['operational_fusion_score']:.4f} | risk_score={res['risk_score']:.4f} | mode={res['scoring_mode']}")

    print(f"\nMatrix verification outcome: {'ALL 16 COMBINATIONS MATCHED' if all_matched else 'MISMATCH DETECTED'}")

if __name__ == "__main__":
    run_phase5_boundary_audit()
    run_phase6_fusion_audit()
