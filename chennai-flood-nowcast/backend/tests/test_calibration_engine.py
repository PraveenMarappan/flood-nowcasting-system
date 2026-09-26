import json
import pytest
from pathlib import Path
from app.services.validation.calibration_engine import CalibrationEngine
from app.services.validation.validation_gate import ValidationGate

backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent

def test_calibration_uses_only_eligible_chennai_2015_records():
    engine = CalibrationEngine()
    obs = engine.load_chennai_2015_observations()
    assert len(obs) == 753
    for o in obs:
        assert o["event"] == "Chennai_2015"

def test_unknown_observations_excluded_from_calibration():
    engine = CalibrationEngine()
    res = engine.run_calibration()
    assert res["dataset"] == "Chennai_2015"
    assert res["records_available"] == 753
    assert res["numerical_depth_records"] == 0

def test_no_numerical_depth_calibration_claimed():
    engine = CalibrationEngine()
    res = engine.run_calibration()
    assert res["calibration_target"] == "EVENT_OCCURRENCE"
    assert res["calibration_mode"] == "OCCURRENCE_BASED"
    assert "numerical flood-depth measurements" in res["notes"]

def test_baseline_and_calibrated_parameters_recorded():
    engine = CalibrationEngine()
    res = engine.run_calibration()
    assert "baseline_parameters" in res
    assert "selected_parameters" in res
    assert res["baseline_parameters"]["impervious_surface_fraction"] == 0.85
    assert res["selected_parameters"]["impervious_surface_fraction"] == 0.88

def test_calibration_reproducibility():
    engine1 = CalibrationEngine()
    res1 = engine1.run_calibration()
    engine2 = CalibrationEngine()
    res2 = engine2.run_calibration()
    assert res1["selected_parameters"] == res2["selected_parameters"]
    assert res1["calibrated_metrics"] == res2["calibrated_metrics"]

def test_calibration_completed_without_changing_overall_validation():
    vg = ValidationGate()
    gate_res = vg.evaluate_gates()
    assert gate_res["gates"]["calibration_gate"]["passed"] is True
    assert gate_res["gates"]["calibration_gate"]["status"] == "COMPLETED — OCCURRENCE-BASED"
    assert gate_res["validation_status"] == "NOT_VALIDATED"
    assert gate_res["scientific_classification"] == "COMPLETE BUT NOT VALIDATED"

def test_no_data_leakage_from_calibration_to_independent_validation():
    vg = ValidationGate()
    gate_res = vg.evaluate_gates()
    assert gate_res["gates"]["independent_validation_gate"]["passed"] is False
    assert gate_res["gates"]["independent_validation_gate"]["status"] == "NOT_AVAILABLE"
