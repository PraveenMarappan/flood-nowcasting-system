import json
import logging
from pathlib import Path
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely.ops import nearest_points
import pyproj

class DrainageCouplingService:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.drainage_file = self.base_dir / "data" / "drainage" / "processed" / "chennai_swd_2023.geojson"
        
        # Geodesic converter for meters (WGS84)
        self.geod = pyproj.Geod(ellps='WGS84')
        
        self.features_original = []
        self.geometries = []
        self.str_tree = None
        self.spatial_bounds = None
        self.valid_feature_count = 0
        self.invalid_feature_count = 0
        self.geometry_types = set()
        
        self._load_and_index()

    def _load_and_index(self):
        if not self.drainage_file.exists():
            return
            
        try:
            with open(self.drainage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            features = data.get("features", [])
            for f in features:
                try:
                    geom = shape(f["geometry"])
                    if geom.is_empty:
                        self.invalid_feature_count += 1
                        continue
                    
                    self.geometries.append(geom)
                    self.features_original.append(f)
                    self.geometry_types.add(geom.geom_type)
                    self.valid_feature_count += 1
                except Exception:
                    self.invalid_feature_count += 1
                    
            if self.geometries:
                self.str_tree = STRtree(self.geometries)
                bounds = min([g.bounds[0] for g in self.geometries]), \
                         min([g.bounds[1] for g in self.geometries]), \
                         max([g.bounds[2] for g in self.geometries]), \
                         max([g.bounds[3] for g in self.geometries])
                self.spatial_bounds = bounds
                
        except Exception as e:
            logging.error(f"Failed to load drainage data: {e}")

    def get_status(self) -> dict:
        status = "PARTIAL" if self.str_tree is not None else "UNAVAILABLE"
        
        return {
            "status": status,
            "geometry_available": self.str_tree is not None,
            "hydraulic_data_available": False,
            "engineering_parameters_available": False,
            "used_in_flood_model": False,
            "source": "OpenCity / Greater Chennai Corporation",
            "dataset": "Chennai Storm Water Drains - SWD - Map 2023",
            "feature_count": self.valid_feature_count
        }

    def get_summary(self) -> dict:
        return {
            "feature_count": self.valid_feature_count + self.invalid_feature_count,
            "valid_feature_count": self.valid_feature_count,
            "invalid_feature_count": self.invalid_feature_count,
            "geometry_types": list(self.geometry_types),
            "crs": "EPSG:4326",
            "spatial_bounds": self.spatial_bounds,
            "engineering_parameters_available": False,
            "hydraulic_coupling_ready": False
        }

    def get_nearest(self, latitude: float, longitude: float):
        if self.str_tree is None or not self.geometries:
            return {"status": "UNAVAILABLE"}

        pt = Point(longitude, latitude)
        # STRtree nearest works natively in Euclidean. Safe proxy for dense local scale.
        nearest_geom_idx = self.str_tree.nearest(pt)
        nearest_geom = self.geometries[nearest_geom_idx]
        
        # Calculate strict geodesic distance in meters
        p1, p2 = nearest_points(pt, nearest_geom)
        az12, az21, dist_m = self.geod.inv(p1.x, p1.y, p2.x, p2.y)
        
        feature = self.features_original[nearest_geom_idx]
        props = feature.get("properties", {})
        
        return {
            "status": "REAL",
            "nearest_swd_distance_m": round(dist_m, 2),
            "nearest_feature_id": props.get("name", "Unknown")
        }

    def evaluate_drainage_influence(self, latitude: float, longitude: float, raw_demand: float) -> dict:
        """
        Kept explicit rules to NEVER couple hydraulically
        """
        return {
            "status": "PARTIAL" if self.str_tree is not None else "UNAVAILABLE",
            "capacity_status": "UNAVAILABLE",
            "engineering_parameters_available": False,
            "numerical_influence": "NOT_COMPUTABLE",
            "proxy_mode_enabled": False,
            "drainage_used": False,
            "hydraulic_coupling": "UNAVAILABLE",
            "engineering_parameters": "UNAVAILABLE"
        }
