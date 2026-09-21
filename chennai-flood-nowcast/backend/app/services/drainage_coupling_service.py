import json
import logging
import math
from pathlib import Path
from shapely.geometry import shape, Point, box, LineString
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

    def calculate_diagnostics(self, latitude: float, longitude: float, terrain_service=None) -> dict:
        if self.str_tree is None or not self.geometries:
            return {
                "status": "UNAVAILABLE",
                "message": "Drainage spatial index unavailable",
                "hydraulic_coupling": "UNAVAILABLE",
                "drainage_effect_on_flood_depth": 0.0,
                "hydraulic_data_status": {
                    "capacity": "UNKNOWN",
                    "diameter": "UNKNOWN",
                    "depth": "UNKNOWN",
                    "invert_elevation": "UNKNOWN",
                    "manning_roughness": "UNKNOWN",
                    "flow_direction": "UNKNOWN",
                    "outfall_condition": "UNKNOWN"
                }
            }

        pt = Point(longitude, latitude)
        nearest_geom_idx = self.str_tree.nearest(pt)
        nearest_geom = self.geometries[nearest_geom_idx]
        
        # Calculate strict geodesic distance in meters to nearest SWD
        p1, p2 = nearest_points(pt, nearest_geom)
        _, _, dist_m = self.geod.inv(p1.x, p1.y, p2.x, p2.y)
        dist_m = round(dist_m, 2)

        # 1. DRAINAGE COVERAGE (GEOMETRIC ONLY)
        coverage_status = "DRAINAGE_SERVED" if dist_m <= 100.0 else "DRAINAGE_UNSERVED"
        
        # 2. DRAINAGE DENSITY (Local search radius = 250m)
        radius_m = 250.0
        deg_buffer = radius_m / 111000.0
        bbox = (longitude - deg_buffer, latitude - deg_buffer, longitude + deg_buffer, latitude + deg_buffer)
        
        try:
            candidate_indices = self.str_tree.query(box(*bbox))
        except Exception:
            candidate_indices = list(range(len(self.geometries)))

        total_swd_length_m = 0.0
        for idx in candidate_indices:
            geom = self.geometries[idx]
            p_near1, p_near2 = nearest_points(pt, geom)
            _, _, d_near = self.geod.inv(p_near1.x, p_near1.y, p_near2.x, p_near2.y)
            if d_near <= radius_m:
                coords = list(geom.coords)
                for i in range(len(coords) - 1):
                    x1, y1 = coords[i]
                    x2, y2 = coords[i+1]
                    seg_p1, seg_p2 = nearest_points(pt, LineString([(x1, y1), (x2, y2)]))
                    _, _, seg_d = self.geod.inv(seg_p1.x, seg_p1.y, seg_p2.x, seg_p2.y)
                    if seg_d <= radius_m:
                        _, _, seg_len = self.geod.inv(x1, y1, x2, y2)
                        total_swd_length_m += seg_len

        search_area_m2 = math.pi * (radius_m ** 2)
        density_m_per_m2 = round(total_swd_length_m / search_area_m2, 6)
        density_km_per_km2 = round(density_m_per_m2 * 1000.0, 3)

        # 3. DRAINAGE DEFICIT INDEX (DBI)
        # Formula: DBI = log10(A_acc + 1) / (1 + (D_swd / D_ref))
        # D_ref = 0.01 m/m^2 (Assumption / Normalization Constant)
        D_ref = 0.01
        dbi_val = None
        dbi_status = "UNAVAILABLE_DEM_MISSING"

        flow_acc_cells = 0

        if terrain_service is not None:
            terrain_derivs = terrain_service.get_derivatives(latitude, longitude)
            if terrain_derivs.get("status") in ["MODELLED", "REAL"]:
                flow_acc_cells = terrain_derivs.get("flow_accumulation_cells", 0)
                if flow_acc_cells > 0:
                    dbi_val = math.log10(flow_acc_cells + 1) / (1.0 + (density_m_per_m2 / D_ref))
                    dbi_val = round(dbi_val, 3)
                    dbi_status = "REAL_DEM"

        # 4. SURFACE-FLOW / SWD ALIGNMENT (alpha_align)
        # alpha_align = abs(cos(theta_surface - theta_swd))
        alpha_align = None
        alpha_align_status = "INDETERMINATE_FLAT_TERRAIN"

        if terrain_service is not None:
            elev_data = terrain_service.get_elevation(latitude, longitude)
            if elev_data.get("status") == "REAL" and getattr(terrain_service, '_dem_cache', None) is not None:
                row, col = elev_data.get("row"), elev_data.get("col")
                dem = terrain_service._dem_cache
                if row is not None and col is not None and 1 <= row < dem.shape[0] - 1 and 1 <= col < dem.shape[1] - 1:
                    dz_dx = (float(dem[row, col+1]) - float(dem[row, col-1])) / 60.0
                    dz_dy = (float(dem[row+1, col]) - float(dem[row-1, col])) / 60.0
                    slope_mag = math.sqrt(dz_dx**2 + dz_dy**2)
                    if slope_mag >= 0.001:
                        theta_surface = math.atan2(-dz_dy, -dz_dx)
                        near_coords = list(nearest_geom.coords)
                        if len(near_coords) >= 2:
                            dx = near_coords[1][0] - near_coords[0][0]
                            dy = near_coords[1][1] - near_coords[0][1]
                            theta_swd = math.atan2(dy, dx)
                            alpha_align = round(abs(math.cos(theta_surface - theta_swd)), 3)
                            alpha_align_status = "MODELLED_SURFACE_ALIGNMENT"

        return {
            "status": "AVAILABLE",
            "mode": "GEOMETRIC_ONLY",
            "location": {"latitude": latitude, "longitude": longitude},
            "coverage": {
                "status": coverage_status,
                "nearest_swd_distance_m": dist_m,
                "threshold_m": 100.0,
                "mode": "GEOMETRIC_ONLY"
            },
            "density": {
                "local_swd_length_m": round(total_swd_length_m, 2),
                "search_radius_m": radius_m,
                "search_area_m2": round(search_area_m2, 2),
                "density_m_per_m2": density_m_per_m2,
                "density_km_per_km2": density_km_per_km2,
                "label": "Drainage Density (Line Length per Search Area)"
            },
            "dbi": {
                "value": dbi_val,
                "status": dbi_status,
                "flow_accumulation_cells": flow_acc_cells,
                "d_ref_value": D_ref,
                "d_ref_units": "m/m^2",
                "d_ref_provenance": "ASSUMED_NORMALIZATION_CONSTANT",
                "d_ref_description": "Normalization constant for urban drainage density scale, not an engineering standard."
            },
            "alignment": {
                "alpha_align": alpha_align,
                "status": alpha_align_status,
                "description": "Absolute cosine of angle between DEM surface slope aspect and local SWD segment orientation."
            },
            "hydraulic_data_status": {
                "capacity": "UNKNOWN",
                "diameter": "UNKNOWN",
                "depth": "UNKNOWN",
                "invert_elevation": "UNKNOWN",
                "manning_roughness": "UNKNOWN",
                "flow_direction": "UNKNOWN",
                "outfall_condition": "UNKNOWN"
            },
            "data_provenance": {
                "swd_geometry_source": "OpenCity / Greater Chennai Corporation (2023)",
                "dem_source": "USGS SRTM 1 Arc-Second DEM"
            },
            "safety_guarantees": {
                "drainage_effect_on_flood_depth": 0.0,
                "hydraulic_coupling": "UNAVAILABLE",
                "disclaimer": "Drainage geometry is used for spatial diagnostics only. Proximity to drains does NOT reduce flood depth estimates."
            }
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

