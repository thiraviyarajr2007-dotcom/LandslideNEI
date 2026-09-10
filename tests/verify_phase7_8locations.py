import os
import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from api.main import app

locations = [
    {"name": "Kohima", "state": "Nagaland", "lat": 25.6740, "lon": 94.1120},
    {"name": "Shillong", "state": "Meghalaya", "lat": 25.5788, "lon": 91.8933},
    {"name": "Tezpur", "state": "Assam", "lat": 26.6528, "lon": 92.7926},
    {"name": "Namchi", "state": "Sikkim", "lat": 27.1664, "lon": 88.3639},
    {"name": "Imphal", "state": "Manipur", "lat": 24.8170, "lon": 93.9368},
    {"name": "Lunglei", "state": "Mizoram", "lat": 22.8878, "lon": 92.7397},
    {"name": "Agartala", "state": "Tripura", "lat": 23.8315, "lon": 91.2868},
    {"name": "Itanagar", "state": "Arunachal Pradesh", "lat": 27.0844, "lon": 93.6053},
]

def run_phase7_audit():
    print("==========================================================================")
    print("PHASE 7: REAL LOCATION API TEST ACROSS ALL 8 NER STATES")
    print("==========================================================================")

    client = TestClient(app)

    # Test Mode 1: Standard Operational (CWC / Local processed baseline)
    print("\n[MODE 1: Standard CWC/Local Baseline (auto_refetch=False)]")
    results_mode1 = []
    for loc in locations:
        payload = {
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "auto_refetch": False
        }
        res = client.post("/api/v1/predict", json=payload)
        assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
        data = res.json()

        susc = data.get("static_susceptibility", {})
        rf = data.get("rainfall", {})
        trig = data.get("rainfall_trigger", {})
        risk = data.get("risk", {})

        row = {
            "Location": loc["name"],
            "State": loc["state"],
            "Latitude": loc["lat"],
            "Longitude": loc["lon"],
            "Static Score": round(float(susc.get("score", 0.0)), 4),
            "Static Level": susc.get("category"),
            "Rainfall Source": rf.get("source"),
            "Station": rf.get("station"),
            "Distance": round(float(rf.get("distance_km", 0.0)), 2) if rf.get("distance_km") is not None else None,
            "Latest Rainfall Timestamp": rf.get("observation_time"),
            "Rainfall Age": rf.get("freshness", {}).get("age_hours"),
            "1h": rf.get("rainfall_1h"),
            "24h": rf.get("rainfall_24h"),
            "3d": rf.get("rainfall_3d"),
            "7d": rf.get("rainfall_7d"),
            "Rainfall Status": trig.get("trigger_level"),
            "Operational Risk": risk.get("risk_level"),
            "Operational Score": risk.get("operational_fusion_score", risk.get("risk_score")),
            "Data Quality": rf.get("quality"),
            "Provenance": rf.get("provenance", {})
        }
        results_mode1.append(row)
        print(f"  {row['Location']:10} ({row['State']:17}) | Static: {row['Static Level']:9} ({row['Static Score']:.4f}) | RF: {str(row['Rainfall Source']):4} @ {str(row['Station']):15} ({str(row['Distance']):5} km) -> Trig: {str(row['Rainfall Status']):7} | Risk: {row['Operational Risk']:8} (OpScore: {row['Operational Score']}) | Quality: {row['Data Quality']}")

    # Test Mode 2: Live Telemetry Integration (auto_refetch=True)
    print("\n[MODE 2: Live Telemetry Integration (auto_refetch=True)]")
    results_mode2 = []
    for loc in locations:
        payload = {
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "auto_refetch": True
        }
        res = client.post("/api/v1/predict", json=payload)
        assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
        data = res.json()

        susc = data.get("static_susceptibility", {})
        rf = data.get("rainfall", {})
        trig = data.get("rainfall_trigger", {})
        risk = data.get("risk", {})

        row = {
            "Location": loc["name"],
            "State": loc["state"],
            "Latitude": loc["lat"],
            "Longitude": loc["lon"],
            "Static Score": round(float(susc.get("score", 0.0)), 4),
            "Static Level": susc.get("category"),
            "Rainfall Source": rf.get("source"),
            "Station": rf.get("station"),
            "Distance": round(float(rf.get("distance_km", 0.0)), 2) if rf.get("distance_km") is not None else None,
            "Latest Rainfall Timestamp": rf.get("observation_time"),
            "Rainfall Age": rf.get("freshness", {}).get("age_hours"),
            "1h": rf.get("rainfall_1h"),
            "24h": rf.get("rainfall_24h"),
            "3d": rf.get("rainfall_3d"),
            "7d": rf.get("rainfall_7d"),
            "Rainfall Status": trig.get("trigger_level"),
            "Operational Risk": risk.get("risk_level"),
            "Operational Score": risk.get("operational_fusion_score", risk.get("risk_score")),
            "Data Quality": rf.get("quality"),
            "Provenance": rf.get("provenance", {})
        }
        results_mode2.append(row)
        print(f"  {row['Location']:10} ({row['State']:17}) | Static: {row['Static Level']:9} ({row['Static Score']:.4f}) | RF: {str(row['Rainfall Source']):12} @ {str(row['Station']):22} ({str(row['Distance']):5} km) -> Trig: {str(row['Rainfall Status']):7} | Risk: {row['Operational Risk']:8} (OpScore: {row['Operational Score']}) | Quality: {row['Data Quality']}")

    # Save results to a json file for report generation
    out_file = PROJECT_ROOT / "docs" / "phase7_8locations_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"mode1_baseline": results_mode1, "mode2_live": results_mode2}, f, indent=2)
    print(f"\nSaved Phase 7 results to {out_file}")

if __name__ == "__main__":
    run_phase7_audit()
