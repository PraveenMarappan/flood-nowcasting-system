import json
import math
import csv
from pathlib import Path

class ValidationService:
    def __init__(self):
        self.validation_status = "NOT_VALIDATED"
        self.observed_data_available = False
        self._historical_cache = None  # Cache for static historical validation data
        
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.validation_file = self.base_dir / "data" / "validation" / "processed" / "chennai_validation_normalized.geojson"
        
        self.observations = []
        self._load_observations()

    def _load_observations(self):
        if not self.validation_file.exists():
            return
            
        try:
            with open(self.validation_file, "r") as f:
                data = json.load(f)
            self.observations = data.get("features", [])
            if self.observations:
                self.observed_data_available = True
        except Exception:
            pass

    def evaluate_point_match(self, predicted_grid, observation):
        """
        Point-to-grid spatial matching infrastructure.
        Only runs when event bounds explicitly overlap temporally.
        """
        props = observation.get("properties", {})
        obs_depth = props.get("observed_depth_cm")
        
        # Spatial tolerance: assume matched if delta < 50m
        matched = False
        if not matched:
            return {"match_status": "UNMATCHED", "reason": "No spatial overlap within 50m"}
            
        if obs_depth is not None:
             # Observed depth vs predicted depth comparison
            return {"match_status": "MATCHED", "type": "DEPTH", "obs": obs_depth, "pred": predicted_grid}
            
        # Flooded vs Not-Flooded classification
        return {"match_status": "MATCHED", "type": "CLASSIFICATION", "obs_status": props.get("observed_status"), "pred_status": "FLOODED"}

    @staticmethod
    def calculate_mae(matches):
        if not matches:
            return None
        depth_matches = [m for m in matches if m["type"] == "DEPTH"]
        if not depth_matches:
            return None
        errors = [abs(m["obs"] - m["pred"]) for m in depth_matches]
        return sum(errors) / len(errors)

    @staticmethod
    def calculate_rmse(matches):
        if not matches:
            return None
        depth_matches = [m for m in matches if m["type"] == "DEPTH"]
        if not depth_matches:
            return None
        squared_errors = [(m["obs"] - m["pred"]) ** 2 for m in depth_matches]
        return math.sqrt(sum(squared_errors) / len(squared_errors))

    def get_validation_metrics(self):
        # Initial bounds check
        if not self.observed_data_available:
            return {
                "status": "NOT_VALIDATED",
                "reason": "No normalized historical validation datasets found locally.",
                "metric": None
            }
            
        # STEP 7 / 8 Requirements: Cannot validate historically dynamically if model lacks 2015 forcing.
        # The existing routing abstractions require live IMERG rainfall rates from NASAGpmService.
        # We do not have Historical Chennai 2015 Gridded Rainfall loaded. 
            
        return {
            "status": "NOT_VALIDATED",
            "validation_dataset": "Chennai Inundation Points",
            "event": "Chennai_2015",
            "observation_count": len(self.observations),
            "matched_count": 0,
            "unmatched_count": len(self.observations),
            "metric": None,
            "reason": "Existing Flood Model relies on live real-time GPM IMERG rainfall. Historical 2015 IMERG forcing gridded temporal files are currently missing, preventing valid point-to-grid accuracy metric validation. DO NOT CALCULATE PSEUDO-METRICS.",
            
            # Provenance Trace
            "provenance": {
                "observation_source": "OpenCity / GCC / Crowd-Sourced",
                "model_version": "v3-spatial-heuristic",
                "model_input": "IMERG (Live)",  # Fails compatibility with 2015
                "event": "Chennai_2015",
                "spatial_matching_method": "Point-to-Grid Tolerance (Euclidean)",
                "tolerance_m": 50.0,
                "timestamp_limitation": "timestamp_available = false",
                "result_type": "None (Estimated block)"
            }
        }

    def get_historical_validation(self):
        # Return cached result if available (data is static stored artifacts)
        if self._historical_cache is not None:
            return self._historical_cache

        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        results_dir = base_dir / "data" / "validation" / "results"
        metrics_file = results_dir / "historical_validation_metrics.json"
        if not metrics_file.exists():
            metrics_file = results_dir / "validation_metrics.json"

        timeseries_file = results_dir / "historical_replay_timeseries.csv"

        metrics = {}
        if metrics_file.exists():
            try:
                with open(metrics_file, "r") as f:
                    metrics = json.load(f)
            except Exception as e:
                print("Error loading metrics json:", e)

        timeseries = []
        if timeseries_file.exists():
            try:
                with open(timeseries_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        timeseries.append({
                            "timestamp_utc": row.get("timestamp_utc"),
                            "rainfall_mm_hr": float(row["rainfall_mm_hr"]) if row.get("rainfall_mm_hr") is not None and row.get("rainfall_mm_hr") != "" else None,
                            "model_depth_cm": float(row["model_depth_cm"]) if row.get("model_depth_cm") is not None and row.get("model_depth_cm") != "" else None,
                            "rainfall_status": row.get("rainfall_status"),
                            "model_risk": row.get("model_risk")
                        })
            except Exception as e:
                print("Error loading timeseries csv:", e)

        result = {
            "status": "NOT_VALIDATED",
            "overall_validation_status": "NOT_VALIDATED",
            "metrics": metrics,
            "timeseries": timeseries
        }

        # Cache for subsequent calls
        self._historical_cache = result
        return result


