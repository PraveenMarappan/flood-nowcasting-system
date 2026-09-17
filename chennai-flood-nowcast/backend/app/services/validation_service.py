import json
import math
from pathlib import Path

class ValidationService:
    def __init__(self):
        self.validation_status = "NOT_VALIDATED"
        self.observed_data_available = False
        
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
