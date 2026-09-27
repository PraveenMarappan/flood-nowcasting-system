import pytest
from app.services.validation.depth_observation_loader import DepthObservationLoader
from app.services.validation.depth_event_matcher import DepthEventMatcher, haversine_distance_m
from app.services.validation.depth_metrics import calculate_depth_metrics
from app.services.validation.numerical_depth_validation import run_numerical_depth_validation, PREDEFINED_ACCEPTANCE_CRITERIA

def test_kml_loading_and_conversion():
    loader = DepthObservationLoader()
    obs = loader.load_opencity_depth_observations()
    assert len(obs) == 192, f"Expected 192 valid OpenCity records, got {len(obs)}"
    
    first = obs[0]
    assert "latitude" in first
    assert "longitude" in first
    assert "observed_depth_cm" in first
    assert first["observed_depth_cm"] == round(first["observed_depth_inches"] * 2.54, 2)
    assert not any(o["observed_depth_cm"] < 0 for o in obs), "No negative depth values should be present"

def test_haversine_distance():
    # Distance between two identical points should be 0.0
    dist = haversine_distance_m(13.0827, 80.2707, 13.0827, 80.2707)
    assert dist == 0.0

def test_calibration_holdout_partitioning():
    loader = DepthObservationLoader()
    obs = loader.load_opencity_depth_observations()
    
    cal_set, holdout_set = DepthEventMatcher.partition_calibration_holdout(obs, holdout_count=39)
    assert len(cal_set) == 153, f"Expected 153 calibration records, got {len(cal_set)}"
    assert len(holdout_set) == 39, f"Expected 39 holdout records, got {len(holdout_set)}"
    
    cal_ids = set(o["observation_id"] for o in cal_set)
    holdout_ids = set(o["observation_id"] for o in holdout_set)
    assert len(cal_ids.intersection(holdout_ids)) == 0, "Data leakage detected between calibration and holdout sets"

def test_metrics_calculation_correctness():
    dummy_records = [
        {"observed_depth_cm": 20.0, "predicted_depth_cm": 15.0}, # err -5, abs 5
        {"observed_depth_cm": 30.0, "predicted_depth_cm": 35.0}, # err +5, abs 5
        {"observed_depth_cm": 40.0, "predicted_depth_cm": 40.0}, # err 0, abs 0
    ]
    res = calculate_depth_metrics(dummy_records)
    assert res["mae_cm"] == round((5 + 5 + 0) / 3, 2)
    assert res["bias_cm"] == round((-5 + 5 + 0) / 3, 2)
    assert res["sample_count"] == 3

def test_numerical_depth_validation_pipeline():
    res = run_numerical_depth_validation()
    assert res["total_observations"] == 192
    assert res["calibration_count"] == 153
    assert res["spatial_holdout_count"] == 39
    assert res["status_summary"]["spatial_holdout_validation_status"] in ["SPATIAL HOLDOUT VALIDATED", "SPATIAL HOLDOUT FAILED"]
    assert res["status_summary"]["overall_system_status"] == "PARTIALLY VALIDATED"
