import pytest
import csv
from pathlib import Path
from datetime import datetime, timezone
from app.services.urban_flood_temporal_validation import UrbanFloodTemporalValidationEngine, run_urban_flood_temporal_validation
from app.services.validation.validation_gate import ValidationGate
from app.services.validation_service import ValidationService

def test_utc_timestamp_parsing():
    """Verify ISO 8601 parsing converts strings to UTC datetime objects."""
    ts_z = "2015-12-01T12:30:00Z"
    dt_z = UrbanFloodTemporalValidationEngine.parse_utc_timestamp(ts_z)
    assert dt_z is not None
    assert dt_z.tzinfo == timezone.utc
    assert dt_z.year == 2015 and dt_z.month == 12 and dt_z.day == 1 and dt_z.hour == 12 and dt_z.minute == 30

    ts_iso = "2015-12-01T12:30:00+00:00"
    dt_iso = UrbanFloodTemporalValidationEngine.parse_utc_timestamp(ts_iso)
    assert dt_iso is not None
    assert dt_iso == dt_z

    # Invalid timestamp handling
    assert UrbanFloodTemporalValidationEngine.parse_utc_timestamp("invalid-date") is None

def test_haversine_distance():
    """Verify geodesic distance calculation between lat/lon points."""
    # Distance between Chennai Central and Egmore (~1.5 km)
    dist = UrbanFloodTemporalValidationEngine.haversine_distance_m(13.0827, 80.2707, 13.0732, 80.2609)
    assert 1000 < dist < 2000

    # Same point distance should be 0
    zero_dist = UrbanFloodTemporalValidationEngine.haversine_distance_m(13.0827, 80.2707, 13.0827, 80.2707)
    assert zero_dist == 0.0

def test_empty_dataset_behavior(tmp_path):
    """Verify behavior when no urban temporal observations file exists."""
    engine = UrbanFloodTemporalValidationEngine(base_dir=tmp_path)
    res = engine.run_validation()

    assert res["status"] == "NOT_VALIDATED"
    assert "Sub-Daily Urban Flood-Depth Time-Series Unavailable" in res["scientific_status"]
    assert res["observation_count"] == 0
    assert res["matched_count"] == 0
    assert res["holdout_count"] == 0
    assert res["metrics"] == {}
    assert res["quality_control"]["missing_timestamps"] == 0

def test_continuous_metrics_calculation():
    """Verify continuous metrics (MAE, RMSE, Bias, R2, Pearson, Spearman, NSE)."""
    dummy_records = [
        {"observed_depth_cm": 10.0, "predicted_depth_cm": 12.0},
        {"observed_depth_cm": 20.0, "predicted_depth_cm": 18.0},
        {"observed_depth_cm": 30.0, "predicted_depth_cm": 28.0},
        {"observed_depth_cm": 40.0, "predicted_depth_cm": 42.0},
        {"observed_depth_cm": 50.0, "predicted_depth_cm": 50.0},
    ]

    metrics = UrbanFloodTemporalValidationEngine.calculate_continuous_metrics(dummy_records)
    assert metrics["sample_count"] == 5
    assert metrics["mae_cm"] == 1.6
    assert metrics["bias_cm"] == 0.0
    assert metrics["pearson_r"] > 0.95
    assert metrics["r2"] > 0.90
    assert metrics["spearman_rho"] > 0.90

def test_threshold_metrics_calculation():
    """Verify threshold classification metrics (Precision, Recall/POD, F1, CSI, FAR)."""
    dummy_records = [
        {"observed_depth_cm": 15.0, "predicted_depth_cm": 20.0},  # TP (thresh 10)
        {"observed_depth_cm": 25.0, "predicted_depth_cm": 30.0},  # TP
        {"observed_depth_cm": 5.0,  "predicted_depth_cm": 2.0},   # TN
        {"observed_depth_cm": 2.0,  "predicted_depth_cm": 12.0},  # FP
        {"observed_depth_cm": 18.0, "predicted_depth_cm": 4.0},   # FN
    ]

    thresh = UrbanFloodTemporalValidationEngine.calculate_threshold_metrics(dummy_records, threshold_cm=10.0)
    assert thresh["tp"] == 2
    assert thresh["tn"] == 1
    assert thresh["fp"] == 1
    assert thresh["fn"] == 1
    assert thresh["precision"] == 0.6667
    assert thresh["recall_pod"] == 0.6667
    assert thresh["f1_score"] == 0.6667

