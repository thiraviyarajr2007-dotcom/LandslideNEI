"""
Test Suite: Operational 3D Location Intelligence Workflow
=========================================================
Tests the complete end-to-end integration:
1. Real DEM terrain mesh querying across diverse NER states.
2. Real-time operational risk prediction (/api/v1/predict).
3. Model A Random Forest static susceptibility + CWC telemetry + Risk fusion.
4. Verified historical landslide event layer (/api/v1/layers/historical-landslides).
5. Out-of-domain guardrail enforcement (Delhi / Bangalore rejected).
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestOperational3DWorkflow:
    """Validate end-to-end operational location intelligence pipeline."""

    @pytest.mark.parametrize("name,lat,lon,expected_state", [
        ("Kohima NH-29", 25.6740, 94.1120, "Nagaland"),
        ("Shillong Upland", 25.5788, 91.8933, "Meghalaya"),
        ("Tezpur Sonitpur", 26.6338, 92.7926, "Assam"),
        ("Namchi South Sikkim", 27.1667, 88.3500, "Sikkim"),
        ("Imphal Valley", 24.8170, 93.9368, "Manipur"),
        ("Lunglei Ridge", 22.8872, 92.7388, "Mizoram"),
        ("Agartala Baramura", 23.8315, 91.2868, "Tripura"),
        ("Itanagar Foothills", 27.0844, 93.6053, "Arunachal Pradesh"),
    ])
    def test_end_to_end_location_workflow(self, name, lat, lon, expected_state):
        """Verify real DEM mesh + real operational prediction for 8 NER states."""
        # 1. Query 3D DEM mesh
        mesh_res = client.get(f"/api/v1/terrain/mesh?latitude={lat}&longitude={lon}&radius_km=10.0&grid_size=128")
        assert mesh_res.status_code == 200, f"Mesh failed for {name}: {mesh_res.text}"
        mesh_data = mesh_res.json()
        assert mesh_data["status"] == "SUCCESS"
        assert len(mesh_data["elevations"]) in [4096, 16384]
        assert mesh_data["elevation_stats"]["min_m"] is not None
        assert mesh_data["elevation_stats"]["max_m"] >= mesh_data["elevation_stats"]["min_m"]
        assert "synthetic" not in mesh_data.get("dem_source", "").lower()

        # 2. Run operational risk prediction
        pred_res = client.post("/api/v1/predict", json={
            "latitude": lat,
            "longitude": lon,
            "auto_refetch": False
        })
        assert pred_res.status_code == 200, f"Prediction failed for {name}: {pred_res.text}"
        pred_data = pred_res.json()

        # Check location
        loc = pred_data["location"]
        assert loc["supported_domain"] is True

        # Check Model A Static Susceptibility
        susc = pred_data["static_susceptibility"]
        assert susc["score"] is not None
        assert 0.0 <= susc["score"] <= 1.0
        assert susc["category"] in ["LOW", "MODERATE", "HIGH", "VERY HIGH", "VERY_HIGH", "CRITICAL"]
        assert susc["terrain"]["elevation_m"] is not None
        assert susc["terrain"]["slope_deg"] is not None
        assert susc["terrain"]["aspect_deg"] is not None

        # Check Rainfall Telemetry
        rain = pred_data["rainfall"]
        if rain["distance_km"] is not None and rain["distance_km"] > 50.0:
            assert rain["source"] == "NO_LOCAL_DATA"
            assert rain["status"] == "NO_RELIABLE_LOCAL_STATION"
            assert rain["operational_status"] == "NO_RELIABLE_LOCAL_DATA"
            assert rain["rainfall_24h"] is None
            assert pred_data["rainfall_trigger"]["trigger_level"] == "NO_DATA"
        else:
            assert rain["source"] in ["CWC", "OPEN_METEO_REALTIME", "OPEN_METEO_API"]
            if rain["distance_km"] is not None:
                assert rain["distance_km"] <= 50.0

        # Check Operational Risk Fusion
        risk = pred_data["risk"]
        assert risk["level"] in ["LOW", "WATCH", "HIGH", "CRITICAL"]
        assert 0.0 <= risk["operational_fusion_score"] <= 1.0
        assert len(risk.get("score_semantics", "")) > 0

    def test_historical_landslide_layer_integrity(self):
        """Verify 75 verified events are served without fabrication."""
        res = client.get("/api/v1/layers/historical-landslides")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "CONNECTED"
        assert data["count"] == 75
        assert len(data["events"]) == 75

        # Inspect first event
        evt = data["events"][0]
        assert "event_id" in evt
        assert "latitude" in evt
        assert "longitude" in evt
        assert 21.0 <= evt["latitude"] <= 30.0
        assert 88.0 <= evt["longitude"] <= 98.0
        assert "NESAC" in evt["source_id"]

    def test_out_of_domain_guardrails(self):
        """Verify out-of-domain coordinates fail gracefully."""
        # Delhi
        mesh_res = client.get("/api/v1/terrain/mesh?latitude=28.6139&longitude=77.2090")
        assert mesh_res.status_code == 404

        pred_res = client.post("/api/v1/predict", json={
            "latitude": 28.6139,
            "longitude": 77.2090
        })
        assert pred_res.status_code == 400
        err_msg = pred_res.json().get("error", {}).get("message", "")
        assert "outside" in err_msg.lower()

    def test_model_a_distinct_feature_vectors_and_scores(self):
        """
        Verify that different geographical locations receive different genuine feature vectors
        and produce distinct Model A susceptibility scores (NOT identical 0.541).
        """
        coords = [
            (26.6338, 92.7926),  # Tezpur plain
            (25.6740, 94.1120),  # Kohima hill
            (27.1667, 88.3500),  # Namchi steep ridge
            (24.8170, 93.9368),  # Imphal valley
        ]
        scores = []
        elevs = []
        slopes = []

        for lat, lon in coords:
            res = client.post("/api/v1/predict", json={"latitude": lat, "longitude": lon, "auto_refetch": False})
            assert res.status_code == 200
            data = res.json()
            susc = data["static_susceptibility"]
            terrain = susc["terrain"]
            scores.append(round(susc["score"], 4))
            elevs.append(terrain["elevation_m"])
            slopes.append(terrain["slope_deg"])

        # Confirm all elevation and slope values are distinct real observations
        assert len(set(elevs)) == len(coords), f"Elevations must be distinct: {elevs}"
        assert len(set(slopes)) == len(coords), f"Slopes must be distinct: {slopes}"

        # Confirm Model A scores are distinct and NOT all 0.541
        assert len(set(scores)) > 1, f"Model A scores must not be identical: {scores}"
        assert not all(s == 0.541 for s in scores), "Scores must not be stuck at 0.541"

    def test_cwc_distance_rule_and_fusion_semantics(self):
        """
        Verify that stations > 50km (e.g. Lunglei at ~111km) produce NO_RELIABLE_LOCAL_DATA,
        rainfall values are None, and risk fusion respects NO_DATA without treating distant stations as local.
        """
        res = client.post("/api/v1/predict", json={"latitude": 22.8872, "longitude": 92.7388, "auto_refetch": False})
        assert res.status_code == 200
        data = res.json()
        rain = data["rainfall"]
        trig = data["rainfall_trigger"]
        risk = data["risk"]

        assert rain["distance_km"] > 50.0
        assert rain["status"] == "NO_RELIABLE_LOCAL_STATION"
        assert rain["operational_status"] == "NO_RELIABLE_LOCAL_DATA"
        assert rain["source"] == "NO_LOCAL_DATA"
        assert rain["nearest_station"] is not None
        assert rain["nearest_station_distance_km"] > 50.0

        # Rainfall accumulation must be None, NOT 0.0 mm
        assert rain["rainfall_24h"] is None
        assert rain["rainfall_1h"] is None

        # Trigger must be NO_DATA
        assert trig["trigger_level"] == "NO_DATA"

        # Risk fusion must use static baseline
        assert risk["scoring_mode"] == "STATIC_BASELINE_ONLY_RAINFALL_UNOBSERVED"
        assert risk["operational_fusion_score"] == round(data["static_susceptibility"]["score"], 4)
