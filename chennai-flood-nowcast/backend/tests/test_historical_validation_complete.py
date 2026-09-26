import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from app.services.historical_validation_engine import (
    run_historical_replay,
)
from scripts.complete_nasa_acquisition import (
    generate_expected_timesteps,
)
from app.services.validation_service import ValidationService

backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent

def test_expected_timesteps_count_is_241():
    timesteps = generate_expected_timesteps()
    assert len(timesteps) == 241
    assert timesteps[0] == datetime(2015, 11, 30, 0, 0, tzinfo=timezone.utc)
    assert timesteps[-1] == datetime(2015, 12, 5, 0, 0, tzinfo=timezone.utc)

def test_completeness_audit_file():
    audit_file = project_root / "data" / "validation" / "results" / "completeness_audit.json"
    assert audit_file.exists()
    with open(audit_file, "r") as f:
        data = json.load(f)
    assert data["expected_timesteps"] == 241
    assert data["available_timesteps"] == 241
    assert data["missing_timesteps"] == 0
    assert data["status"] == "COMPLETE"

def test_raw_manifest_completeness():
    manifest_file = project_root / "data" / "forcing" / "historical" / "raw_manifest.json"
    assert manifest_file.exists()
    with open(manifest_file, "r") as f:
        items = json.load(f)
    assert len(items) == 241
    for item in items:
        assert item["hdf5_valid"] is True
        assert item["dataset"] == "GPM_3IMERGHH"
        assert item["version"] == "V07B"
        assert item["file_size_bytes"] > 100000
        assert len(item["sha256"]) == 64

def test_historical_replay_status_complete():
    raw_dir = project_root / "data" / "forcing" / "historical" / "raw"
    replay = run_historical_replay(raw_dir, model_version="GRID_HYDROLOGY_V1")
    assert replay["historical_replay_status"] == "COMPLETE"
    assert replay["event_replay_status"] == "COMPLETE"
    assert replay["forcing"]["available_timesteps"] == 241
    assert replay["forcing"]["missing_timesteps"] == 0
    assert len(replay["timeseries"]) == 241

def test_observation_attribution_sources():
    sources_file = project_root / "data" / "validation" / "observation_sources.json"
    assert sources_file.exists()
    with open(sources_file, "r") as f:
        data = json.load(f)
    datasets = {d["population_name"]: d for d in data["datasets"]}
    assert "Chennai_2015" in datasets
    assert "UNKNOWN" in datasets
    assert datasets["Chennai_2015"]["records_with_depth"] == 0
    assert datasets["UNKNOWN"]["event_confidence"] == "UNKNOWN"

def test_validation_service_provenance_and_status():
    service = ValidationService()
    hist = service.get_historical_validation()
    assert hist["status"] == "NOT_VALIDATED"
    assert hist["overall_validation_status"] == "NOT_VALIDATED"
    assert hist["historical_replay_model_version"] == "GRID_HYDROLOGY_V1"
    assert hist["model_status"] == "IMPLEMENTED — NOT VALIDATED"
    assert hist["forcing"]["available_timesteps"] == 241
    assert hist["forcing"]["missing_timesteps"] == 0

def test_drainage_hydraulic_coupling_unavailable():
    indep_file = project_root / "data" / "validation" / "results" / "independent_validation_metrics.json"
    assert indep_file.exists()
    with open(indep_file, "r") as f:
        metrics = json.load(f)
    assert metrics["hydraulic_coupling"] == "UNAVAILABLE"
    assert metrics["drainage_effect_on_flood_depth_cm"] == 0.0
    assert metrics["scientific_classification"] == "COMPLETE BUT NOT VALIDATED"
