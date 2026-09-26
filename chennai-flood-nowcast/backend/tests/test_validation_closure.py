import pytest
import json
from pathlib import Path
from app.services.validation.event_matcher import EventMatcher
from app.services.validation.validation_gate import ValidationGate
from app.services.validation.status_evaluator import ValidationStatusEvaluator
from app.services.validation_service import ValidationService

def test_event_matcher_wgs84_distance():
    matcher = EventMatcher()
    dist = matcher.calculate_distance_m(13.0827, 80.2707, 13.0827, 80.2707)
    assert dist == 0.0

def test_event_matcher_chennai_2015_records():
    matcher = EventMatcher()
    obs_list = matcher.load_normalized_observations()
    assert len(obs_list) > 0

    results = matcher.match_observations(obs_list)
    chennai_2015_matches = [r for r in results if r["population_name"] == "Chennai_2015"]
    assert len(chennai_2015_matches) == 753
    for m in chennai_2015_matches:
        assert m["match_status"] == "NOT_COMPUTABLE"

def test_event_matcher_unknown_records():
    matcher = EventMatcher()
    obs_list = matcher.load_normalized_observations()
    results = matcher.match_observations(obs_list)
    unknown_matches = [r for r in results if r["population_name"] == "UNKNOWN"]
    assert len(unknown_matches) == 192
    for m in unknown_matches:
        assert m["match_status"] == "DIAGNOSTIC_SPATIAL_ONLY"

def test_validation_gate_evaluator():
    vg = ValidationGate()
    gate_results = vg.evaluate_gates()
    assert gate_results["validation_status"] == "NOT_VALIDATED"
    gates = gate_results["gates"]
    assert gates["forcing_completeness_gate"]["passed"] is True
    assert gates["event_matched_depth_observations_gate"]["passed"] is False
    assert gates["calibration_gate"]["passed"] is True
    assert gates["calibration_gate"]["status"] == "COMPLETED — OCCURRENCE-BASED"
    assert gates["independent_validation_gate"]["passed"] is False

def test_occurrence_metrics_separation():
    vg = ValidationGate()
    gate_results = vg.evaluate_gates()
    occurrence = gate_results.get("occurrence_validation_diagnostic", {})
    assert occurrence["usage"] == "DIAGNOSTIC_OCCURRENCE_ONLY"
    assert occurrence["is_independent_validation"] is False
    assert occurrence["metrics"]["precision"] > 0.8

def test_validation_status_evaluator_preserves_not_validated():
    evaluator = ValidationStatusEvaluator()
    eval_res = evaluator.evaluate_status()
    assert eval_res["status"] == "IMPLEMENTED — NOT VALIDATED"
    assert eval_res["scientific_classification"] == "COMPLETE BUT NOT VALIDATED"
    assert "Zero sub-daily numerical flood depth observations" in eval_res["validation_blocker"]

def test_validation_service_payload_completeness():
    service = ValidationService()
    payload = service.get_historical_validation()
    assert payload["overall_validation_status"] == "NOT_VALIDATED"
    assert payload["forcing"]["available_timesteps"] == 241
    assert payload["forcing"]["missing_timesteps"] == 0
    assert payload["historical_replay_status"] == "COMPLETE"
    assert payload["historical_replay_model_version"] == "GRID_HYDROLOGY_V1"
