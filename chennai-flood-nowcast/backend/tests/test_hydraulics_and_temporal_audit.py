import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.hydraulics.hydraulic_capacity import HydraulicCapacityCalculator
from app.services.hydraulics.drainage_runoff import DrainageRunoffCalculator
from app.services.hydraulics.hydraulic_network import HydraulicNetworkManager
from app.services.hydraulics.drainage_overflow import DrainageOverflowEvaluator
from app.services.hydraulics.hydraulic_validation import HydraulicValidationChecker
from app.services.drainage_coupling_service import DrainageCouplingService
from app.services.validation.validation_gate import ValidationGate

client = TestClient(app)

def test_manning_box_culvert_capacity():
    """Verify Manning box culvert capacity formula Q = (1/n) * A * R^(2/3) * S^(1/2)."""
    res = HydraulicCapacityCalculator.calculate_box_culvert_capacity(
        width_m=0.60,
        height_m=0.75,
        manning_n=0.015,
        slope=0.001,
        is_measured=False,
        provenance="ASSUMED_DESIGN_STANDARD"
    )
    assert res["status"] == "CALCULATED"
    assert res["capacity_m3_s"] > 0
    assert res["area_m2"] == 0.45
    assert res["wetted_perimeter_m"] == 2.7
    assert res["provenance"] == "ASSUMED_DESIGN_STANDARD"
    assert res["measured"] is False

def test_manning_circular_pipe_capacity():
    """Verify Manning circular pipe capacity calculation."""
    res = HydraulicCapacityCalculator.calculate_circular_pipe_capacity(
        diameter_m=0.60,
        manning_n=0.015,
        slope=0.001,
        is_measured=False,
        provenance="ASSUMED_DESIGN_STANDARD"
    )
    assert res["status"] == "CALCULATED"
    assert res["capacity_m3_s"] > 0
    assert res["provenance"] == "ASSUMED_DESIGN_STANDARD"

def test_drainage_runoff_rational_method():
    """Verify Rational Method runoff inflow Q_in = (C * I * A) / 3600000."""
    res = DrainageRunoffCalculator.calculate_inflow_m3_s(
        rainfall_intensity_mm_hr=50.0,
        catchment_area_m2=10000.0,
        runoff_coefficient=0.85
    )
    assert res["status"] == "CALCULATED"
    # Q_in = (0.85 * 50 * 10000) / 3,600,000 = 425000 / 3600000 = 0.118056 m3/s
    assert abs(res["inflow_m3_s"] - 0.118056) < 0.001
    assert res["measured"] is False

def test_drainage_overflow_evaluator():
    """Verify surcharge ratio and scientific safety rules against depth reduction."""
    # Under capacity
    res_under = DrainageOverflowEvaluator.evaluate_overflow(inflow_q_m3_s=0.05, capacity_q_m3_s=0.10)
    assert res_under["surcharge_ratio"] == 0.5
    assert res_under["overflow_rate_m3_s"] == 0.0
    assert res_under["capacity_status"] == "WITHIN_ASSUMED_CAPACITY"
    assert res_under["drainage_effect_on_flood_depth"] == 0.0

    # Over capacity
    res_over = DrainageOverflowEvaluator.evaluate_overflow(inflow_q_m3_s=0.20, capacity_q_m3_s=0.10)
    assert res_over["surcharge_ratio"] == 2.0
    assert res_over["overflow_rate_m3_s"] == 0.10
    assert res_over["capacity_status"] == "ASSUMED_CAPACITY_EXCEEDED"
    assert res_over["drainage_effect_on_flood_depth"] == 0.0

def test_hydraulic_validation_checker():
    """Verify observational validation check returns NOT VALIDATED with 0 observations."""
    val = HydraulicValidationChecker.check_hydraulic_validation()
    assert val["status"] == "NOT_VALIDATED"
    assert val["hydraulic_observations_count"] == 0
    assert val["validation_gate_passed"] is False

def test_drainage_coupling_service_status():
    """Verify DrainageCouplingService status format."""
    service = DrainageCouplingService()
    status = service.get_status()
    assert status["status"] == "HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED"
    assert status["full_network_mode"] == "GEOMETRIC_ONLY"
    assert status["pilot_mode"] == "HYDRAULIC_MODEL"
    assert status["engineering_data"]["measured"] is False
    assert status["engineering_data"]["assumed"] is True
    assert status["parameter_provenance"] == "ASSUMED_DESIGN_STANDARD"
    assert status["hydraulic_validation"] == "NOT_VALIDATED"

def test_temporal_gauge_api():
    """Test /api/validation/temporal-gauge endpoint returns dynamic CAG temporal payload."""
    response = client.get("/api/validation/temporal-gauge")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PARTIALLY_VALIDATED"
    assert data["temporal_hydrological_observations"] == "AVAILABLE"
    assert data["urban_flood_depth_temporal_validation"] == "NOT_VALIDATED"
    assert data["observation_count"] == 10
    assert data["source_agency"] == "CAG / WRD"

def test_drainage_status_api():
    """Test /api/drainage/status endpoint returns required dynamic payload."""
    response = client.get("/api/drainage/status")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "PILOT_HYDRAULIC_COUPLING"
    assert data["full_network_mode"] == "GEOMETRIC_ONLY"
    assert data["engineering_data"]["measured"] is False
    assert data["parameter_provenance"] == "ASSUMED_DESIGN_STANDARD"

def test_validation_gate_core_12_gates():
    """Verify ValidationGate evaluates 12 core component gates with 10 passing."""
    vg = ValidationGate()
    summary = vg.evaluate_gates()
    assert summary["total_gates_count"] == 12
    assert summary["passed_gates_count"] == 10
    assert summary["gates"]["temporal_hydrological_observation_gate"]["status"] == "AVAILABLE"
    assert summary["gates"]["temporal_gauge_gate"]["status"] == "NOT VALIDATED"
    assert summary["gates"]["drainage_hydraulic_model_gate"]["status"] == "HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED"

