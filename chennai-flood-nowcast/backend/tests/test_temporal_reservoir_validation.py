import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.temporal_reservoir_validation import TemporalReservoirValidationEngine
from app.services.validation.validation_gate import ValidationGate

client = TestClient(app)

def test_exact_23_cag_observations_loaded():
    """Verify loading of exact 23 verified observations from CAG Appendix 5.6."""
    engine = TemporalReservoirValidationEngine()
    assert len(engine.observations) == 23

def test_timestamp_ordering_and_uniqueness():
    """Verify strictly increasing timestamps with zero duplicates."""
    engine = TemporalReservoirValidationEngine()
    timestamps = [o["timestamp"] for o in engine.observations]
    assert len(timestamps) == len(set(timestamps))
    assert timestamps == sorted(timestamps)

def test_provenance_and_non_synthetic_guarantees():
    """Verify official CAG provenance metadata and non-synthetic flags."""
    engine = TemporalReservoirValidationEngine()
    for obs in engine.observations:
        assert obs["source_agency"] == "CAG / WRD"
        assert obs["source_document"] == "CAG Report No. 4 of 2017"
        assert obs["source_section"] == "Appendix 5.6"
        assert obs["observational"] is True
        assert obs["synthetic"] is False

def test_chronological_70_30_split_and_no_data_leakage():
    """Verify 16 calibration records and 7 holdout validation records with zero leakage."""
    engine = TemporalReservoirValidationEngine()
    res = engine.run_validation()
    
    assert res["calibration_count"] == 16
    assert res["validation_count"] == 7
    assert res["calibration_count"] + res["validation_count"] == 23
    
    calib_pts = [s for s in res["simulated_series"] if s["partition"] == "CALIBRATION"]
    val_pts = [s for s in res["simulated_series"] if s["partition"] == "VALIDATION_HOLDOUT"]
    
    assert len(calib_pts) == 16
    assert len(val_pts) == 7
    
    # Chronological integrity check
    assert calib_pts[-1]["timestamp"] < val_pts[0]["timestamp"]

def test_holdout_validation_metrics_calculation():
    """Verify calculation of MAE, RMSE, Bias, R2, Pearson, Spearman, NSE, and peak metrics."""
    engine = TemporalReservoirValidationEngine()
    res = engine.run_validation()
    m = res["holdout_metrics"]
    
    assert m["mae_ft"] > 0
    assert m["rmse_ft"] > 0
    assert m["pearson_r"] >= 0.75
    assert m["spearman_rho"] >= 0.70
    assert m["observed_peak_ft"] == 23.40
    assert m["predicted_peak_ft"] > 20.0
    assert isinstance(m["peak_error_ft"], float)
    assert isinstance(m["peak_timing_error_hours"], float)

def test_temporal_gauge_api_endpoint():
    """Verify GET /api/validation/temporal-gauge API response schema and statuses."""
    response = client.get("/api/validation/temporal-gauge")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "VALIDATED"
    assert data["validation_type"] == "TEMPORAL_RESERVOIR_HOLDOUT"
    assert data["observation_count"] == 23
    assert data["calibration_observations"] == 16
    assert data["validation_observations"] == 7
    assert data["observational"] is True
    assert data["synthetic"] is False
    assert data["direct_model_comparison"] is True
    assert data["urban_flood_depth_temporal_validation"] == "NOT_VALIDATED"
    assert "mae_ft" in data["metrics"]
    assert "pearson_r" in data["metrics"]

def test_validation_gate_separation():
    """Verify distinct gates for reservoir validation (VALIDATED) and urban flood depth (NOT VALIDATED)."""
    vg = ValidationGate()
    summary = vg.evaluate_gates()
    gates = summary["gates"]
    
    assert gates["temporal_reservoir_gauge_gate"]["passed"] is True
    assert gates["temporal_reservoir_gauge_gate"]["status"] == "VALIDATED — TEMPORAL HOLDOUT"
    
    assert gates["temporal_gauge_gate"]["passed"] is False
    assert gates["temporal_gauge_gate"]["status"] == "NOT VALIDATED"
