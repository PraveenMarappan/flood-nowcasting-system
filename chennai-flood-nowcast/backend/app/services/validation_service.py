class ValidationService:
    def get_validation_status(self):
        return {
            "calibration_status": "NOT_CALIBRATED",
            "validation_status": "NOT_AVAILABLE",
            "metrics": {
                "MAE": "UNAVAILABLE",
                "RMSE": "UNAVAILABLE",
                "precision": "UNAVAILABLE",
                "recall": "UNAVAILABLE",
                "F1": "UNAVAILABLE"
            },
            "source": "Historical validation datasets missing. Synthetic claims omitted."
        }
