import math
import logging
from typing import Dict, Any, List, Optional
from shapely.geometry import shape, Point, LineString, box
from shapely.strtree import STRtree
from shapely.ops import nearest_points
import pyproj

class HydraulicNetworkManager:
    """
    Manages spatial & hydraulic representation of the Chennai Storm Water Drain (SWD) network.

    Full Network (10,255 LineStrings):
    - Status: GEOMETRIC ONLY
    - Attributes: Geometry loaded; measured invert levels, conduit dimensions, and roughness are MISSING.

    Pilot Catchment (Adyar / Zone 10 Pilot Ward):
    - Status: HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED
    - Coverage: Identified spatial bounding box within Adyar / Zone 10 catchment.
    - Parameters: Standard GCC assumed design specifications (0.60m x 0.75m RC box culvert, Manning n=0.015).
    - Slope: DERIVED FROM DEM ground elevation gradient (not measured drain invert slope).
    """

    PILOT_CATCHMENT_NAME = "Adyar / Zone 10 Pilot Catchment"
    # Bounding box for Adyar / Zone 10 Pilot Catchment (approx 13.00N to 13.04N, 80.20E to 80.26E)
    PILOT_BBOX = (80.2000, 13.0000, 80.2600, 13.0400)

    def __init__(self):
        self.geod = pyproj.Geod(ellps='WGS84')
        self.full_feature_count = 0
        self.pilot_features = []
        self.pilot_geometries = []
        self.pilot_str_tree = None

    def initialize_pilot_network(self, features: List[dict]):
        """Identifies pilot catchment features from full network features."""
        self.full_feature_count = len(features)
        self.pilot_features = []
        self.pilot_geometries = []

        pilot_box = box(*self.PILOT_BBOX)

        for feat in features:
            try:
                geom = shape(feat["geometry"])
                if geom.is_empty:
                    continue
                if geom.intersects(pilot_box):
                    self.pilot_features.append(feat)
                    self.pilot_geometries.append(geom)
            except Exception:
                pass

        if self.pilot_geometries:
            self.pilot_str_tree = STRtree(self.pilot_geometries)

    def calculate_dem_derived_slope(
        self,
        geom: LineString,
        terrain_service=None
    ) -> Dict[str, Any]:
        """
        Calculates approximate segment slope S = delta_Z / L using DEM surface elevations.
        Provenance: DERIVED FROM DEM (not measured drain invert slope).
        """
        try:
            coords = list(geom.coords)
            if len(coords) < 2:
                return {"slope": 0.001, "provenance": "ASSUMED_DEFAULT_SLOPE"}

            p_start, p_end = coords[0], coords[-1]
            lon1, lat1 = p_start[0], p_start[1]
            lon2, lat2 = p_end[0], p_end[1]

            _, _, length_m = self.geod.inv(lon1, lat1, lon2, lat2)
            if length_m <= 0.001:
                return {"slope": 0.001, "provenance": "ASSUMED_DEFAULT_SLOPE"}

            if terrain_service is not None:
                elev1_res = terrain_service.get_elevation(lat1, lon1)
                elev2_res = terrain_service.get_elevation(lat2, lon2)

                e1 = elev1_res.get("elevation_m")
                e2 = elev2_res.get("elevation_m")

                if e1 is not None and e2 is not None:
                    delta_z = abs(float(e1) - float(e2))
                    slope = max(0.0001, delta_z / length_m)
                    return {
                        "slope": round(slope, 6),
                        "length_m": round(length_m, 2),
                        "delta_z_m": round(delta_z, 2),
                        "provenance": "DERIVED_FROM_DEM",
                        "measured_invert_slope": False,
                        "disclaimer": "Slope derived from DEM surface elevation difference. Drain invert elevation is unavailable."
                    }

        except Exception as e:
            logging.warning(f"Error computing DEM slope: {e}")

        return {
            "slope": 0.001,
            "length_m": 100.0,
            "provenance": "ASSUMED_DEFAULT_SLOPE",
            "measured_invert_slope": False
        }

    def get_pilot_summary(self) -> Dict[str, Any]:
        return {
            "name": self.PILOT_CATCHMENT_NAME,
            "feature_count": len(self.pilot_features),
            "bbox": self.PILOT_BBOX
        }

    def get_network_status_summary(self) -> Dict[str, Any]:
        return {
            "full_network": {
                "status": "GEOMETRIC_ONLY",
                "feature_count": self.full_feature_count,
                "measured_engineering_data": False,
                "description": "10,255 SWD LineStrings loaded for spatial overlay. Engineering attributes (dimensions, invert levels, roughness) unavailable for full network."
            },
            "pilot_catchment": {
                "name": self.PILOT_CATCHMENT_NAME,
                "status": "HYDRAULIC MODEL IMPLEMENTED — NOT VALIDATED",
                "bbox": self.PILOT_BBOX,
                "feature_count": len(self.pilot_features),
                "assumed_parameters": {
                    "width_m": 0.60,
                    "height_m": 0.75,
                    "manning_n": 0.015,
                    "provenance": "ASSUMED_DESIGN_STANDARD"
                },
                "slope_methodology": "DERIVED_FROM_DEM"
            }
        }