def test_peak_metrics_calculation():
    """Verify peak depth error and peak timing error calculations."""
    dummy_records = [
        {"timestamp": "2015-12-01T10:00:00Z", "datetime": datetime(2015, 12, 1, 10, 0, tzinfo=timezone.utc), "observed_depth_cm": 10.0, "predicted_depth_cm": 8.0},
        {"timestamp": "2015-12-01T12:00:00Z", "datetime": datetime(2015, 12, 1, 12, 0, tzinfo=timezone.utc), "observed_depth_cm": 50.0, "predicted_depth_cm": 30.0},
        {"timestamp": "2015-12-01T14:00:00Z", "datetime": datetime(2015, 12, 1, 14, 0, tzinfo=timezone.utc), "observed_depth_cm": 20.0, "predicted_depth_cm": 60.0},
    ]

    peaks = UrbanFloodTemporalValidationEngine.calculate_peak_metrics(dummy_records)
    assert peaks["peak_observed_cm"] == 50.0
    assert peaks["peak_predicted_cm"] == 60.0
    assert peaks["peak_depth_error_cm"] == 10.0
    assert peaks["observed_peak_timestamp"] == "2015-12-01T12:00:00Z"
    assert peaks["predicted_peak_timestamp"] == "2015-12-01T14:00:00Z"
    assert peaks["peak_timing_error_hours"] == 2.0

def test_synthetic_chronological_holdout_split(tmp_path):
    """Verify 70/30 chronological split and validation gate logic when observations exist."""
    data_dir = tmp_path / "data" / "validation" / "temporal" / "urban_flood_depth"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_file = data_dir / "chennai_urban_flood_depth_temporal.csv"

    # Create 30 synthetic test records
    rows = []
    base_dt = datetime(2015, 12, 1, 0, 0, tzinfo=timezone.utc)
    for i in range(30):
        dt_str = (base_dt.isoformat().replace("+00:00", "Z"))
        obs = 10.0 + i * 2.0
        pred = obs + (1.0 if i % 2 == 0 else -1.0)
        rows.append({
            "timestamp": dt_str,
            "station_id": "ST01",
            "source_name": "Test Gauge",
            "latitude": 13.08,
            "longitude": 80.27,
            "observed_depth_cm": obs,
            "predicted_depth_cm": pred,
            "quality_flag": "PASSED"
        })
        base_dt = datetime.fromtimestamp(base_dt.timestamp() + 3600, tz=timezone.utc)

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    engine = UrbanFloodTemporalValidationEngine(base_dir=tmp_path)
    res = engine.run_validation()

    assert res["observation_count"] == 30
    assert res["calibration_count"] == 21  # 70% of 30
    assert res["holdout_count"] == 9      # 30% of 30
    assert res["status"] in ["VALIDATED", "PARTIALLY_VALIDATED"]
    assert res["metrics"]["mae_cm"] is not None
    assert res["metrics"]["mae_cm"] < 5.0

def test_validation_gate_and_service_integration():
    """Verify that ValidationGate and ValidationService correctly separate reservoir and urban gates."""
    gate_eval = ValidationGate()
    gates = gate_eval.evaluate_gates()["gates"]

    assert "temporal_reservoir_gauge_gate" in gates
    assert "urban_flood_depth_temporal_gate" in gates
    assert gates["temporal_reservoir_gauge_gate"]["status"] == "VALIDATED — TEMPORAL HOLDOUT"
    assert "NOT VALIDATED" in gates["urban_flood_depth_temporal_gate"]["status"]

    val_service = ValidationService()
    temp_val = val_service.get_temporal_gauge_validation()

    assert "temporal_reservoir_gauge_gate" in temp_val
    assert "urban_flood_depth_temporal_gate" in temp_val
    assert "VALIDATED" in temp_val["temporal_reservoir_gauge_gate"]["status"]
    assert temp_val["urban_flood_depth_temporal_gate"]["short_status"] == "NOT_VALIDATED"
