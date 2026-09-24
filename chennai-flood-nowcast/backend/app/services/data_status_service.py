class DataStatusService:
    def get_status(self, rainfall_status: str, dem_status: str, drainage_status: dict) -> dict:
        
        confidence = "MEDIUM" if (rainfall_status in ["REAL", "LIVE"] and dem_status == "REAL") else "LOW"
        
        drainage_label = "PARTIAL / NOT VERIFIED" if drainage_status.get("status") == "PARTIAL" else "UNAVAILABLE"
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
                    "geometry_available": drainage_status.get("status") == "PARTIAL",
                    "hydraulic_data_available": False,
                    "used_in_flood_model": False,
                    "drainage_mode": "GEOMETRIC_ONLY"
                },
                "flood_depth": {
                    "status": "MODELLED",
                    "model_version": "GRID_HYDROLOGY_V1",
                    "model_type": "GRID-BASED HYDROLOGICAL FLOOD-RISK ESTIMATE",
                    "calibration_status": "NOT_CALIBRATED",
                    "validation_status": "NOT_VALIDATED"
                },
                "forecast": {
                    "status": "MODELLED",
                    "source": "Grid-Based Hydrological Forecast Decay",
                    "model_version": "GRID_HYDROLOGY_V1"
                }
            }
        }
