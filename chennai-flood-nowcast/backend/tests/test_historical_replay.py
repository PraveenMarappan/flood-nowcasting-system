"""
Tests for the Historical Rainfall Replay + Validation Pipeline.

Covers:
1.  IMERG filename parsing
2.  Precipitation variable detection
3.  Nearest lat/lon indexing
4.  Timestamp extraction
5.  Chronological ordering
6.  Missing value handling
7.  Negative value handling
8.  Unit handling (mm/hr)
9.  Synthetic HDF5 extraction
10. Default timestep remains 1.0
11. Historical replay uses 0.5
12. Existing production callers remain compatible
13. MAE calculation
14. RMSE calculation
15. Occurrence validation with null threshold
16. Occurrence validation with explicit threshold
17. Empty observations
18. No network requests
19. No NASA credentials required

All tests use synthetic fixtures. No real NASA credentials or servers.
"""

import math
import tempfile
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# ─── Fixtures ──────────────────────────────────────────────────────

def _create_synthetic_hdf5(
    filepath,
    lat_target=13.0827,
    lon_target=80.2707,
    precip_value=5.09,
    var_name="precipitation",
    time_val=1132876800,
):
    """Create a minimal synthetic IMERG-like HDF5 file for testing."""
    import h5py

    # Create minimal grid: small lat/lon arrays centered around target
    lats = np.arange(12.95, 13.15, 0.1, dtype=np.float32)  # 2 values
    lons = np.arange(80.15, 80.35, 0.1, dtype=np.float32)  # 2 values

    # Find nearest indices
    lat_idx = int(np.abs(lats - lat_target).argmin())
    lon_idx = int(np.abs(lons - lon_target).argmin())

    # Create precip array: shape (1, n_lons, n_lats)
    precip = np.zeros((1, len(lons), len(lats)), dtype=np.float32)
    precip[0, lon_idx, lat_idx] = precip_value

    with h5py.File(filepath, "w") as f:
        grid = f.create_group("Grid")
        grid.create_dataset("lat", data=lats)
        grid.create_dataset("lon", data=lons)
        grid.create_dataset(var_name, data=precip)
        grid.create_dataset("time", data=np.array([time_val], dtype=np.int64))
        grid.create_dataset("time_bnds", data=np.array([[time_val, time_val + 1800]], dtype=np.int64))


# ─── 1. IMERG Filename Parsing ────────────────────────────────────

class TestImergFilenameParsing:
    def test_valid_filename(self):
        from app.services.historical_rainfall_service import parse_imerg_filename

        result = parse_imerg_filename(
            "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        )
        assert result is not None
        assert result["version"] == "V07B"
        assert result["start_time"].year == 2015
        assert result["start_time"].month == 11
        assert result["start_time"].day == 30
        assert result["start_time"].hour == 0
        assert result["start_time"].minute == 0
        assert result["end_time"].hour == 0
        assert result["end_time"].minute == 29
        assert result["minute_offset"] == 0

    def test_second_half_hour_filename(self):
        from app.services.historical_rainfall_service import parse_imerg_filename

        result = parse_imerg_filename(
            "3B-HHR.MS.MRG.3IMERG.20151130-S003000-E005959.0030.V07B.HDF5"
        )
        assert result is not None
        assert result["start_time"].minute == 30
        assert result["end_time"].minute == 59
        assert result["minute_offset"] == 30

    def test_invalid_filename_returns_none(self):
        from app.services.historical_rainfall_service import parse_imerg_filename

        assert parse_imerg_filename("random_file.txt") is None
        assert parse_imerg_filename("") is None
        assert parse_imerg_filename("3B-HHR.WRONG.FORMAT.HDF5") is None


# ─── 2. Precipitation Variable Detection ──────────────────────────

class TestPrecipVariableDetection:
    def test_preferred_variable(self, tmp_path):
        """Should use 'precipitation' when available."""
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp, precip_value=5.09, var_name="precipitation")

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["precipitation_variable"] == "precipitation"
        assert result["rainfall_status"] == "VALID"

    def test_fallback_variable(self, tmp_path):
        """Should fall back to 'precipitationCal' when 'precipitation' is missing."""
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp, precip_value=3.5, var_name="precipitationCal")

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["precipitation_variable"] == "precipitationCal"
        assert result["rainfall_status"] == "VALID"
        assert result["rainfall_mm_hr"] == 3.5


