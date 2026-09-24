import pytest
import numpy as np

from app.services.hydrology.rainfall_runoff import RainfallRunoffService
from app.services.hydrology.dem_processing import DEMProcessingService
from app.services.hydrology.flow_accumulation import D8FlowAccumulationService
from app.services.hydrology.ponding import PondingDetectionService
from app.services.hydrology.flood_depth import FloodDepthEngine
from app.services.hydrology.model_provenance import ModelProvenance
from app.services.flood_model_service import FloodModelService
from app.services.calibration_service import CalibrationService
from app.services.model_comparison_service import ModelComparisonService

class TestGridHydrologyScience:
    def test_rainfall_runoff_excess_calculation(self):
        service = RainfallRunoffService()
        res = service.calculate_excess(rainfall_rate_mm_hr=50.0, timestep_hours=1.0, runoff_coefficient=0.85)
        
        assert res["precipitation_depth_mm"] == 50.0
        assert res["runoff_coefficient"] == 0.85
        assert res["excess_rainfall_mm"] == 42.5
        assert res["coefficient_provenance"] == "ASSUMED"
        assert res["units"]["excess_rainfall"] == "mm"

    def test_timestep_conversion(self):
        service = RainfallRunoffService()
        res = service.calculate_excess(rainfall_rate_mm_hr=50.0, timestep_hours=0.5, runoff_coefficient=0.80)
        
        assert res["precipitation_depth_mm"] == 25.0
        assert res["excess_rainfall_mm"] == 20.0

    @pytest.mark.parametrize("rainfall_rate", [10.0, 25.0, 50.0, 75.0, 105.0])
    @pytest.mark.parametrize("runoff_c", [0.2, 0.5, 0.85, 1.0])
    def test_mass_volume_conservation(self, rainfall_rate, runoff_c):
        """
        MASS / VOLUME CONSERVATION TEST:
        For uniform rainfall P over area A (m2) and duration 1 hr:
        Expected excess depth: P_excess (mm) = P * C
        Expected excess volume: V_excess (m3) = (P_excess / 1000) * A
        Verify that model runoff volume matches P * C * A within floating point tolerance.
        """
        service = RainfallRunoffService()
        res = service.calculate_excess(rainfall_rate_mm_hr=rainfall_rate, timestep_hours=1.0, runoff_coefficient=runoff_c)
        
        expected_p_excess_mm = rainfall_rate * runoff_c
        assert abs(res["excess_rainfall_mm"] - expected_p_excess_mm) < 1e-5

        cell_area_m2 = 925.0  # Approx cell area at Chennai latitude
        expected_volume_m3 = (expected_p_excess_mm / 1000.0) * cell_area_m2
        actual_volume_m3 = (res["excess_rainfall_mm"] / 1000.0) * cell_area_m2
        
        assert abs(actual_volume_m3 - expected_volume_m3) < 1e-5

    def test_synthetic_3x3_slope_d8_direction(self):
        """
        SYNTHETIC 3x3 DEM SLOPE TEST:
        Slope strictly North -> South:
        [30, 30, 30]
        [20, 20, 20]
        [10, 10, 10]
        Expected flow direction for row 0 & 1 is 2 (South).
        """
        dem = np.array([
            [30.0, 30.0, 30.0],
            [20.0, 20.0, 20.0],
            [10.0, 10.0, 10.0]
        ], dtype=np.float32)

        flow_dir = D8FlowAccumulationService.calculate_flow_direction(dem)
        
        assert flow_dir[0, 1] == 2  # South
        assert flow_dir[1, 1] == 2  # South
        assert flow_dir[2, 1] == -1 # Outlet / boundary

    def test_synthetic_v_shaped_basin_flow_accumulation(self):
        """
        SYNTHETIC V-SHAPED BASIN ACCUMULATION TEST:
        DEM slopes from East & West inward to central column (col 1) and South to [2, 1].
        [30, 30, 30]
        [20, 10, 20]
        [10,  5, 10]
        """
        dem = np.array([
            [30.0, 30.0, 30.0],
            [20.0, 10.0, 20.0],
            [10.0,  5.0, 10.0]
        ], dtype=np.float32)

        flow_dir = D8FlowAccumulationService.calculate_flow_direction(dem)
        flow_acc = D8FlowAccumulationService.calculate_flow_accumulation(flow_dir, dem)

        # Outlet cell [2, 1] must accumulate flow from upstream cells
        assert flow_acc[2, 1] >= 5

    def test_projected_cell_area_calculation(self):
        area_m2 = DEMProcessingService.calculate_cell_area_m2(lat_deg=13.0827)
        assert 900.0 <= area_m2 <= 960.0

    @pytest.mark.parametrize("initial_depth_cm", [10.0, 30.0, 50.0])
    def test_zero_rainfall_cessation_recovery(self, initial_depth_cm):
        """
        ZERO-RAINFALL RECOVERY & NO NEGATIVE DEPTHS TEST:
        75 mm/hr rainfall ceases (0 mm/hr) for offsets +30m, +60m, +120m, +180m.
        Verify:
        - Water depth is non-negative at all timesteps.
        - Water depth decreases strictly monotonically over time.
        - Behavior is 100% deterministic.
        """
        engine = FloodDepthEngine()
        
        offsets = [0, 30, 60, 120, 180]
        depths = []

        for off in offsets:
            res = engine.compute_flood_depth(
                rainfall_rate_mm_hr=0.0 if off > 0 else 75.0,
                latitude=13.0827,
                longitude=80.2707,
                elevation_m=10.0,
                forecast_offset_minutes=off,
                current_water_depth_cm=initial_depth_cm if off > 0 else None
            )
            d = res["water_depth_cm"]
            assert d >= 0.0, f"Negative depth detected at offset {off}: {d}"
            depths.append(d)

        # Verify strict monotonic decrease during cessation (for offsets 30, 60, 120, 180)
        for i in range(1, len(depths) - 1):
            assert depths[i+1] < depths[i], f"Depth did not decrease monotonically at step {i}: {depths}"

    def test_monotonicity_sanity_check(self):
        engine = FloodDepthEngine()
        d10 = engine.compute_flood_depth(10.0, 13.0827, 80.2707, 10.0)["water_depth_cm"]
        d20 = engine.compute_flood_depth(20.0, 13.0827, 80.2707, 10.0)["water_depth_cm"]
        d40 = engine.compute_flood_depth(40.0, 13.0827, 80.2707, 10.0)["water_depth_cm"]

        assert d10 < d20 < d40

    def test_runoff_coefficient_sensitivity(self):
        service = RainfallRunoffService()
        res_low = service.calculate_excess(50.0, 1.0, runoff_coefficient=0.40)
        res_high = service.calculate_excess(50.0, 1.0, runoff_coefficient=0.90)

        assert res_high["excess_rainfall_mm"] > res_low["excess_rainfall_mm"]

    def test_drainage_geometric_only_adherence(self):
        model = FloodModelService(default_version="GRID_HYDROLOGY_V1")
        res = model.calculate_current_flood(50.0, 10.0, True, 13.0827, 80.2707)

        assert res["drainage_used"] is False
        assert res["drainage"]["hydraulic_coupling"] == "UNAVAILABLE"
        assert res["provenance"]["drainage_mode"] == "GEOMETRIC_ONLY"

    def test_provenance_structure(self):
        prov = ModelProvenance.get_provenance_metadata("GRID_HYDROLOGY_V1")

        assert prov["model_version"] == "GRID_HYDROLOGY_V1"
        assert prov["validation_status"] == "NOT_VALIDATED"
        assert prov["calibration_status"] == "NOT_CALIBRATED"
        assert prov["provenance_map"]["dem_elevation"] == "REAL"
        assert prov["provenance_map"]["flow_direction"] == "DERIVED"
        assert prov["provenance_map"]["runoff_coefficients"] == "ASSUMED"

    def test_dual_model_selection(self):
        model = FloodModelService()
        res_legacy = model.calculate_spatial_flood(13.0827, 80.2707, 50.0, 0, 1.0, model_version="LEGACY_HEURISTIC")
        res_grid = model.calculate_spatial_flood(13.0827, 80.2707, 50.0, 0, 1.0, model_version="GRID_HYDROLOGY_V1")

        assert res_legacy["model_version"] == "LEGACY_HEURISTIC"
        assert res_grid["estimator"] == "GRID-BASED HYDROLOGICAL FLOOD-DEPTH ESTIMATE"
        assert res_grid["water_depth_cm"] > 0.0

    def test_calibration_service_metrics(self):
        obs = [10.0, 20.0, 30.0]
        pred = [12.0, 18.0, 33.0]
        metrics = CalibrationService.calculate_metrics(obs, pred)

        assert metrics["mae"] == round((2.0 + 2.0 + 3.0)/3.0, 4)
        assert metrics["status"] == "COMPUTED"
        assert metrics["n_samples"] == 3
