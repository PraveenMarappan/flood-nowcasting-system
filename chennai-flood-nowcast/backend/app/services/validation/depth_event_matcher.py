"""
Depth Event Matcher

Pairs spatial numerical depth observations with GRID_HYDROLOGY_V1 predictions.

Key Requirements & Scientific Rules:
1. Spatial Geodesic Distance matching within tolerance (50.0m).
2. Explicitly records distance and matching status.
3. Deterministic 80/20 train/holdout partition split:
   - 153 Calibration records (80%)
   - 39 Spatial Holdout Validation records (20%)
4. Zero data leakage between calibration and holdout partitions.
"""

import math
import logging
from typing import List, Dict, Any, Tuple
from app.services.flood_model_service import FloodModelService

logger = logging.getLogger(__name__)

EARTH_RADIUS_M = 6371000.0

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance in meters between two lat/lon points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c

class DepthEventMatcher:
    def __init__(
        self,
        tolerance_m: float = 50.0,
        model: FloodModelService = None,
        forcing_peak_mm_hr: float = 50.0,
    ):
        self.tolerance_m = tolerance_m
        self.model = model or FloodModelService()
        self.forcing_peak_mm_hr = forcing_peak_mm_hr

    def match_observations(
        self,
        observations: List[Dict[str, Any]],
        model_version: str = "GRID_HYDROLOGY_V1",
        calibrated_params: Dict[str, float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Match each observation coordinate to GRID_HYDROLOGY_V1 predicted depth.
        Records exact spatial distance, matched grid cell, and matching status.
        """
        matched_records = []

        runoff_c = None
        if calibrated_params:
            if "impervious_surface_fraction" in calibrated_params:
                runoff_c = calibrated_params["impervious_surface_fraction"]
            elif "runoff_coefficient" in calibrated_params:
                runoff_c = calibrated_params["runoff_coefficient"]

        for obs in observations:
            lat = obs["latitude"]
            lon = obs["longitude"]
            obs_depth = obs["observed_depth_cm"]

            # Query flood model at observation location
            res = self.model.calculate_spatial_flood(
                lat=lat,
                lng=lon,
                rainfall=self.forcing_peak_mm_hr,
                forecast_offset_minutes=0,
                model_version=model_version,
                runoff_coefficient=runoff_c,
            )

            pred_depth = res.get("water_depth_cm", 0.0)
            cell_lat = res.get("grid_cell_lat", lat)
            cell_lon = res.get("grid_cell_lon", lon)

            # Calculate geodesic distance to cell center
            dist_m = haversine_distance_m(lat, lon, cell_lat, cell_lon)
            matched_within_tolerance = dist_m <= self.tolerance_m

            row = {
                "observation_id": obs["observation_id"],
                "observation_coordinates": {"latitude": lat, "longitude": lon},
                "matched_grid_cell": {"latitude": cell_lat, "longitude": cell_lon},
                "actual_spatial_distance_m": round(dist_m, 2),
                "spatial_distance_m": round(dist_m, 2),
                "matching_within_tolerance": matched_within_tolerance,
                "matching_status": "MATCHED" if matched_within_tolerance else "CELL_ASSIGNED_EXCEEDS_TOLERANCE",
                "observed_depth_cm": obs_depth,
                "predicted_depth_cm": pred_depth,
                "residual_cm": round(pred_depth - obs_depth, 2),
                "remarks": obs.get("remarks", ""),
            }
            matched_records.append(row)

        return matched_records

    @staticmethod
    def partition_calibration_holdout(
        records: List[Dict[str, Any]],
        holdout_count: int = 39,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Deterministically split records into exactly 153 Calibration records (80%)
        and 39 Spatial Holdout Validation records (20%).
        Uses strided index selection for uniform spatial coverage.
        """
        n = len(records)
        if n == 0:
            return [], []
        
        if n < holdout_count:
            return records, []

        # Select exactly holdout_count indices evenly spaced across the dataset
        holdout_indices = set(int(round(i * (n - 1) / (holdout_count - 1))) for i in range(holdout_count))

        calibration_set = []
        holdout_set = []

        for idx, rec in enumerate(records):
            if idx in holdout_indices:
                holdout_set.append(rec)
            else:
                calibration_set.append(rec)

        return calibration_set, holdout_set
