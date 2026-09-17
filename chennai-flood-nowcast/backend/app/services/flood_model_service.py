from datetime import datetime
from app.services.runoff_service import RunoffEstimationService
from app.services.drainage_coupling_service import DrainageCouplingService
from app.services.terrain_service import TerrainService
from app.services.catchment_service import CatchmentService

class FloodModelService:
    def __init__(self):
        self.runoff_service = RunoffEstimationService()
        self.drainage_service = DrainageCouplingService()
        self.terrain_service = TerrainService()
        self.catchment_service = CatchmentService()
        self.model_version = "v3-spatial-heuristic"
        self.calibration_status = "NOT_CALIBRATED"

    def calculate_spatial_flood(self, lat: float, lng: float, rainfall: float, forecast_offset_minutes: int):
        # 1. 0-Rainfall Behavior: Explicitly bail on flat zero without storage abstraction
        if rainfall <= 0 and forecast_offset_minutes == 0:
            return {
                "water_depth_cm": 0.0,
                "forecast_type": "CURRENT",
                "estimator": "SPATIAL HEURISTIC FLOOD-DEPTH ESTIMATE"
            }
            
        # 2. Extract Terrain Concentration Factor
        terrain = self.terrain_service.get_derivatives(lat, lng)
        concentration_factor = terrain.get("acc_prioritization_factor", 1.0)
        
        # 3. Catchment Logic
        catchment = self.catchment_service.get_catchment_properties(lat, lng)
        C = catchment["impervious_fraction"]
        
        # 4. Strict Dimensional Runoff Eq
        runoff_rate_mm_hr = rainfall * C
        timestep_hours = 1.0 # Base temporal resolution context
        runoff_depth_mm = runoff_rate_mm_hr * timestep_hours
        runoff_depth_cm = runoff_depth_mm * 0.1
        
        # 5. Spatial Routing (Heuristic limitation explicitly labeled)
        base_water_depth_cm = runoff_depth_cm * concentration_factor
        
        # 6. Heuristic Projection (Forecasts logic mapping asymptotic decay)
        recession_mult = 1.0
        forecast_type = "CURRENT"
        if forecast_offset_minutes > 0:
            forecast_type = "BASELINE HEURISTIC PROJECTION" 
            if forecast_offset_minutes >= 180: recession_mult = 0.05
            elif forecast_offset_minutes >= 150: recession_mult = 0.1
            elif forecast_offset_minutes >= 120: recession_mult = 0.2
            elif forecast_offset_minutes >= 90: recession_mult = 0.5
            elif forecast_offset_minutes >= 60: recession_mult = 0.7
            elif forecast_offset_minutes >= 30: recession_mult = 0.9
            
        if rainfall > 0:
            water_depth = base_water_depth_cm + (rainfall * (1.0 - recession_mult) * 0.1)
        else:
            water_depth = base_water_depth_cm * recession_mult
            
        return {
            "water_depth_cm": round(water_depth, 2),
            "forecast_type": forecast_type,
            "estimator": "SPATIAL HEURISTIC FLOOD-DEPTH ESTIMATE"
        }

    # Maintain existing backwards compatibility for non-road endpoints precisely
    def calculate_current_flood(self, actual_rainfall: float, elevation_val: float, has_real_terrain: bool, latitude: float, longitude: float):
        # Maps legacy requirements explicitly over upgraded spatial classes
        catchment = self.catchment_service.get_catchment_properties(latitude, longitude)
        runoff_rate_mm_hr = actual_rainfall * catchment["impervious_fraction"]
        
        accumulation_interval_hours = 1.0 
        runoff_depth_cm = (runoff_rate_mm_hr * accumulation_interval_hours) * 0.1
        
        terrain_factor = 1.0 
        if has_real_terrain and elevation_val is not None:
            if elevation_val < 5: terrain_factor = 1.8
            elif elevation_val < 15: terrain_factor = 1.2
            else: terrain_factor = 0.5 
            
        water_depth = runoff_depth_cm * terrain_factor
        
        risk_level = "NORMAL"
        if water_depth > 30.0:
            risk_level = "HIGH"
        elif water_depth > 10.0:
            risk_level = "MODERATE"
        elif water_depth > 0.1:
            risk_level = "LOW"
            
        # 7. DRAINAGE AUDIT: Currently not verified stormwater engineering data.
        drainage_evaluation = self.drainage_service.evaluate_drainage_influence(latitude, longitude, water_depth)
        drainage_evaluation["drainage_used"] = False
        drainage_evaluation["hydraulic_coupling"] = "UNAVAILABLE"
        drainage_evaluation["engineering_parameters"] = "UNAVAILABLE"

        return {
            "status": "MODELLED",
            "source": "Spatial Urban Flood Model",
            "model_version": self.model_version,
            "calibration_status": self.calibration_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "rainfall_rate_mm_hr": actual_rainfall,
            "runoff_coefficient": catchment["impervious_fraction"],
            "runoff_rate_mm_hr": round(runoff_rate_mm_hr, 2),
            "accumulation_interval_hours": accumulation_interval_hours,
            "runoff_depth_cm": round(runoff_depth_cm, 2),
            "terrain_elevation_m": elevation_val if has_real_terrain else None,
            "terrain_factor": terrain_factor,
            "flow_direction": "MODELLED",
            "flow_accumulation": "MODELLED",
            "water_depth_cm": round(water_depth, 2),
            "risk_level": risk_level,
            "drainage_used": False,
            "drainage": drainage_evaluation
        }
