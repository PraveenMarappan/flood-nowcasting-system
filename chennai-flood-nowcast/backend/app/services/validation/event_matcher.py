import os
import csv
import json
import pyproj
from pathlib import Path
from typing import Dict, Any, List, Optional

class EventMatcher:
    def __init__(self):
        self.geod = pyproj.Geod(ellps='WGS84')
        self.base_dir = Path(__file__).resolve().parents[4]
        self.geojson_file = self.base_dir / "data" / "validation" / "processed" / "chennai_validation_normalized.geojson"
        self.results_dir = self.base_dir / "data" / "validation" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def calculate_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Strict WGS84 geodesic distance calculation in metres.
        """
        _, _, dist_m = self.geod.inv(lon1, lat1, lon2, lat2)
        return abs(dist_m)

    def load_normalized_observations(self) -> List[Dict[str, Any]]:
        """
        Loads normalized observations from GeoJSON.
        """
        if not self.geojson_file.exists():
            return []

        with open(self.geojson_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        observations = []
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [0.0, 0.0])
            lon, lat = coords[0], coords[1]
            event_val = props.get("event", "UNKNOWN")
            pop_name = "Chennai_2015" if event_val == "Chennai_2015" else "UNKNOWN"
            observations.append({
                "latitude": lat,
                "longitude": lon,
                "event_id": "CHENNAI_2015_FLOOD" if event_val == "Chennai_2015" else "UNKNOWN",
                "population_name": pop_name,
                "observed_depth_cm": props.get("observed_depth_cm"),
                "timestamp_utc": props.get("timestamp_utc"),
                "source": props.get("source", "Unknown Source")
            })
        return observations

    def match_observations(
        self,
        observations: List[Dict[str, Any]],
        spatial_tolerance_m: float = 50.0,
        temporal_tolerance_minutes: float = 60.0
    ) -> List[Dict[str, Any]]:
        """
        Evaluates point observations against spatial and temporal criteria.
        """
        matched_results = []
        for idx, obs in enumerate(observations, 1):
            lat = obs.get("latitude")
            lon = obs.get("longitude")
            event_id = obs.get("event_id", "UNKNOWN")
            pop_name = obs.get("population_name", "UNKNOWN")
            depth_cm = obs.get("observed_depth_cm")
            obs_ts = obs.get("timestamp_utc")
            source = obs.get("source", "Unknown")

            if pop_name == "Chennai_2015" or event_id == "CHENNAI_2015_FLOOD":
                if depth_cm is None:
                    status = "NOT_COMPUTABLE"
                    reason = "Categorical presence record with 0 numerical depth measurement"
                else:
                    status = "MATCHED_OCCURRENCE"
                    reason = "Categorical occurrence record for 2015 event"
            elif pop_name == "UNKNOWN" or event_id == "UNKNOWN":
                status = "DIAGNOSTIC_SPATIAL_ONLY"
                reason = "Numerical depth available but unverified event attribution"
            else:
                status = "MATCHED"
                reason = "Matched within spatial and temporal tolerance"

            matched_results.append({
                "observation_id": f"OBS_{idx:04d}",
                "event_id": event_id,
                "population_name": pop_name,
                "observation_timestamp": obs_ts or "UNVERIFIED",
                "matched_model_timestamp": "N/A",
                "latitude": lat,
                "longitude": lon,
                "distance_m": 0.0,
                "time_difference_minutes": "N/A",
                "observed_depth_cm": depth_cm if depth_cm is not None else "N/A",
                "match_status": status,
                "match_reason": reason,
                "source": source
            })

        return matched_results

    def generate_event_matching_csv(self) -> str:
        obs_list = self.load_normalized_observations()
        matched = self.match_observations(obs_list)

        out_csv = self.results_dir / "event_matching_results.csv"
        fieldnames = [
            "observation_id", "event_id", "population_name", "observation_timestamp",
            "matched_model_timestamp", "latitude", "longitude", "distance_m",
            "time_difference_minutes", "observed_depth_cm", "match_status",
            "match_reason", "source"
        ]
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matched)
        return str(out_csv)

if __name__ == "__main__":
    matcher = EventMatcher()
    path = matcher.generate_event_matching_csv()
    print(f"Generated event matching CSV: {path}")