# ─── 3. Nearest Lat/Lon Indexing ──────────────────────────────────

class TestNearestIndex:
    def test_nearest_index_exact(self):
        from app.services.historical_rainfall_service import _find_nearest_index
        arr = np.array([12.95, 13.05, 13.15])
        assert _find_nearest_index(arr, 13.05) == 1

    def test_nearest_index_between(self):
        from app.services.historical_rainfall_service import _find_nearest_index
        arr = np.array([12.95, 13.05, 13.15])
        # 13.08 is closer to 13.05 than 13.15
        assert _find_nearest_index(arr, 13.08) == 1

    def test_nearest_index_edge(self):
        from app.services.historical_rainfall_service import _find_nearest_index
        arr = np.array([-89.95, -89.85, 89.85, 89.95])
        assert _find_nearest_index(arr, -89.95) == 0
        assert _find_nearest_index(arr, 89.95) == 3


# ─── 4. Timestamp Extraction ──────────────────────────────────────

class TestTimestampExtraction:
    def test_timestamp_from_filename(self, tmp_path):
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp)

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["timestamp_utc"] == "2015-11-30T00:00:00+00:00"

    def test_version_from_filename(self, tmp_path):
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp)

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["dataset_version"] == "V07B"
        assert result["dataset"] == "GPM_3IMERGHH"


# ─── 5. Chronological Ordering ────────────────────────────────────

class TestChronologicalOrdering:
    def test_files_sorted_chronologically(self, tmp_path):
        # Create files out of order
        names = [
            "3B-HHR.MS.MRG.3IMERG.20151130-S003000-E005959.0030.V07B.HDF5",
            "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5",
            "3B-HHR.MS.MRG.3IMERG.20151201-S000000-E002959.0000.V07B.HDF5",
        ]
        for name in names:
            _create_synthetic_hdf5(tmp_path / name, precip_value=1.0)

        from app.services.historical_rainfall_service import extract_timeseries
        records = extract_timeseries(tmp_path, 13.0827, 80.2707)
        assert len(records) == 3
        timestamps = [r["timestamp_utc"] for r in records]
        assert timestamps == sorted(timestamps)


# ─── 6. Missing Value Handling ─────────────────────────────────────

class TestMissingValueHandling:
    def test_nan_value_is_missing(self, tmp_path):
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp, precip_value=float("nan"))

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["rainfall_status"] == "MISSING"
        assert result["rainfall_mm_hr"] is None


# ─── 7. Negative Value Handling ────────────────────────────────────

class TestNegativeValueHandling:
    def test_negative_value_preserved(self, tmp_path):
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp, precip_value=-9999.9)

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["rainfall_status"] == "NEGATIVE"
        assert result["rainfall_mm_hr"] is None
        assert result["raw_value"] == pytest.approx(-9999.9, abs=0.1)


# ─── 8. Unit Handling ──────────────────────────────────────────────

class TestUnitHandling:
    def test_rainfall_in_mm_hr(self, tmp_path):
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp, precip_value=5.09)

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["units"] == "mm/hr"
        assert result["rainfall_mm_hr"] == pytest.approx(5.09, abs=0.01)


# ─── 9. Synthetic HDF5 Extraction ─────────────────────────────────

class TestSyntheticExtraction:
    def test_known_value_extraction(self, tmp_path):
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp, precip_value=12.34)

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["rainfall_mm_hr"] == pytest.approx(12.34, abs=0.01)
        assert result["rainfall_status"] == "VALID"
        assert result["latitude"] is not None
        assert result["longitude"] is not None

    def test_zero_rainfall_is_valid(self, tmp_path):
        fp = tmp_path / "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
        _create_synthetic_hdf5(fp, precip_value=0.0)

        from app.services.historical_rainfall_service import extract_rainfall
        result = extract_rainfall(fp, 13.0827, 80.2707)
        assert result["rainfall_status"] == "VALID"
        assert result["rainfall_mm_hr"] == 0.0


# ─── 10. Default Timestep Remains 1.0 ─────────────────────────────

