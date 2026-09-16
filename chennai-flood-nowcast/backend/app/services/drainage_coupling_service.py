import json
from pathlib import Path

class DrainageCouplingService:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
        self.drainage_file = self.base_dir / "drainage" / "chennai_drainage.geojson"

    def get_status(self) -> dict:
        if not self.drainage_file.exists():
            return {
                "status": "UNAVAILABLE",
                "source": "None",
                "feature_count": 0,
                "feature_types": [],
                "crs": "Unknown",
                "engineering_parameters": {
                    "diameter": "UNAVAILABLE",
                    "slope": "UNAVAILABLE",
                    "capacity": "UNAVAILABLE",
                    "condition": "UNAVAILABLE",
                    "flow_direction": "UNAVAILABLE",
                    "depth": "UNAVAILABLE"
                },
                "flood_model_integration": "NOT_COMPUTABLE"
            }

        try:
            with open(self.drainage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {
                "status": "ERROR",
                "source": "Chennai Drainage GeoJSON",
                "feature_count": 0,
                "flood_model_integration": "NOT_COMPUTABLE",
                "error": "Failed to parse GeoJSON"
            }

        features = data.get("features", [])
        types = set()
        for feature in features:
            props = feature.get("properties", {})
            t = props.get("waterway") or props.get("type") or props.get("drain") or "unknown"
            types.add(t)

        return {
            "status": "PARTIAL",
            "source": "Chennai Drainage GeoJSON",
            "feature_count": len(features),
            "feature_types": list(types),
            "crs": "EPSG:4326",  # Standard GeoJSON CRS
            "engineering_parameters": {
                "diameter": "UNAVAILABLE",
                "slope": "UNAVAILABLE",
                "capacity": "UNAVAILABLE",
                "condition": "UNAVAILABLE",
                "flow_direction": "UNAVAILABLE",
                "depth": "UNAVAILABLE"
            },
            "capacity_availability": "UNAVAILABLE",
            "flood_model_integration": "NOT_COMPUTABLE"
        }

    def evaluate_drainage_influence(self, latitude: float, longitude: float, raw_demand: float) -> dict:
        """
        Determines if the drainage dataset has enough capacity information to affect the flood depth numerically.
        Returns the drainage coupling status.
        """
        # We rely on get_status to check if parameters exist.
        status_info = self.get_status()
        
        has_real = self.drainage_file.exists()
        
        # In a real model, we would compute a distance query to nearest drainage pipe 
        # using the lat/long, identify its capacity from properties, and subtract it from raw_demand.
        
        return {
            "status": "PARTIAL" if has_real else "UNAVAILABLE",
            "capacity_status": "UNAVAILABLE",
            "engineering_parameters_available": False,
            "numerical_influence": "NOT_COMPUTABLE",
            "proxy_mode_enabled": False
        }
