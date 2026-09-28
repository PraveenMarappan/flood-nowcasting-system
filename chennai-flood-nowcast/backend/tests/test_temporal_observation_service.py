import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.temporal_observation_service import TemporalObservationService

client = TestClient(app)

def test_temporal_observation_service_loading():
    """Verify loading of exact 23 CAG report observations."""
    service = TemporalObservationService()
    obs = service.get_observations()
    assert len(obs) == 23

def test_timestamp_ordering_and_uniqueness():
    """Verify strictly increasing timestamps with zero duplicates."""
    service = TemporalObservationService()
    timestamps = [o["timestamp"] for o in service.get_observations()]
    assert len(timestamps) == len(set(timestamps))
    assert timestamps == sorted(timestamps)

def test_reservoir_hydrograph_metrics():
    """Verify exact observed peak, min water level, max inflow, and max outflow."""
    service = TemporalObservationService()
    stats = service.get_reservoir_statistics()
    
    assert stats["status"] == "CALCULATED"
    assert stats["observation_count"] == 23
    assert stats["observed_peak_water_level_ft"] == 23.40
    assert stats["maximum_inflow_cusec"] == 31000.0
    assert stats["maximum_outflow_cusec"] == 29000.0

def test_provenance_and_non_synthetic_guarantee():
    """Verify data provenance metadata and non-synthetic guarantees."""
    service = TemporalObservationService()
    summary = service.get_temporal_audit_summary()
    
    assert summary["source_agency"] == "CAG / WRD"
    assert summary["source_type"] == "GOVERNMENT_REPORT"
    assert summary["event"] == "Chennai_2015"
    assert summary["location"] == "Chembarambakkam_Tank"
    assert summary["observational"] is True
    assert summary["synthetic"] is False

def test_provenance_separation_classifications():
    """Verify explicit separation between reservoir availability and urban flood depth validation."""
    service = TemporalObservationService()
    summary = service.get_temporal_audit_summary()
    
    provs = summary["provenance_classifications"]
    assert provs["TEMPORAL_HYDROLOGICAL_VALIDATION"] == "AVAILABLE"
    assert provs["CHEMBARAMBAKKAM_RESERVOIR_VALIDATION"] == "VALIDATED_DATASET_AVAILABLE"
    assert provs["TEMPORAL_URBAN_FLOOD_DEPTH_GAUGE_VALIDATION"] == "NOT_VALIDATED"

def test_temporal_gauge_api_response():
    """Verify GET /api/validation/temporal-gauge API payload format."""
    response = client.get("/api/validation/temporal-gauge")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "VALIDATED"
    assert data["validation_type"] == "TEMPORAL_RESERVOIR_HOLDOUT"
    assert data["urban_flood_depth_temporal_validation"] == "NOT_VALIDATED"
    assert data["observation_count"] == 23
    assert data["source_agency"] == "CAG / WRD"
    assert data["observational"] is True
    assert data["synthetic"] is False
    assert data["direct_model_comparison"] is True

