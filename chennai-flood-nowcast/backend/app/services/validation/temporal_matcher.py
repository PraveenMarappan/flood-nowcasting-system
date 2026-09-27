import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class TemporalMatcher:
    """
    Matches sub-daily timestamped gauge observations with GRID_HYDROLOGY_V1 model replay predicted depths.
    Ensures strict temporal matching without timestamp shifting or data leakage.
    """

    MATCHING_TOLERANCE_MINUTES = 30.0

    @staticmethod
    def calculate_haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    def match_observations_to_replay(
        self,
        observations: List[Dict[str, Any]],
        replay_timeseries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Pairs each temporal observation with the closest timestamp in the model replay.
        """
        matched_pairs = []

        if not observations or not replay_timeseries:
            return matched_pairs

        # Convert replay timestamps to dt
        replay_lookup = []
        for item in replay_timeseries:
            ts_str = item.get("timestamp_utc") or item.get("timestamp")
            if not ts_str:
                continue
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                replay_lookup.append({
                    "dt": dt,
                    "model_depth_cm": float(item.get("model_depth_cm", 0.0)),
                    "rainfall_mm_hr": float(item.get("rainfall_mm_hr", 0.0))
                })
            except (ValueError, TypeError):
                continue

        if not replay_lookup:
            return matched_pairs

        for obs in observations:
            obs_dt = obs.get("dt")
            if not obs_dt:
                continue

            # Find closest replay timestep
            best_replay = min(
                replay_lookup,
                key=lambda r: abs((r["dt"] - obs_dt).total_seconds())
            )

            diff_minutes = abs((best_replay["dt"] - obs_dt).total_seconds()) / 60.0

            if diff_minutes <= self.MATCHING_TOLERANCE_MINUTES:
                matched_pairs.append({
                    "timestamp_obs": obs["dt"].isoformat(),
                    "timestamp_model": best_replay["dt"].isoformat(),
                    "station_id": obs.get("station_id", "UNKNOWN"),
                    "latitude": obs.get("latitude"),
                    "longitude": obs.get("longitude"),
                    "observed_depth_cm": obs.get("observed_depth_cm"),
                    "predicted_depth_cm": best_replay["model_depth_cm"],
                    "rainfall_mm_hr": best_replay["rainfall_mm_hr"],
                    "time_difference_minutes": round(diff_minutes, 2),
                    "gauge_type": obs.get("gauge_type", "STREET_FLOOD_DEPTH"),
                    "source": obs.get("source", "UNKNOWN")
                })

        return matched_pairs
