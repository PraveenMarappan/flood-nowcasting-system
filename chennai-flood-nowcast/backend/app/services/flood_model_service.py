from datetime import datetime
from app.services.runoff_service import RunoffEstimationService
from app.services.drainage_coupling_service import DrainageCouplingService

class FloodModelService:
    def __init__(self):
        self.runoff_service = RunoffEstimationService()
        self.drainage_service = DrainageCouplingService()
        self.model_version = "baseline-v1"
        self.calibration_status = "NOT_CALIBRATED"

    def calculate_current_flood(self, actual_rainfall: float, elevation_val: float, has_real_terrain: bool, latitude: float, longitude: float):
        # 1. Rainfall -> Runoff
        # R = rainfall intensity [mm/hr]
        # Q_r = R * C (C=0.8 from runoff_service)
        runoff_rate_mm_hr = self.runoff_service.estimate_runoff(actual_rainfall)
        
        # 2. Time Integration
        accumulation_interval_hours = 1.0 # explicit delta-T
        runoff_depth_mm = runoff_rate_mm_hr * accumulation_interval_hours
        runoff_depth_cm = runoff_depth_mm * 0.1
        
        # 3. Terrain Factor
        terrain_factor = 1.0 
        if has_real_terrain and elevation_val is not None:
            if elevation_val < 5: terrain_factor = 1.8
            elif elevation_val < 15: terrain_factor = 1.2
            else: terrain_factor = 0.5 
            
        # 4. Modelled Surface Depth
        water_depth = runoff_depth_cm * terrain_factor
        
        # 5. Risk Classification (based on modelled depth instead of just rainfall)
        risk_level = "NORMAL"
        if water_depth > 20.0:
            risk_level = "CRITICAL"
        elif water_depth > 10.0:
            risk_level = "HIGH"
        elif water_depth > 3.0:
            risk_level = "MODERATE"
        elif water_depth > 0.1:
            risk_level = "LOW"
            
        drainage_evaluation = self.drainage_service.evaluate_drainage_influence(latitude, longitude, water_depth)

        return {
            "status": "MODELLED",
            "source": "Baseline Hydrological Model",
            "model_version": self.model_version,
            "calibration_status": self.calibration_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "rainfall_rate_mm_hr": actual_rainfall,
            "runoff_coefficient": self.runoff_service.runoff_coefficient,
            "runoff_rate_mm_hr": round(runoff_rate_mm_hr, 2),
            "accumulation_interval_hours": accumulation_interval_hours,
            "runoff_depth_cm": round(runoff_depth_cm, 2),
            "terrain_elevation_m": elevation_val if has_real_terrain else None,
            "terrain_factor": terrain_factor,
            "water_depth_cm": round(water_depth, 2),
            "risk_level": risk_level,
            "drainage_used": False,
            "drainage": drainage_evaluation
        }
