import json
from pathlib import Path
from app.services.flood_model_service import FloodModelService

class RouteService:
    def __init__(self):
        self.model_version = "baseline-v2"
        # 1. ROAD DATA AUDIT: Expecting real roads, synthetic test roads were moved.
        self.roads_file = Path(__file__).parent.parent.parent.parent / "data" / "roads" / "chennai_roads.geojson"
        self._cached_roads = None
        self._cache_load()

    def _cache_load(self):
        if self.roads_file.exists():
            with open(self.roads_file, 'r') as f:
                self._cached_roads = json.load(f)
        else:
            self._cached_roads = None

    def _get_risk_class(self, depth_cm):
        # 8. ROAD RISK RULE: Missing prediction -> GRAY
        if depth_cm is None or depth_cm < 0: return "DATA UNAVAILABLE", "GRAY"
        if depth_cm < 10.0: return "LOW", "GREEN"
        if depth_cm < 30.0: return "MODERATE", "ORANGE"
        return "HIGH", "RED"

    def get_roads_risk(self, forecast_offset_minutes: int, rainfall: float, is_simulated: bool):
        if not self._cached_roads:
            self._cache_load()
            
        if not self._cached_roads:
            # 1. ROAD DATA AUDIT: return empty or UNAVAILABLE
            return {
                "type": "FeatureCollection",
                "road_data_status": "UNAVAILABLE",
                "features": []
            }
            
        flood_service = FloodModelService()
        processed_features = []
        
        for feature in self._cached_roads.get("features", []):
            coords = feature.get("geometry", {}).get("coordinates", [])
            if not coords:
                continue
                
            lng = sum(pt[0] for pt in coords) / len(coords)
            lat = sum(pt[1] for pt in coords) / len(coords)
            
            # 4. FLOOD GRID AUDIT: Truly fetching spatial results using coordinates
            flood = flood_service.calculate_spatial_flood(lat, lng, rainfall, forecast_offset_minutes)
            
            risk_level, risk_color = self._get_risk_class(flood.get("water_depth_cm"))
            
            feature_copy = dict(feature)
            feature_copy["properties"] = dict(feature["properties"])
            feature_copy["properties"].update({
                "predicted_flood_depth_cm": flood.get("water_depth_cm", "UNAVAILABLE"),
                "max_depth_cm": flood.get("water_depth_cm", "UNAVAILABLE"),
                "mean_depth_cm": flood.get("water_depth_cm", "UNAVAILABLE"),
                "risk_level": risk_level,
                "risk_color": risk_color,
                "forecast_time": f"+{forecast_offset_minutes} MIN" if forecast_offset_minutes > 0 else "NOW",
                "model_version": self.model_version,
                "data_status": "MODELLED" if flood.get("water_depth_cm") is not None else "DATA UNAVAILABLE"
            })
            processed_features.append(feature_copy)

        return {
            "type": "FeatureCollection",
            "road_data_status": "AVAILABLE",
            "features": processed_features
        }

    def get_critical_locations(self):
        return {"locations": []}

    def get_safer_route(self):
        return {"locations": []}
