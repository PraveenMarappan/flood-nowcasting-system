from typing import Dict, Any

class ModelProvenance:
    @staticmethod
    def get_provenance_metadata(
        model_version: str = "GRID_HYDROLOGY_V1",
        rainfall_source: str = "NASA GPM IMERG",
        rainfall_status: str = "REAL",
        is_simulated: bool = False
    ) -> Dict[str, Any]:
        """
        Builds scientifically honest provenance metadata for all model predictions.
        Exposes explicit labels: REAL, DERIVED, ASSUMED, CALIBRATED, SIMULATED, UNKNOWN.
        """
        return {
            "model_version": model_version,
            "model_type": "GRID-BASED HYDROLOGICAL FLOOD-RISK ESTIMATE" if model_version == "GRID_HYDROLOGY_V1" else "SPATIAL HEURISTIC FLOOD-DEPTH ESTIMATE",
            "rainfall_source": rainfall_source,
            "rainfall_source_resolution": "~0.1 degree (~10-11 km)",
            "rainfall_information_resolution": "~0.1 degree (~10-11 km)",
            "computational_grid_resolution": "~1 Arc-Second (~30 meters)",
            "resolution_warning": "Fine computational grid does not imply fine-resolution street-level rainfall observations.",
            "dem_source": "USGS SRTM 1 Arc-Second Global",
            "dem_resolution": "~30 meters",
            "routing_method": "D8_GRID_ROUTING" if model_version == "GRID_HYDROLOGY_V1" else "SPATIAL_TERRAIN_MULTIPLIER",
            "runoff_coefficient_source": "Configurable Land-Cover Proxy (ASSUMED)",
            "drainage_mode": "GEOMETRIC_ONLY",
            "hydraulic_coupling": "UNAVAILABLE",
            "validation_status": "NOT_VALIDATED",
            "calibration_status": "NOT_CALIBRATED",
            "forcing_status": "INCOMPLETE_128_OF_241" if rainfall_status == "HISTORICAL" else rainfall_status,
            "is_simulated": is_simulated,
            "provenance_map": {
                "rainfall": "SIMULATED" if is_simulated else ("REAL" if rainfall_status in ["REAL", "LIVE"] else "UNKNOWN"),
                "dem_elevation": "REAL",
                "flow_direction": "DERIVED",
                "flow_accumulation": "DERIVED",
                "runoff_coefficients": "ASSUMED",
                "drainage_capacity": "UNKNOWN",
                "flood_depth_calibration": "NOT_CALIBRATED",
                "historical_event_validation": "NOT_VALIDATED"
            }
        }
