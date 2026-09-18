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
            
            flood_service = FloodModelService()
            self._road_spatial_params = []
            for feature in self._cached_roads.get("features", []):
                coords = feature.get("geometry", {}).get("coordinates", [])
                if not coords:
                    self._road_spatial_params.append(None)
                    continue
                lng = sum(pt[0] for pt in coords) / len(coords)
                lat = sum(pt[1] for pt in coords) / len(coords)
                terrain = flood_service.terrain_service.get_derivatives(lat, lng)
                conc = terrain.get("acc_prioritization_factor", 1.0)
                catchment = flood_service.catchment_service.get_catchment_properties(lat, lng)
                c_val = catchment.get("impervious_fraction", 0.85)
                self._road_spatial_params.append((c_val, conc))
        else:
            self._cached_roads = None
            self._road_spatial_params = []

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
            
        processed_features = []
        features = self._cached_roads.get("features", [])
        
        # Precompute recession_mult and forecast_type for forecast_offset_minutes
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
            
        for i, feature in enumerate(features):
            params = self._road_spatial_params[i] if i < len(self._road_spatial_params) else None
            if not params:
                continue
                
            c_val, conc = params
            
            if rainfall <= 0 and forecast_offset_minutes == 0:
                water_depth = 0.0
            else:
                runoff_depth_cm = (rainfall * c_val * 1.0) * 0.1
                base_water_depth_cm = runoff_depth_cm * conc
                if rainfall > 0:
                    water_depth = base_water_depth_cm + (rainfall * (1.0 - recession_mult) * 0.1)
                else:
                    water_depth = base_water_depth_cm * recession_mult
                    
            water_depth_rounded = round(water_depth, 2)
            risk_level, risk_color = self._get_risk_class(water_depth_rounded)
            
            feature_copy = dict(feature)
            feature_copy["properties"] = dict(feature["properties"])
            feature_copy["properties"].update({
                "predicted_flood_depth_cm": water_depth_rounded,
                "max_depth_cm": water_depth_rounded,
                "mean_depth_cm": water_depth_rounded,
                "risk_level": risk_level,
                "risk_color": risk_color,
                "forecast_time": f"+{forecast_offset_minutes} MIN" if forecast_offset_minutes > 0 else "NOW",
                "model_version": self.model_version,
                "data_status": "MODELLED"
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
