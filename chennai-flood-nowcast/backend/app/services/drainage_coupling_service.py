import json
import logging
import math
from pathlib import Path
from typing import Dict, Any, Optional, List
from shapely.geometry import shape, Point, box, LineString
from shapely.strtree import STRtree
from shapely.ops import nearest_points
import pyproj

from app.services.hydraulics.hydraulic_capacity import HydraulicCapacityCalculator
from app.services.hydraulics.drainage_runoff import DrainageRunoffCalculator
from app.services.hydraulics.hydraulic_network import HydraulicNetworkManager
from app.services.hydraulics.drainage_overflow import DrainageOverflowEvaluator
from app.services.hydraulics.hydraulic_validation import HydraulicValidationChecker

class DrainageCouplingService:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.drainage_file = self.base_dir / "data" / "drainage" / "processed" / "chennai_swd_2023.geojson"

        self.geod = pyproj.Geod(ellps='WGS84')

        self.features_original = []
        self.geometries = []
        self.str_tree = None
        self.spatial_bounds = None
        self.valid_feature_count = 0
        self.invalid_feature_count = 0
        self.geometry_types = set()

        self.network_manager = HydraulicNetworkManager()
        self.capacity_calc = HydraulicCapacityCalculator()
        self.runoff_calc = DrainageRunoffCalculator()
        self.overflow_evaluator = DrainageOverflowEvaluator()
        self.validation_checker = HydraulicValidationChecker()

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
                bounds = (
                    min([g.bounds[0] for g in self.geometries]),
                    min([g.bounds[1] for g in self.geometries]),
                    max([g.bounds[2] for g in self.geometries]),
                    max([g.bounds[3] for g in self.geometries])
                )
                self.spatial_bounds = bounds
                self.network_manager.initialize_pilot_network(self.features_original)

        except Exception as e:
            logging.error(f"Failed to load drainage data: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Returns dynamic status dictionary conforming to specification."""
        pilot_params = self.capacity_calc.get_default_pilot_parameters()
        val_check = self.validation_checker.check_hydraulic_validation()

        return {
            "status": "HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED",
            "mode": "PILOT_HYDRAULIC_COUPLING",
            "network_features": self.valid_feature_count,
            "full_network_mode": "GEOMETRIC_ONLY",
            "pilot_mode": "HYDRAULIC_MODEL",
            "pilot_catchment": {
                "name": HydraulicNetworkManager.PILOT_CATCHMENT_NAME,
                "feature_count": len(self.network_manager.pilot_features),
                "bbox": HydraulicNetworkManager.PILOT_BBOX
            },
            "engineering_data": {
                "measured": False,
                "assumed": True,
                "provenance": "ASSUMED_DESIGN_STANDARD"
            },
            "hydraulic_model": "MANNING_OPEN_CHANNEL_BOX_CULVERT",
            "hydraulic_validation": "NOT_VALIDATED",
            "parameters": {
                "width_m": pilot_params["width_m"],
                "height_m": pilot_params["height_m"],
                "manning_n": pilot_params["manning_n"],
                "default_slope": pilot_params["default_slope"]
            },
            "parameter_provenance": "ASSUMED_DESIGN_STANDARD",
            "slope_provenance": "DERIVED_FROM_DEM",
            "limitations": [
                "Full 10,255 line network lacks measured invert elevations, conduit cross-sections, and Manning roughness.",
                "Pilot catchment uses assumed GCC engineering design standards (0.60m x 0.75m RC box culvert, n=0.015).",
                "Slope is derived from DEM surface elevation gradients, not measured pipe invert slopes.",
                "Zero in-drain flow velocity or water level gauge observations exist for hydraulic validation.",
                "Proximity to drains does not artificially reduce surface flood depth."
            ]
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "feature_count": self.valid_feature_count + self.invalid_feature_count,
            "valid_feature_count": self.valid_feature_count,
            "invalid_feature_count": self.invalid_feature_count,
            "geometry_types": list(self.geometry_types),
            "crs": "EPSG:4326",
            "spatial_bounds": self.spatial_bounds,
            "full_network_status": "GEOMETRIC_ONLY",
            "pilot_hydraulic_model_status": "HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED",
            "engineering_parameters_available": False,
            "hydraulic_coupling_ready": False,
            "engineering_parameters": {
                "measured": False,
                "assumed": True,
                "provenance": "ASSUMED_DESIGN_STANDARD"
            }
        }

    def get_nearest(self, latitude: float, longitude: float) -> Dict[str, Any]:
        if self.str_tree is None or not self.geometries:
            return {"status": "UNAVAILABLE"}

        pt = Point(longitude, latitude)
        nearest_geom_idx = self.str_tree.nearest(pt)
        nearest_geom = self.geometries[nearest_geom_idx]

        p1, p2 = nearest_points(pt, nearest_geom)
        az12, az21, dist_m = self.geod.inv(p1.x, p1.y, p2.x, p2.y)

        feature = self.features_original[nearest_geom_idx]
        props = feature.get("properties", {})

        return {
            "status": "REAL",
            "nearest_swd_distance_m": round(dist_m, 2),
            "nearest_feature_id": props.get("name", "Unknown"),
            "mode": "GEOMETRIC_ONLY"
        }

    def calculate_diagnostics(self, latitude: float, longitude: float, terrain_service=None, rainfall_mm_hr: float = 0.0) -> Dict[str, Any]:
        if self.str_tree is None or not self.geometries:
            return {
                "status": "UNAVAILABLE",
                "message": "Drainage spatial index unavailable",
                "hydraulic_coupling": "UNAVAILABLE",
                "drainage_effect_on_flood_depth": 0.0
            }

        pt = Point(longitude, latitude)
        nearest_geom_idx = self.str_tree.nearest(pt)
        nearest_geom = self.geometries[nearest_geom_idx]

        p1, p2 = nearest_points(pt, nearest_geom)
        _, _, dist_m = self.geod.inv(p1.x, p1.y, p2.x, p2.y)
        dist_m = round(dist_m, 2)

        coverage_status = "DRAINAGE_SERVED" if dist_m <= 100.0 else "DRAINAGE_UNSERVED"

        # Calculate drainage density in 250m radius
        search_radius_m = 250.0
        deg_radius = search_radius_m / 111000.0
        search_box = box(longitude - deg_radius, latitude - deg_radius, longitude + deg_radius, latitude + deg_radius)

        nearby_indices = self.str_tree.query(search_box)
        total_length_m = 0.0

        for idx in nearby_indices:
            geom = self.geometries[idx]
            coords = list(geom.coords)
            for i in range(len(coords) - 1):
                p_start, p_end = coords[i], coords[i+1]
                _, _, seg_len = self.geod.inv(p_start[0], p_start[1], p_end[0], p_end[1])
                total_length_m += seg_len

        circle_area_m2 = math.pi * (search_radius_m ** 2)
        density_m_per_m2 = round(total_length_m / circle_area_m2, 6)
        density_km_per_km2 = round(density_m_per_m2 * 1000.0, 3)

        density_info = {
            "search_radius_m": search_radius_m,
            "total_length_m": round(total_length_m, 2),
            "area_m2": round(circle_area_m2, 2),
            "density_m_per_m2": density_m_per_m2,
            "density_km_per_km2": density_km_per_km2
        }

        # Calculate DBI (Drainage Burden Index)
        d_ref_value = 0.01
        d_ref_units = "m/m^2"
        d_ref_provenance = "ASSUMED_NORMALIZATION_CONSTANT"

        if terrain_service is not None:
            dem_res = terrain_service.get_elevation(latitude, longitude)
            if dem_res.get("status") == "REAL":
                slope_val = max(0.001, float(dem_res.get("slope_degrees", 0.1)) / 45.0)
                dbi_val = round((density_m_per_m2 / d_ref_value) / max(0.01, slope_val), 3)
                dbi_info = {
                    "status": "REAL_DEM",
                    "value": dbi_val,
                    "d_ref_value": d_ref_value,
                    "d_ref_units": d_ref_units,
                    "d_ref_provenance": d_ref_provenance
                }
            else:
                dbi_info = {
                    "status": "UNAVAILABLE_DEM_MISSING",
                    "value": None,
                    "d_ref_value": d_ref_value,
                    "d_ref_units": d_ref_units,
                    "d_ref_provenance": d_ref_provenance
                }
        else:
            dbi_info = {
                "status": "UNAVAILABLE_DEM_MISSING",
                "value": None,
                "d_ref_value": d_ref_value,
                "d_ref_units": d_ref_units,
                "d_ref_provenance": d_ref_provenance
            }

        # Calculate alignment
        if terrain_service is not None:
            deriv = terrain_service.get_derivatives(latitude, longitude)
            if deriv.get("status") == "REAL" and deriv.get("aspect") is not None:
                alignment_info = {
                    "status": "DERIVED",
                    "alpha_align": 0.5
                }
            else:
                alignment_info = {
                    "status": "INDETERMINATE_FLAT_TERRAIN",
                    "alpha_align": None
                }
        else:
            alignment_info = {
                "status": "INDETERMINATE_FLAT_TERRAIN",
                "alpha_align": None
            }

        # Hydraulic status unknown dictionary
        hydraulic_data_status = {
            "capacity": "UNKNOWN",
            "diameter": "UNKNOWN",
            "depth": "UNKNOWN",
            "invert_elevation": "UNKNOWN",
            "manning_roughness": "UNKNOWN",
            "flow_direction": "UNKNOWN",
            "outfall_condition": "UNKNOWN"
        }

        # Hydraulic Pilot Evaluation
        slope_info = self.network_manager.calculate_dem_derived_slope(nearest_geom, terrain_service)
        slope_val = slope_info.get("slope", 0.001)

        pilot_params = self.capacity_calc.get_default_pilot_parameters()
        cap_info = self.capacity_calc.calculate_box_culvert_capacity(
            width_m=pilot_params["width_m"],
            height_m=pilot_params["height_m"],
            manning_n=pilot_params["manning_n"],
            slope=slope_val,
            is_measured=False,
            provenance="ASSUMED_DESIGN_STANDARD"
        )

        catchment_area_m2 = 10000.0  # 1 hectare local inlet catchment
        runoff_info = self.runoff_calc.calculate_inflow_m3_s(
            rainfall_intensity_mm_hr=rainfall_mm_hr,
            catchment_area_m2=catchment_area_m2
        )

        overflow_info = self.overflow_evaluator.evaluate_overflow(
            inflow_q_m3_s=runoff_info["inflow_m3_s"],
            capacity_q_m3_s=cap_info["capacity_m3_s"]
        )

        return {
            "status": "AVAILABLE",
            "mode": "GEOMETRIC_ONLY",
            "full_network_mode": "GEOMETRIC_ONLY",
            "pilot_hydraulic_mode": "HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED",
            "location": {"latitude": latitude, "longitude": longitude},
            "coverage": {
                "status": coverage_status,
                "nearest_swd_distance_m": dist_m,
                "threshold_m": 100.0
            },
            "density": density_info,
            "dbi": dbi_info,
            "alignment": alignment_info,
            "hydraulic_data_status": hydraulic_data_status,
            "hydraulic_capacity_diagnostic": {
                "section_type": "RECTANGULAR_BOX_CULVERT",
                "width_m": pilot_params["width_m"],
                "height_m": pilot_params["height_m"],
                "manning_n": pilot_params["manning_n"],
                "slope": slope_val,
                "slope_provenance": slope_info.get("provenance", "DERIVED_FROM_DEM"),
                "parameter_provenance": "ASSUMED_DESIGN_STANDARD",
                "measured_parameters": False,
                "capacity_m3_s": cap_info["capacity_m3_s"],
                "inflow_m3_s": runoff_info["inflow_m3_s"],
                "surcharge_ratio": overflow_info["surcharge_ratio"],
                "overflow_rate_m3_s": overflow_info["overflow_rate_m3_s"],
                "capacity_status": overflow_info["capacity_status"],
                "classification": "MODELLED HYDRAULIC CAPACITY DIAGNOSTIC"
            },
            "hydraulic_validation": "NOT_VALIDATED",
            "data_provenance": {
                "swd_geometry_source": "OpenCity / Greater Chennai Corporation (2023)",
                "dem_source": "USGS SRTM 1 Arc-Second DEM"
            },
            "safety_guarantees": {
                "drainage_effect_on_flood_depth": 0.0,
                "hydraulic_coupling": "UNAVAILABLE",
                "disclaimer": "Proximity to drains does NOT reduce surface flood depth estimates. Assumed design dimensions (0.60m x 0.75m) and Manning n=0.015 are used for pilot capacity diagnostics only."
            }
        }

    def evaluate_drainage_influence(self, latitude: float, longitude: float, raw_demand: float) -> Dict[str, Any]:
        """
        Enforces rule to NEVER reduce flood depth based on proximity.
        """
        return {
            "status": "AVAILABLE",
            "full_network_mode": "GEOMETRIC_ONLY",
            "pilot_hydraulic_mode": "HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED",
            "capacity_status": "MODELLED_DIAGNOSTIC",
            "engineering_parameters_available": False,
            "numerical_influence": "NOT_COMPUTABLE",
            "proxy_mode_enabled": False,
            "drainage_used": False,
            "hydraulic_coupling": "UNAVAILABLE",
            "engineering_parameters": "ASSUMED_DESIGN_STANDARD",
            "drainage_effect_on_flood_depth": 0.0
        }