class TestDefaultTimestep:
    def test_default_timestep_produces_original_result(self):
        """calculate_spatial_flood with no timestep_hours arg must use 1.0 default."""
        from app.services.flood_model_service import FloodModelService
        model = FloodModelService()

        # Call without timestep_hours (production behavior)
        result_default = model.calculate_spatial_flood(13.0827, 80.2707, 10.0, 0)
        # Call with explicit 1.0 (must be identical)
        result_explicit = model.calculate_spatial_flood(13.0827, 80.2707, 10.0, 0, timestep_hours=1.0)

        assert result_default["water_depth_cm"] == result_explicit["water_depth_cm"]
        assert result_default["water_depth_cm"] > 0

    def test_invalid_timestep_raises(self):
        from app.services.flood_model_service import FloodModelService
        model = FloodModelService()

        with pytest.raises(ValueError, match="timestep_hours must be > 0"):
            model.calculate_spatial_flood(13.0827, 80.2707, 10.0, 0, timestep_hours=0)

        with pytest.raises(ValueError, match="timestep_hours must be > 0"):
            model.calculate_spatial_flood(13.0827, 80.2707, 10.0, 0, timestep_hours=-1.0)


# ─── 11. Historical Replay Uses 0.5 ───────────────────────────────

class TestHalfHourTimestep:
    def test_half_hour_gives_half_runoff(self):
        """0.5-hour timestep should produce approximately half the depth of 1.0-hour.
        The model rounds to 2 decimal places, so exact halving may not hold at output level.
        Instead we verify the mathematical ratio within rounding tolerance."""
        from app.services.flood_model_service import FloodModelService
        model = FloodModelService()

        result_1h = model.calculate_spatial_flood(13.0827, 80.2707, 10.0, 0, timestep_hours=1.0)
        result_half = model.calculate_spatial_flood(13.0827, 80.2707, 10.0, 0, timestep_hours=0.5)

        # With forecast_offset_minutes=0 and rainfall > 0, recession_mult=1.0
        # So the additive term is 0, and water_depth = base_water_depth_cm
        # base_water_depth_cm = rainfall * C * timestep_hours * 0.1 * concentration_factor
        # Half timestep → half depth (before rounding)
        # Allow for round(x, 2) tolerance (up to 0.005)
        assert result_half["water_depth_cm"] == pytest.approx(
            result_1h["water_depth_cm"] / 2.0, abs=0.01
        )

    def test_half_hour_less_depth(self):
        """0.5-hour should produce less flood depth than 1.0-hour for same rainfall rate."""
        from app.services.flood_model_service import FloodModelService
        model = FloodModelService()

        result_1h = model.calculate_spatial_flood(13.0827, 80.2707, 50.0, 0, timestep_hours=1.0)
        result_half = model.calculate_spatial_flood(13.0827, 80.2707, 50.0, 0, timestep_hours=0.5)

        assert result_half["water_depth_cm"] < result_1h["water_depth_cm"]
        assert result_half["water_depth_cm"] > 0


# ─── 12. Production Callers Compatible ────────────────────────────

class TestProductionCompat:
    def test_route_service_call_signature(self):
        """route_service.py calls calculate_spatial_flood(lat, lng, rainfall, offset).
        This must continue working without timestep_hours."""
        from app.services.flood_model_service import FloodModelService
        model = FloodModelService()
        # Simulate exact call from route_service line 51
        result = model.calculate_spatial_flood(13.0, 80.0, 50.0, 0)
        assert "water_depth_cm" in result

    def test_positional_args_only(self):
        """Verify the function works with purely positional arguments."""
        from app.services.flood_model_service import FloodModelService
        model = FloodModelService()
        result = model.calculate_spatial_flood(13.0, 80.0, 25.0, 30)
        assert "water_depth_cm" in result


# ─── 13. MAE Calculation ──────────────────────────────────────────

