import json
from pathlib import Path
from collections import OrderedDict
from typing import Optional, Dict, Any, Tuple

from app.services.flood_model_service import FloodModelService

class RouteService:
    def __init__(self, model_version: str = "GRID_HYDROLOGY_V1"):
        self.model_version = model_version
        self.roads_file = Path(__file__).parent.parent.parent.parent / "data" / "roads" / "chennai_roads.geojson"
        self._cached_roads = None
        self._road_spatial_params = []
        self._road_bboxes = []
        
        self.flood_model_service = FloodModelService(default_version=self.model_version)

        self._risk_cache = OrderedDict()
        self._risk_cache_max = 32

        self._cache_load()

    def _cache_load(self):
        if self.roads_file.exists():
            with open(self.roads_file, 'r') as f:
                self._cached_roads = json.load(f)
            
            self._road_spatial_params = []
            self._road_bboxes = []
            for feature in self._cached_roads.get("features", []):
                coords = feature.get("geometry", {}).get("coordinates", [])
                if not coords:
                    self._road_spatial_params.append(None)
                    self._road_bboxes.append(None)
                    continue
                lng = sum(pt[0] for pt in coords) / len(coords)
                lat = sum(pt[1] for pt in coords) / len(coords)
                terrain = self.flood_model_service.terrain_service.get_derivatives(lat, lng)
                flow_acc_cells = terrain.get("flow_accumulation_cells", 0)
                elevation_m = terrain.get("elevation_m")
                catchment = self.flood_model_service.catchment_service.get_catchment_properties(lat, lng)
                c_val = catchment.get("impervious_fraction", 0.85)
                self._road_spatial_params.append((lat, lng, c_val, flow_acc_cells, elevation_m))

                lngs = [pt[0] for pt in coords]
                lats = [pt[1] for pt in coords]
                self._road_bboxes.append((min(lngs), min(lats), max(lngs), max(lats)))
        else:
            self._cached_roads = None
            self._road_spatial_params = []
            self._road_bboxes = []

    def _get_risk_class(self, depth_cm: Optional[float]) -> Tuple[str, str]:
        if depth_cm is None or depth_cm < 0:
            return "DATA UNAVAILABLE", "GRAY"
        if depth_cm <= 0.1:
            return "NORMAL", "WHITE"
        if depth_cm < 10.0:
            return "LOW", "LIGHT_BLUE"
        if depth_cm < 30.0:
            return "MODERATE", "ORANGE"
        return "HIGH", "RED"

    def _round_rainfall(self, rainfall: float) -> float:
        return round(rainfall, 2)

    def _bbox_intersects(self, road_bbox, query_bbox) -> bool:
        if road_bbox is None or query_bbox is None:
            return False
        r_min_lng, r_min_lat, r_max_lng, r_max_lat = road_bbox
        q_min_lng, q_min_lat, q_max_lng, q_max_lat = query_bbox
        return not (r_max_lng < q_min_lng or r_min_lng > q_max_lng or
                    r_max_lat < q_min_lat or r_min_lat > q_max_lat)

    def _put_cache(self, key, value):
        if key in self._risk_cache:
            self._risk_cache.move_to_end(key)
            self._risk_cache[key] = value
        else:
            if len(self._risk_cache) >= self._risk_cache_max:
                self._risk_cache.popitem(last=False)
            self._risk_cache[key] = value

    def _get_cache(self, key):
        if key in self._risk_cache:
            self._risk_cache.move_to_end(key)
            return self._risk_cache[key]
        return None

    def get_roads_risk(
        self,
        forecast_offset_minutes: int,
        rainfall: float,
        is_simulated: bool,
        bbox: tuple = None,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self._cached_roads:
            self._cache_load()
            
        if not self._cached_roads:
            return {
                "type": "FeatureCollection",
                "road_data_status": "UNAVAILABLE",
                "features": []
            }

        active_version = model_version or self.model_version
        rainfall_key = self._round_rainfall(rainfall)
        bbox_key = tuple(round(v, 6) for v in bbox) if bbox else None
        cache_key = (rainfall_key, forecast_offset_minutes, is_simulated, bbox_key, active_version)

        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        features = self._cached_roads.get("features", [])
        processed_features = []

        for i, feature in enumerate(features):
            params = self._road_spatial_params[i] if i < len(self._road_spatial_params) else None
            if not params:
                continue

            if bbox is not None:
                road_bb = self._road_bboxes[i] if i < len(self._road_bboxes) else None
                if not self._bbox_intersects(road_bb, bbox):
                    continue
                
            lat, lng, c_val, flow_acc_cells, elevation_m = params

            if active_version == "LEGACY_HEURISTIC":
                conc = 1.0 + (min(2.5, math.log10(max(1, flow_acc_cells)) * 0.2) if flow_acc_cells > 0 else 0.0)
                recession_mult = 1.0
                if forecast_offset_minutes >= 180: recession_mult = 0.05
                elif forecast_offset_minutes >= 150: recession_mult = 0.1
                elif forecast_offset_minutes >= 120: recession_mult = 0.2
                elif forecast_offset_minutes >= 90: recession_mult = 0.5
                elif forecast_offset_minutes >= 60: recession_mult = 0.7
                elif forecast_offset_minutes >= 30: recession_mult = 0.9

                if rainfall <= 0 and forecast_offset_minutes == 0:
                    water_depth = 0.0
                else:
                    runoff_depth_cm = (rainfall * c_val * 1.0) * 0.1
                    base_water_depth_cm = runoff_depth_cm * conc
                    if rainfall > 0:
                        water_depth = base_water_depth_cm + (rainfall * (1.0 - recession_mult) * 0.1)
                    else:
                        water_depth = base_water_depth_cm * recession_mult
            else:
                res = self.flood_model_service.grid_engine.compute_flood_depth(
                    rainfall_rate_mm_hr=rainfall,
                    latitude=lat,
                    longitude=lng,
                    elevation_m=elevation_m,
                    flow_acc_cells=flow_acc_cells,
                    forecast_offset_minutes=forecast_offset_minutes,
                    runoff_coefficient=c_val,
                    is_simulated=is_simulated
                )
                water_depth = res["water_depth_cm"]

            water_depth_rounded = round(float(water_depth), 2)
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
                "model_version": active_version,
                "data_status": "MODELLED"
            })
            processed_features.append(feature_copy)

        result = {
            "type": "FeatureCollection",
            "road_data_status": "AVAILABLE",
            "model_version": active_version,
            "features": processed_features
        }

        self._put_cache(cache_key, result)
        return result

    def get_critical_locations(self):
        return {"locations": []}

    def get_safer_route(self):
        return {"locations": []}
