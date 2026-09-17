from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_roads_risk():
    res = client.get("/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true")
    assert res.status_code == 200
    data = res.json()
    assert "features" in data
    assert data["road_data_status"] == "UNAVAILABLE" # We moved the roads away

def test_flood_current():
    res = client.get("/api/flood/current")
    assert res.status_code == 200

def test_flood_forecast():
    res = client.get("/api/flood/forecast?rainfall=50&is_simulated=true")
    assert res.status_code == 200

def test_terrain_status():
    res = client.get("/api/terrain/status")
    assert res.status_code == 200

def test_terrain_elevation():
    res = client.get("/api/terrain/elevation?latitude=13.0827&longitude=80.2707")
    assert res.status_code == 200

def test_drainage_status():
    res = client.get("/api/drainage/status")
    assert res.status_code == 200

def test_data_status():
    res = client.get("/api/data-status")
    assert res.status_code == 200

def test_terrain_summary():
    res = client.get("/api/terrain/summary")
    assert res.status_code == 200

def test_zero_rainfall():
    # 9. ZERO-RAINFALL BEHAVIOUR
    res = client.get("/api/flood/forecast?rainfall=0&is_simulated=true")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "MODELLED"

def test_validation():
    # 11. VALIDATION -> NOT_VALIDATED
    res = client.get("/api/flood/validation")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "NOT_VALIDATED"
    assert data["metric"] is None
    assert "reason" in data
    
    prov = data.get("provenance", {})
    assert prov.get("timestamp_limitation") == "timestamp_available = false"
    assert prov.get("model_input") == "IMERG (Live)"

def test_drainage_summary():
    res = client.get("/api/drainage/summary")
    assert res.status_code == 200
    data = res.json()
    assert "feature_count" in data
    assert data["engineering_parameters_available"] == False
    assert data["hydraulic_coupling_ready"] == False

def test_drainage_nearest():
    res = client.get("/api/drainage/nearest?latitude=13.0827&longitude=80.2707")
    assert res.status_code == 200
    data = res.json()
    if data["status"] == "REAL":
        assert "nearest_swd_distance_m" in data