class TestMaeCalculation:
    def test_known_mae(self):
        """MAE of [2, 5, 0] = 7/3 ≈ 2.3333"""
        from app.services.validation_service import ValidationService
        matches = [
            {"type": "DEPTH", "obs": 10.0, "pred": 12.0},  # error 2
            {"type": "DEPTH", "obs": 15.0, "pred": 10.0},  # error 5
            {"type": "DEPTH", "obs": 5.0, "pred": 5.0},    # error 0
        ]
        mae = ValidationService.calculate_mae(matches)
        assert mae == pytest.approx(7.0 / 3.0, rel=1e-5)

    def test_mae_empty_returns_none(self):
        from app.services.validation_service import ValidationService
        assert ValidationService.calculate_mae([]) is None
        assert ValidationService.calculate_mae([{"type": "CLASSIFICATION"}]) is None

    def test_engine_depth_validation_mae(self):
        """Test MAE via the validation engine with synthetic observations."""
        from app.services.historical_validation_engine import run_depth_validation

        # Create synthetic observations with known depths
        observations = [
            {
                "geometry": {"type": "Point", "coordinates": [80.27, 13.08]},
                "properties": {"observed_depth_cm": 10.0, "event": "UNKNOWN"},
            },
            {
                "geometry": {"type": "Point", "coordinates": [80.28, 13.09]},
                "properties": {"observed_depth_cm": 20.0, "event": "UNKNOWN"},
            },
        ]

        result = run_depth_validation(observations, peak_rainfall=5.0)
        # Should have computed metrics
        assert result["sample_count"] == 2
        assert result["mae_cm"] is not None
        assert result["validation_type"] == "SPATIAL_EVENT_LEVEL"


# ─── 14. RMSE Calculation ─────────────────────────────────────────

class TestRmseCalculation:
    def test_known_rmse(self):
        """RMSE of [2, 5, 0] = sqrt(29/3) ≈ 3.1091"""
        from app.services.validation_service import ValidationService
        matches = [
            {"type": "DEPTH", "obs": 10.0, "pred": 12.0},
            {"type": "DEPTH", "obs": 15.0, "pred": 10.0},
            {"type": "DEPTH", "obs": 5.0, "pred": 5.0},
        ]
        rmse = ValidationService.calculate_rmse(matches)
        expected = math.sqrt((4 + 25 + 0) / 3)
        assert rmse == pytest.approx(expected, rel=1e-5)

    def test_rmse_empty_returns_none(self):
        from app.services.validation_service import ValidationService
        assert ValidationService.calculate_rmse([]) is None


# ─── 15. Occurrence with Null Threshold ────────────────────────────

class TestOccurrenceNullThreshold:
    def test_null_threshold_not_computable(self):
        from app.services.historical_validation_engine import run_occurrence_validation

        observations = [
            {
                "geometry": {"type": "Point", "coordinates": [80.27, 13.08]},
                "properties": {"event": "Chennai_2015", "observed_status": "FLOODED"},
            },
        ]

        result = run_occurrence_validation(
            observations, peak_rainfall=5.0, threshold_cm=None
        )
        assert result["status"] == "NOT_COMPUTABLE"
        assert "THRESHOLD_REQUIRED" in result["reason"]
        assert result["precision"] is None
        assert result["recall"] is None
        assert result["f1"] is None
        assert result["threshold_depth_cm"] is None
        assert result["continuous_predictions_available"] is True


# ─── 16. Occurrence with Explicit Threshold ────────────────────────

class TestOccurrenceWithThreshold:
    def test_with_threshold_computes_metrics(self):
        from app.services.historical_validation_engine import run_occurrence_validation

        observations = [
            {
                "geometry": {"type": "Point", "coordinates": [80.27, 13.08]},
                "properties": {"event": "Chennai_2015", "observed_status": "FLOODED"},
            },
            {
                "geometry": {"type": "Point", "coordinates": [80.28, 13.09]},
                "properties": {"event": "Chennai_2015", "observed_status": "UNKNOWN"},
            },
        ]

        result = run_occurrence_validation(
            observations, peak_rainfall=50.0,
            threshold_cm=0.1,
            threshold_source="TEST_VALUE",
        )
        assert result["status"] == "READY_FOR_REVIEW"
        assert result["threshold_depth_cm"] == 0.1
        assert result["threshold_source"] == "TEST_VALUE"
        assert result["threshold_tuned_against_validation"] is False
        # Confusion matrix should exist
        assert "confusion_matrix" in result
        # Metrics may or may not be None depending on model output
        assert result["sample_count"] == 2

    def test_threshold_not_tuned(self):
        from app.services.historical_validation_engine import run_occurrence_validation

        result = run_occurrence_validation(
            observations=[{
                "geometry": {"type": "Point", "coordinates": [80.27, 13.08]},
                "properties": {"event": "Chennai_2015", "observed_status": "FLOODED"},
            }],
            peak_rainfall=10.0,
            threshold_cm=5.0,
            threshold_source="USER_SPECIFIED",
        )
        assert result["threshold_tuned_against_validation"] is False


