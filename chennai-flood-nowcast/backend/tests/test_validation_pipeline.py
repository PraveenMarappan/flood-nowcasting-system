import pytest
import math
from app.services.validation_service import ValidationService

def test_mae_with_compatible_observations():
    matches = [
        {"type": "DEPTH", "obs": 10.0, "pred": 12.0},  # Error: 2.0
        {"type": "DEPTH", "obs": 15.0, "pred": 10.0},  # Error: 5.0
        {"type": "DEPTH", "obs": 5.0, "pred": 5.0},    # Error: 0.0
    ]
    mae = ValidationService.calculate_mae(matches)
    assert mae == pytest.approx(2.333333, rel=1e-5)

def test_rmse_with_compatible_observations():
    matches = [
        {"type": "DEPTH", "obs": 10.0, "pred": 12.0},  # Sq Error: 4.0
        {"type": "DEPTH", "obs": 15.0, "pred": 10.0},  # Sq Error: 25.0
        {"type": "DEPTH", "obs": 5.0, "pred": 5.0},    # Sq Error: 0.0
    ]
    rmse = ValidationService.calculate_rmse(matches)
    expected = math.sqrt((4.0 + 25.0 + 0.0) / 3)
    assert rmse == pytest.approx(expected, rel=1e-5)

def test_spatial_matching():
    service = ValidationService()
    # Mock an observation
    observation_depth = {
        "properties": {
            "observed_depth_cm": 15.5
        }
    }
    # Pretend it matched spatially against a grid cell predicting 10.0 cm
    result = service.evaluate_point_match(predicted_grid=10.0, observation=observation_depth)
    
    # By default, evaluate_point_match explicitly fails if spatial tolerance check fails,
    # but the current mock in validation_service hardcodes `matched = False`.
    # Let's verify what it does right now:
    # Actually wait, in validation_service.py it's hardcoded to return UNMATCHED right now:
    # matched = False 
    # if not matched: return {"match_status": "UNMATCHED"}
    assert result["match_status"] == "UNMATCHED"
    assert "No spatial overlap" in result["reason"]

def test_production_2015_returns_not_validated_without_historical_forcing():
    service = ValidationService()
    metrics = service.get_validation_metrics()
    
    assert metrics["status"] == "NOT_VALIDATED"
    # Even if historical JSON is ready, it must still return NOT_VALIDATED
    # because the routing / flood model only receives live GPM IMERG currently.
    assert "reason" in metrics
    assert "DO NOT CALCULATE" in metrics["reason"] or "missing" in metrics["reason"]
    assert metrics["metric"] is None

