import math
import numpy as np
from typing import List, Dict, Any, Optional

class CalibrationService:
    def __init__(self):
        self.calibration_status = "NOT_CALIBRATED"
        self.provenance_status = "FRAMEWORK_READY_UNCALIBRATED"

    @staticmethod
    def calculate_metrics(observed_depths: List[float], predicted_depths: List[float]) -> Dict[str, Any]:
        """
        Calculates hydrological performance metrics between observed and predicted water depths.
        """
        if not observed_depths or not predicted_depths or len(observed_depths) != len(predicted_depths):
            return {
                "mae": None,
                "rmse": None,
                "bias": None,
                "median_absolute_error": None,
                "n_samples": 0,
                "status": "INSUFFICIENT_DATA"
            }

        obs = np.array(observed_depths, dtype=np.float64)
        pred = np.array(predicted_depths, dtype=np.float64)
        errors = pred - obs
        abs_errors = np.abs(errors)

        mae = float(np.mean(abs_errors))
        rmse = float(math.sqrt(np.mean(errors ** 2)))
        bias = float(np.mean(errors))
        med_ae = float(np.median(abs_errors))

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "bias": round(bias, 4),
            "median_absolute_error": round(med_ae, 4),
            "n_samples": len(observed_depths),
            "status": "COMPUTED"
        }

    def evaluate_parameter_set(
        self,
        parameters: Dict[str, float],
        observed_events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate parameter set against observed historical flood data.
        Does NOT alter production defaults unless explicit optimization is requested.
        """
        if not observed_events:
            return {
                "calibration_status": self.calibration_status,
                "provenance": self.provenance_status,
                "metrics": None,
                "message": "No event-matched observations available for calibration. Status remains NOT_CALIBRATED."
            }

        # Calibration loop skeleton
        obs_list = []
        pred_list = []
        for event in observed_events:
            obs = event.get("observed_depth_cm")
            pred = event.get("predicted_depth_cm")
            if obs is not None and pred is not None:
                obs_list.append(float(obs))
                pred_list.append(float(pred))

        metrics = self.calculate_metrics(obs_list, pred_list)
        
        return {
            "calibration_status": self.calibration_status,
            "provenance": self.provenance_status,
            "parameters_evaluated": parameters,
            "metrics": metrics
        }
