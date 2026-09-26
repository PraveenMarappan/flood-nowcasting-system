import json
from pathlib import Path
from typing import Dict, Any

class ValidationStatusEvaluator:
    """
    Evaluates backend evidence to return dynamic machine-readable validation status.
    NEVER allows frontend text or static strings to manually claim VALIDATED.
    """
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parents[4]
        self.results_dir = self.base_dir / "data" / "validation" / "results"

    def evaluate_status(self) -> Dict[str, Any]:
        metrics_file = self.results_dir / "independent_validation_metrics.json"
        calib_file = self.results_dir / "calibration_results.json"

        event_matched_depth_samples = 0
        calibration_complete = False
        independent_validation_complete = False
        validation_gate_passed = False

        if metrics_file.exists():
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    gates = data.get("gates", {})
                    event_matched_depth_samples = gates.get("event_matched_depth_observations_gate", {}).get("sample_count", 0)
                    independent_validation_complete = gates.get("independent_validation_gate", {}).get("passed", False)
            except Exception:
                pass

        if calib_file.exists():
            try:
                with open(calib_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    calibration_complete = data.get("calibration_gate_passed", False)
            except Exception:
                pass

        # Dynamic Status Logic Rule
        if event_matched_depth_samples == 0:
            status = "IMPLEMENTED — NOT VALIDATED"
            scientific_classification = "COMPLETE BUT NOT VALIDATED"
            blocker = "Zero sub-daily numerical flood depth observations attributed to 2015 event"
        elif not calibration_complete:
            status = "CALIBRATED — PENDING INDEPENDENT VALIDATION"
            scientific_classification = "CALIBRATION PENDING"
            blocker = "Hydrological parameters uncalibrated against independent events"
        elif not independent_validation_complete or not validation_gate_passed:
            status = "VALIDATION BLOCKED — INSUFFICIENT OBSERVATIONS"
            scientific_classification = "VALIDATION GATE FAILED"
            blocker = "Independent validation gate evaluation failed"
        else:
            status = "VALIDATED"
            scientific_classification = "VALIDATED"
            blocker = None

        return {
            "status": status,
            "scientific_classification": scientific_classification,
            "event_matched_depth_samples": event_matched_depth_samples,
            "calibration_complete": calibration_complete,
            "independent_validation_complete": independent_validation_complete,
            "validation_gate_passed": validation_gate_passed,
            "validation_blocker": blocker
        }

if __name__ == "__main__":
    evaluator = ValidationStatusEvaluator()
    res = evaluator.evaluate_status()
    print("Dynamic Status Evaluation Result:", json.dumps(res, indent=2))
