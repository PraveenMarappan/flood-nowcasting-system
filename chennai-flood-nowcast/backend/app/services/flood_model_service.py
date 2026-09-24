from datetime import datetime
from typing import Dict, Any, Optional

from app.services.runoff_service import RunoffEstimationService
from app.services.drainage_coupling_service import DrainageCouplingService
from app.services.terrain_service import TerrainService
from app.services.catchment_service import CatchmentService
from app.services.hydrology.flood_depth import FloodDepthEngine
from app.services.hydrology.model_provenance import ModelProvenance

class FloodModelService:
    def __init__(self, default_version: str = "GRID_HYDROLOGY_V1"):
        self.runoff_service = RunoffEstimationService()
        self.drainage_service = DrainageCouplingService()
        self.terrain_service = TerrainService()
        self.catchment_service = CatchmentService()
        self.grid_engine = FloodDepthEngine()
        
        self.model_version = default_version
        self.calibration_status = "NOT_CALIBRATED"
        self.validation_status = "NOT_VALIDATED"

    def calculate_legacy_heuristic(
        self,
        lat: float,
        lng: float,
        rainfall: float,
        forecast_offset_minutes: int,
        timestep_hours: float = 1.0
    ) -> Dict[str, Any]:
        """
        Original Legacy Heuristic Model (LEGACY_HEURISTIC).
        Maintained for exact backward compatibility and model comparison.
        """
        if timestep_hours <= 0:
            raise ValueError(f"timestep_hours must be > 0, got {timestep_hours}")
            
        if rainfall <= 0 and forecast_offset_minutes == 0:
            return {
                "water_depth_cm": 0.0,
                "forecast_type": "CURRENT",
                "estimator": "SPATIAL HEURISTIC FLOOD-DEPTH ESTIMATE",
                "model_version": "LEGACY_HEURISTIC"
            }
            
        terrain = self.terrain_service.get_derivatives(lat, lng)
        concentration_factor = terrain.get("acc_prioritization_factor", 1.0)
        
        catchment = self.catchment_service.get_catchment_properties(lat, lng)
        C = catchment["impervious_fraction"]
        
        runoff_rate_mm_hr = rainfall * C
        runoff_depth_mm = runoff_rate_mm_hr * timestep_hours
        runoff_depth_cm = runoff_depth_mm * 0.1
        
        base_water_depth_cm = runoff_depth_cm * concentration_factor
        
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
            "estimator": "SPATIAL HEURISTIC FLOOD-DEPTH ESTIMATE",
            "model_version": "LEGACY_HEURISTIC"
        }

    def calculate_spatial_flood(
        self,
        lat: float,
        lng: float,
        rainfall: float,
        forecast_offset_minutes: int,
        timestep_hours: float = 1.0,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main model router supporting both LEGACY_HEURISTIC and GRID_HYDROLOGY_V1.
        """
        active_version = model_version or self.model_version
        
        if active_version == "LEGACY_HEURISTIC":
            return self.calculate_legacy_heuristic(lat, lng, rainfall, forecast_offset_minutes, timestep_hours)

        # GRID_HYDROLOGY_V1 execution
        terrain = self.terrain_service.get_derivatives(lat, lng)
        elevation_m = terrain.get("elevation_m")
        flow_acc_cells = terrain.get("flow_accumulation_cells", 0)
        
        catchment = self.catchment_service.get_catchment_properties(lat, lng)
        runoff_c = catchment.get("impervious_fraction", 0.85)

        return self.grid_engine.compute_flood_depth(
            rainfall_rate_mm_hr=rainfall,
            latitude=lat,
            longitude=lng,
            elevation_m=elevation_m,
            flow_acc_cells=flow_acc_cells,
            slope=0.005,
            forecast_offset_minutes=forecast_offset_minutes,
            timestep_hours=timestep_hours,
            runoff_coefficient=runoff_c
        )

    def calculate_current_flood(
        self,
        actual_rainfall: float,
        elevation_val: Optional[float],
        has_real_terrain: bool,
        latitude: float,
        longitude: float,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Backwards-compatible API endpoint method returning full spatial flood response.
        Exposes full model provenance and drainage diagnostics.
        """
        active_version = model_version or self.model_version

        if active_version == "LEGACY_HEURISTIC":
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
            if water_depth > 30.0: risk_level = "HIGH"
            elif water_depth > 10.0: risk_level = "MODERATE"
            elif water_depth > 0.1: risk_level = "LOW"

            drainage_evaluation = self.drainage_service.evaluate_drainage_influence(latitude, longitude, water_depth)
            drainage_evaluation["drainage_used"] = False
            drainage_evaluation["hydraulic_coupling"] = "UNAVAILABLE"

            return {
                "status": "MODELLED",
                "source": "Spatial Urban Flood Model",
                "model_version": "LEGACY_HEURISTIC",
                "calibration_status": self.calibration_status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "location": {"latitude": latitude, "longitude": longitude},
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

        # GRID_HYDROLOGY_V1 execution
        res = self.calculate_spatial_flood(latitude, longitude, actual_rainfall, 0, 1.0, model_version="GRID_HYDROLOGY_V1")
        water_depth = res["water_depth_cm"]
        risk_level = res["risk_level"]

        drainage_eval = self.drainage_service.evaluate_drainage_influence(latitude, longitude, water_depth)
        drainage_eval["drainage_used"] = False
        drainage_eval["hydraulic_coupling"] = "UNAVAILABLE"
        drainage_eval["engineering_parameters"] = "UNAVAILABLE"

        prov = ModelProvenance.get_provenance_metadata("GRID_HYDROLOGY_V1")

        return {
            "status": "MODELLED",
            "source": "Grid-Based Hydrological Flood Model",
            "model_version": "GRID_HYDROLOGY_V1",
            "calibration_status": self.calibration_status,
            "validation_status": self.validation_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "location": {"latitude": latitude, "longitude": longitude},
            "rainfall_rate_mm_hr": actual_rainfall,
            "runoff_coefficient": res.get("runoff_coefficient", 0.85),
            "runoff_rate_mm_hr": round(actual_rainfall * res.get("runoff_coefficient", 0.85), 2),
            "accumulation_interval_hours": 1.0,
            "runoff_depth_cm": res.get("runoff_depth_cm", 0.0),
            "terrain_elevation_m": elevation_val if has_real_terrain else None,
            "terrain_factor": res.get("ponding_factor", 1.0),
            "flow_direction": "D8_GRID_ROUTING",
            "flow_accumulation": res.get("flow_accumulation_cells", 0),
            "water_depth_cm": water_depth,
            "risk_level": risk_level,
            "drainage_used": False,
            "drainage": drainage_eval,
            "provenance": prov
        }
