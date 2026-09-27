import json
from pathlib import Path
from typing import Dict, Any, List

class DatasetEligibilityEngine:
    """
    Classifies dataset features and observation points into strict eligibility categories.
    
    Categories:
    - CALIBRATION_ELIGIBLE: Used strictly for model parameter calibration (e.g., Chennai_2015 753 occurrence points).
    - VALIDATION_ELIGIBLE: Independent event-attributed observations with verified spatial & temporal provenance.
    - DIAGNOSTIC_ONLY: Useful for spatial diagnostic comparisons but unverified timestamp/event (e.g. 192 UNKNOWN depth points, river stage gauges).
    - INELIGIBLE: Missing spatial/temporal data or corrupted.
    """
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parents[4]
        self.processed_geojson = self.base_dir / "data" / "validation" / "processed" / "chennai_validation_normalized.geojson"

    def classify_observation(self, feature: Dict[str, Any], is_calibration_set: bool = True) -> Dict[str, Any]:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])

        if not coords or len(coords) < 2:
            return {"category": "INELIGIBLE", "reason": "Invalid spatial coordinates"}

        event = props.get("event", "UNKNOWN")
        obs_depth = props.get("observed_depth_cm")
        timestamp = props.get("timestamp_utc")

        if event == "Chennai_2015":
            if is_calibration_set:
                return {
                    "category": "CALIBRATION_ELIGIBLE",
                    "reason": "Chennai_2015 event-attributed spatial occurrence point (calibration training set)",
                    "type": "OCCURRENCE",
                    "depth_available": obs_depth is not None
                }
            else:
                return {
                    "category": "INELIGIBLE",
                    "reason": "Cannot be used as independent validation (used in calibration dataset)",
                    "type": "OCCURRENCE",
                    "depth_available": obs_depth is not None
                }
        elif event == "UNKNOWN":
            return {
                "category": "DIAGNOSTIC_ONLY",
                "reason": "Numerical depth available but unverified event attribution and timestamp",
                "type": "NUMERICAL_DEPTH",
                "depth_available": obs_depth is not None
            }
        elif timestamp is not None and event != "UNKNOWN":
            return {
                "category": "VALIDATION_ELIGIBLE",
                "reason": "Independent event-attributed observation with temporal alignment",
                "type": "NUMERICAL_DEPTH" if obs_depth is not None else "OCCURRENCE",
                "depth_available": obs_depth is not None
            }
        else:
            return {"category": "DIAGNOSTIC_ONLY", "reason": "Unverified temporal alignment"}

    def audit_inventory(self) -> Dict[str, Any]:
        if not self.processed_geojson.exists():
            return {"status": "ERROR", "reason": "Normalized GeoJSON missing"}

        with open(self.processed_geojson, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        counts = {
            "CALIBRATION_ELIGIBLE": 0,
            "VALIDATION_ELIGIBLE": 0,
            "DIAGNOSTIC_ONLY": 0,
            "INELIGIBLE": 0
        }
        details = []

        for feat in features:
            cls = self.classify_observation(feat, is_calibration_set=True)
            cat = cls["category"]
            counts[cat] += 1

        return {
            "status": "COMPLETED",
            "total_features": len(features),
            "counts": counts,
            "calibration_occurrence_records": counts["CALIBRATION_ELIGIBLE"],
            "diagnostic_depth_records": counts["DIAGNOSTIC_ONLY"],
            "independent_validation_records": counts["VALIDATION_ELIGIBLE"]
        }

if __name__ == "__main__":
    engine = DatasetEligibilityEngine()
    print(json.dumps(engine.audit_inventory(), indent=2))