# ─── 17. Empty Observations ───────────────────────────────────────

class TestEmptyObservations:
    def test_depth_validation_empty(self):
        from app.services.historical_validation_engine import run_depth_validation
        result = run_depth_validation(observations=[], peak_rainfall=5.0)
        assert result["status"] == "NOT_COMPUTABLE"
        assert result["sample_count"] == 0
        assert result["mae_cm"] is None
        assert result["rmse_cm"] is None

    def test_depth_validation_no_depth_field(self):
        from app.services.historical_validation_engine import run_depth_validation
        obs = [{
            "geometry": {"type": "Point", "coordinates": [80.27, 13.08]},
            "properties": {"event": "Chennai_2015"},  # no observed_depth_cm
        }]
        result = run_depth_validation(observations=obs, peak_rainfall=5.0)
        assert result["status"] == "NOT_COMPUTABLE"
        assert result["sample_count"] == 0

    def test_occurrence_validation_empty(self):
        from app.services.historical_validation_engine import run_occurrence_validation
        result = run_occurrence_validation(observations=[], peak_rainfall=5.0)
        assert result["status"] == "NOT_COMPUTABLE"
        assert result["sample_count"] == 0

    def test_depth_validation_no_rainfall(self):
        from app.services.historical_validation_engine import run_depth_validation
        result = run_depth_validation(
            observations=[{
                "geometry": {"type": "Point", "coordinates": [80.27, 13.08]},
                "properties": {"observed_depth_cm": 10.0},
            }],
            peak_rainfall=None,
        )
        assert result["status"] == "NOT_COMPUTABLE"
        assert result["reason"] == "No valid historical rainfall available for model forcing"


# ─── 18. No Network Requests ──────────────────────────────────────

class TestNoNetworkRequests:
    def test_historical_service_no_imports_requests(self):
        """historical_rainfall_service must not import requests or httpx."""
        import importlib
        mod = importlib.import_module("app.services.historical_rainfall_service")
        source = Path(mod.__file__).read_text()
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "urllib.request" not in source

    def test_validation_engine_no_network_imports(self):
        import importlib
        mod = importlib.import_module("app.services.historical_validation_engine")
        source = Path(mod.__file__).read_text()
        assert "import requests" not in source
        assert "import httpx" not in source


# ─── 19. No NASA Credentials ──────────────────────────────────────

class TestNoNasaCredentials:
    def test_no_credential_access(self):
        """Pipeline modules must not access EARTHDATA env vars."""
        import importlib
        for mod_name in [
            "app.services.historical_rainfall_service",
            "app.services.historical_validation_engine",
        ]:
            mod = importlib.import_module(mod_name)
            source = Path(mod.__file__).read_text()
            assert "EARTHDATA_USERNAME" not in source
            assert "EARTHDATA_PASSWORD" not in source
            assert "EARTHDATA_TOKEN" not in source


# ─── Additional: Metrics Assembly ──────────────────────────────────

class TestMetricsAssembly:
    def test_build_metrics_not_validated(self):
        from app.services.historical_validation_engine import build_validation_metrics

        replay = {
            "historical_replay_status": "PARTIAL",
            "event_replay_status": "INCOMPLETE",
            "forcing": {
                "files_available": 1,
                "timesteps_processed": 1,
            },
            "processed_window_peak_rainfall_mm_hr": 5.09,
        }
        depth = {
            "status": "READY_FOR_REVIEW",
            "validation_type": "SPATIAL_EVENT_LEVEL",
            "sample_count": 192,
            "mae_cm": 10.5,
            "rmse_cm": 15.2,
        }
        occurrence = {
            "status": "NOT_COMPUTABLE",
            "reason": "THRESHOLD_REQUIRED",
            "sample_count": 753,
            "threshold_depth_cm": None,
        }

        metrics = build_validation_metrics(replay, depth, occurrence)
        assert metrics["model_validation_status"] == "NOT_VALIDATED"
        assert metrics["historical_replay_status"] == "PARTIAL"
        assert metrics["event_replay_status"] == "INCOMPLETE"
        assert "limitations" in metrics
        assert len(metrics["limitations"]) > 0
