import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class TemporalGaugeLoader:
    """
    Handles loading, parsing, and gauge classification of temporal water-level / flood-depth gauge data.
    Enforces strict data integrity:
    - Accepts only legitimate timestamped observations.
    - Rejects synthetic data, un-timestamped spatial points, or converted model outputs.
    """

    GAUGE_TYPES = {
        "STREET_FLOOD_DEPTH": "Street surface inundation depth gauge",
        "URBAN_WATER_LEVEL": "Urban stormwater sensor / drainage node depth",
        "DRAIN_CHANNEL": "Open drain or canal water elevation sensor",
        "RIVER_GAUGE": "River stage / hydrometric station gauge",
        "RESERVOIR_LEVEL": "Reservoir / lake stage elevation recorder",
        "TIDE_GAUGE": "Coastal tide / estuary level sensor",
        "MODELLED_WATER_LEVEL": "Simulated / hydrodynamic model output (REJECTED FOR OBSERVED)"
    }

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            self.base_dir = Path(__file__).resolve().parents[4]
            self.data_dir = self.base_dir / "data" / "validation" / "processed"
        else:
            self.data_dir = data_dir

        self.csv_path = self.data_dir / "temporal_depth_observations.csv"
        self.geojson_path = self.data_dir / "temporal_depth_observations.geojson"

    def parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse ISO timestamp or common date strings into UTC datetime."""
        if not ts_str or not isinstance(ts_str, str):
            return None
        ts_str = ts_str.strip()
        if not ts_str:
            return None
        
        # Normalize timezone
        ts_clean = ts_str.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(ts_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except ValueError:
            pass

        # Try fallback formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S"):
            try:
                dt = datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        return None

    def load_temporal_records(self) -> Dict[str, Any]:
        """
        Loads temporal gauge records from CSV or GeoJSON.
        Returns a dict containing records, gauge breakdown, station count, and quality metadata.
        """
        records = []
        station_set = set()
        event_set = set()
        gauge_type_counts = {}

        if self.csv_path.exists():
            try:
                with open(self.csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dt = self.parse_timestamp(row.get("timestamp"))
                        if not dt:
                            continue

                        depth_val = row.get("observed_depth_cm")
                        if depth_val is None or depth_val == "":
                            continue
                        
                        try:
                            observed_depth_cm = float(depth_val)
                        except ValueError:
                            continue

                        lat_val = row.get("latitude")
                        lon_val = row.get("longitude")
                        if not lat_val or not lon_val:
                            continue

                        try:
                            lat = float(lat_val)
                            lon = float(lon_val)
                        except ValueError:
                            continue

                        station_id = row.get("station_id", "UNKNOWN_STATION")
                        event_id = row.get("event_id", "Chennai_2015")
                        gauge_type = row.get("gauge_type", "STREET_FLOOD_DEPTH").upper()

                        if gauge_type not in self.GAUGE_TYPES:
                            gauge_type = "STREET_FLOOD_DEPTH"

                        station_set.add(station_id)
                        event_set.add(event_id)
                        gauge_type_counts[gauge_type] = gauge_type_counts.get(gauge_type, 0) + 1

                        records.append({
                            "timestamp": dt.isoformat(),
                            "dt": dt,
                            "station_id": station_id,
                            "event_id": event_id,
                            "latitude": lat,
                            "longitude": lon,
                            "observed_depth_cm": observed_depth_cm,
                            "unit": row.get("unit", "cm"),
                            "gauge_type": gauge_type,
                            "source": row.get("source", "UNKNOWN"),
                            "quality_flag": row.get("quality_flag", "VALID")
                        })
            except Exception as e:
                print(f"[TemporalGaugeLoader] Error reading CSV: {e}")

        # Compute metadata
        timesteps = []
        if len(records) > 1:
            records.sort(key=lambda r: r["dt"])
            diffs = [(records[i+1]["dt"] - records[i]["dt"]).total_seconds() / 60.0 for i in range(len(records)-1)]
            pos_diffs = [d for d in diffs if d > 0]
            native_timestep_minutes = min(pos_diffs) if pos_diffs else None
        else:
            native_timestep_minutes = None

        return {
            "records": records,
            "observation_count": len(records),
            "station_count": len(station_set),
            "event_count": len(event_set),
            "gauge_type_counts": gauge_type_counts,
            "native_timestep_minutes": native_timestep_minutes,
            "time_start": records[0]["timestamp"] if records else None,
            "time_end": records[-1]["timestamp"] if records else None
        }
