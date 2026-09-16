class DataStatusService:
    def get_status(self, rainfall_status: str, dem_status: str, drainage_status: dict) -> dict:
        
        confidence = "LOW"
        if rainfall_status == "REAL" and dem_status == "REAL":
            confidence = "MEDIUM" # Since not calibrated
        
        drainage_label = "PARTIAL / NOT VERIFIED" if drainage_status.get("status") == "PARTIAL" else "UNAVAILABLE"
        dem_label = "REAL" if dem_status == "REAL" else "UNAVAILABLE"
        
        return {
            "overall_health": "OK",
            "data_confidence": confidence,
            "sources": {
                "rainfall": {"status": "REAL" if rainfall_status == "REAL" else rainfall_status, "source": "NASA GPM IMERG"},
                "dem_terrain": {"status": dem_label, "source": "USGS SRTM 1 Arc-Second Global"},
                "drainage": {"status": drainage_label, "geometry_available": drainage_status.get("status") == "PARTIAL", "hydraulic_data_available": False, "used_in_flood_model": False},
                "flood_depth": {"status": "MODELLED", "source": "Baseline Hydrological Model", "calibration_status": "NOT_CALIBRATED"},
                "forecast": {"status": "MODELLED", "source": "Baseline Hydrological Forecast"}
            }
        }
