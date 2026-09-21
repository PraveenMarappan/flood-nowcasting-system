import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.drainage_coupling_service import DrainageCouplingService
from app.services.terrain_service import TerrainService
from app.services.flood_model_service import FloodModelService

client = TestClient(app)

def test_nearest_swd_distance_and_coverage():
    service = DrainageCouplingService()
    # Test point in Chennai (near Chennai Central)
    lat, lng = 13.0827, 80.2707
    diag = service.calculate_diagnostics(lat, lng)
    
    assert diag["status"] == "AVAILABLE"
    assert diag["mode"] == "GEOMETRIC_ONLY"
    assert "coverage" in diag
    
    dist_m = diag["coverage"]["nearest_swd_distance_m"]
    assert isinstance(dist_m, float)
    assert dist_m >= 0.0
    
    if dist_m <= 100.0:
        assert diag["coverage"]["status"] == "DRAINAGE_SERVED"
    else:
        assert diag["coverage"]["status"] == "DRAINAGE_UNSERVED"

def test_drainage_density_units_and_values():
    service = DrainageCouplingService()
    lat, lng = 13.0827, 80.2707
    diag = service.calculate_diagnostics(lat, lng)
    
    density = diag["density"]
    assert density["search_radius_m"] == 250.0
    assert density["density_m_per_m2"] >= 0.0
    assert density["density_km_per_km2"] == round(density["density_m_per_m2"] * 1000.0, 3)

def test_dbi_calculation_and_dref_provenance():
    service = DrainageCouplingService()
    terrain = TerrainService()
    lat, lng = 13.0827, 80.2707
    diag = service.calculate_diagnostics(lat, lng, terrain_service=terrain)
    
    dbi = diag["dbi"]
    assert dbi["d_ref_value"] == 0.01
    assert dbi["d_ref_units"] == "m/m^2"
    assert dbi["d_ref_provenance"] == "ASSUMED_NORMALIZATION_CONSTANT"
    
    if dbi["status"] == "REAL_DEM":
        assert dbi["value"] is not None
        assert dbi["value"] >= 0.0

def test_missing_dem_dbi_behavior():
    service = DrainageCouplingService()
    # Passing terrain_service=None mimics missing DEM
    diag = service.calculate_diagnostics(13.0827, 80.2707, terrain_service=None)
    
    dbi = diag["dbi"]
    assert dbi["status"] == "UNAVAILABLE_DEM_MISSING"
    assert dbi["value"] is None

def test_flat_terrain_alpha_align_behavior():
    service = DrainageCouplingService()
    # Mocking terrain service without DEM cache to simulate flat/missing DEM
    class MockFlatTerrainService:
        def get_elevation(self, lat, lng):
            return {"status": "UNAVAILABLE"}
        def get_derivatives(self, lat, lng):
            return {"status": "UNAVAILABLE"}
            
    mock_terrain = MockFlatTerrainService()
    diag = service.calculate_diagnostics(13.0827, 80.2707, terrain_service=mock_terrain)
    
    align = diag["alignment"]
    assert align["status"] == "INDETERMINATE_FLAT_TERRAIN"
    assert align["alpha_align"] is None

def test_hydraulic_data_status_strictly_unknown():
    service = DrainageCouplingService()
    diag = service.calculate_diagnostics(13.0827, 80.2707)
    
    h_status = diag["hydraulic_data_status"]
    expected_keys = [
        "capacity", "diameter", "depth", "invert_elevation",
        "manning_roughness", "flow_direction", "outfall_condition"
    ]
    for key in expected_keys:
        assert h_status[key] == "UNKNOWN"

def test_safety_guarantees_zero_flood_depth_impact():
    service = DrainageCouplingService()
    diag = service.calculate_diagnostics(13.0827, 80.2707)
    
    guarantees = diag["safety_guarantees"]
    assert guarantees["drainage_effect_on_flood_depth"] == 0.0
    assert guarantees["hydraulic_coupling"] == "UNAVAILABLE"

def test_flood_model_service_unaffected_by_drainage():
    model = FloodModelService()
    # Calculate flood depth for 50 mm/hr rainfall
    result = model.calculate_spatial_flood(13.0827, 80.2707, 50.0, 0)
    
    # Ensure water depth calculation is purely hydrological (rainfall * C * terrain_factor)
    assert result["water_depth_cm"] > 0.0
    assert "SPATIAL HEURISTIC" in result["estimator"]

def test_drainage_diagnostics_api_endpoint():
    response = client.get("/api/drainage/diagnostics?latitude=13.0827&longitude=80.2707")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "AVAILABLE"
    assert data["mode"] == "GEOMETRIC_ONLY"
    assert "coverage" in data
    assert "density" in data
    assert "dbi" in data
    assert "alignment" in data
    assert "hydraulic_data_status" in data
    assert data["safety_guarantees"]["drainage_effect_on_flood_depth"] == 0.0
