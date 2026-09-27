from app.services.validation.status_evaluator import ValidationStatusEvaluator

class DataStatusService:
    def __init__(self):
        self.status_evaluator = ValidationStatusEvaluator()

    def get_status(self, rainfall_status: str, dem_status: str, drainage_status: dict) -> dict:
        val_eval = self.status_evaluator.evaluate_status()
        dynamic_val_status = val_eval.get("status", "PARTIALLY_VALIDATED")

        confidence = "HIGH" if (rainfall_status in ["REAL", "LIVE"] and dem_status == "REAL") else "MEDIUM"
        
        drainage_label = "REAL GEOMETRY — HYDRAULICS UNAVAILABLE" if drainage_status.get("status") in ["REAL", "PARTIAL"] else "UNAVAILABLE"
        dem_label = "REAL" if dem_status == "REAL" else "UNAVAILABLE"
        
        return {
            "overall_health": "OK",
            "data_confidence": confidence,
            "sources": {
                "rainfall": {
                    "status": "REAL" if rainfall_status in ["REAL", "LIVE"] else rainfall_status,
                    "source": "NASA GPM IMERG (~0.1 deg)"
                },
                "dem_terrain": {
                    "status": dem_label,
                    "source": "USGS SRTM 1 Arc-Second Global (~30m)"
                },
                "drainage": {
                    "status": drainage_label,
                    "geometry_available": True,
                    "hydraulic_data_available": False,
                    "used_in_flood_model": True,
                    "drainage_mode": "GEOMETRIC_PROXIMITY_DIAGNOSTIC"
                },
                "flood_depth": {
                    "status": "MODELLED",
                    "model_version": "GRID_HYDROLOGY_V1",
                    "model_type": "GRID-BASED HYDROLOGICAL FLOOD-RISK ESTIMATE",
                    "calibration_status": "COMPLETED — OCCURRENCE-BASED",
                    "validation_status": dynamic_val_status
                },
                "forecast": {
                    "status": "MODELLED",
                    "source": "Grid-Based Hydrological Forecast Decay",
                    "model_version": "GRID_HYDROLOGY_V1"
                }
            }
        }
