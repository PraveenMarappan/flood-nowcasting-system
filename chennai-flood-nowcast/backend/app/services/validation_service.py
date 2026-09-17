class ValidationService:
    def __init__(self):
        self.validation_status = "NOT_VALIDATED"
        self.observed_data_available = False

    def get_validation_metrics(self):
        # 11. VALIDATION
        # Return NOT_VALIDATED explicitly when no observed flood dataset exists.
        return {
            "validation_status": self.validation_status,
            "metrics": {
                "MAE": None,
                "RMSE": None,
                "classification_accuracy": None,
                "precision": None,
                "recall": None
            },
            "message": "Historical validation observed datasets are entirely unavailable. Do not fabricate results."
        }
