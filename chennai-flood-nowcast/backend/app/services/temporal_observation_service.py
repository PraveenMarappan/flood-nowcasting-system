import csv
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class TemporalObservationService:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.data_file = self.base_dir / "data" / "validation" / "temporal" / "chembarambakkam_2015_temporal.csv"
        
        self.dataset_id = "Chembarambakkam_2015_CAG_WRD"
        self.source_agency = "CAG / WRD"
        self.source_type = "GOVERNMENT_REPORT"
        self.event = "Chennai_2015"
        self.location = "Chembarambakkam_Tank"
        self.report_title = "Performance Audit of Flood management and response in Chennai and its suburban areas"
        
        self.observations: List[Dict[str, Any]] = []
        self._load_observations()

    def _load_observations(self):
        if not self.data_file.exists():
            logging.error(f"Temporal dataset file not found: {self.data_file}")
            return

        seen_timestamps = set()
        loaded = []

        with open(self.data_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_str = row.get("timestamp", "").strip()
                if not ts_str:
                    continue

                if ts_str in seen_timestamps:
                    raise ValueError(f"Duplicate timestamp detected in verified dataset: {ts_str}")
                seen_timestamps.add(ts_str)

                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    wl = float(row["water_level_ft"])
                    inflow = float(row["inflow_cusec"])
                    outflow = float(row["outflow_cusec"])

                    loaded.append({
                        "timestamp": ts_str,
                        "datetime": dt,
                        "water_level_ft": round(wl, 2),
                        "inflow_cusec": round(inflow, 1),
                        "outflow_cusec": round(outflow, 1),
                        "source": row.get("source", self.source_agency),
                        "source_type": row.get("source_type", self.source_type),
                        "event": row.get("event", self.event),
                        "location": row.get("location", self.location),
                        "synthetic": False,
                        "observational": True
                    })
                except Exception as e:
                    logging.error(f"Failed to parse temporal row: {row}, error: {e}")

        # Ensure strict timestamp chronological sorting
        loaded.sort(key=lambda x: x["datetime"])
        self.observations = loaded

    def get_reservoir_statistics(self) -> Dict[str, Any]:
        if not self.observations:
            return {"status": "NO_DATA"}

        water_levels = [o["water_level_ft"] for o in self.observations]
        inflows = [o["inflow_cusec"] for o in self.observations]
        outflows = [o["outflow_cusec"] for o in self.observations]

        max_wl = max(water_levels)
        min_wl = min(water_levels)
        peak_ts = [o["timestamp"] for o in self.observations if o["water_level_ft"] == max_wl]

        first_ts = self.observations[0]["datetime"]
        peak_first_dt = self.observations[water_levels.index(max_wl)]["datetime"]
        time_to_peak_hours = round((peak_first_dt - first_ts).total_seconds() / 3600.0, 2)

        return {
            "status": "CALCULATED",
            "observation_count": len(self.observations),
            "start_time": self.observations[0]["timestamp"],
            "end_time": self.observations[-1]["timestamp"],
            "observed_peak_water_level_ft": max_wl,
            "observed_peak_timestamps": peak_ts,
            "minimum_water_level_ft": min_wl,
            "water_level_rise_ft": round(max_wl - min_wl, 2),
            "water_level_recession_ft": round(max_wl - water_levels[-1], 2),
            "maximum_inflow_cusec": max(inflows),
            "maximum_outflow_cusec": max(outflows),
            "time_to_peak_hours": time_to_peak_hours
        }

    def get_temporal_audit_summary(self) -> Dict[str, Any]:
        stats = self.get_reservoir_statistics()

        return {
            "status": "PARTIALLY_VALIDATED",
            "temporal_hydrological_observations": "AVAILABLE",
            "urban_flood_depth_temporal_validation": "NOT_VALIDATED",
            "adyar_river_gauge_validation": "NOT_VALIDATED",
            "street_flood_depth_validation": "NOT_VALIDATED",
            "reservoir_temporal_validation": "VALIDATED_DATASET_AVAILABLE",
            "dataset_id": self.dataset_id,
            "dataset_name": "Chembarambakkam Tank 2015 Hydrological Series",
            "source_agency": self.source_agency,
            "source_type": self.source_type,
            "reference_report": self.report_title,
            "location": self.location,
            "event": self.event,
            "primary_variable": "reservoir_water_level",
            "primary_units": "feet",
            "secondary_variables": ["inflow_cusec", "outflow_cusec"],
            "temporal_resolution": "2–4 hours",
            "observation_count": len(self.observations),
            "observational": True,
            "synthetic": False,
            "direct_model_comparison": False,
            "reservoir_statistics": stats,
            "provenance_classifications": {
                "TEMPORAL_HYDROLOGICAL_VALIDATION": "AVAILABLE",
                "TEMPORAL_URBAN_FLOOD_DEPTH_GAUGE_VALIDATION": "NOT_VALIDATED",
                "TEMPORAL_ADYAR_RIVER_GAUGE_VALIDATION": "NOT_VALIDATED",
                "TEMPORAL_STREET_FLOOD_DEPTH_VALIDATION": "NOT_VALIDATED",
                "CHEMBARAMBAKKAM_RESERVOIR_VALIDATION": "VALIDATED_DATASET_AVAILABLE"
            },
            "reason": "Verified timestamped reservoir observations exist (CAG / WRD Report), but they are not direct urban flood-depth gauge observations. Reservoir water levels cannot be directly scored against urban street flood depth."
        }

    def get_observations(self) -> List[Dict[str, Any]]:
        # Return cleaned serializable observation list
        return [
            {
                "timestamp": o["timestamp"],
                "water_level_ft": o["water_level_ft"],
                "inflow_cusec": o["inflow_cusec"],
                "outflow_cusec": o["outflow_cusec"],
                "source": o["source"],
                "source_type": o["source_type"]
            }
            for o in self.observations
        ]
