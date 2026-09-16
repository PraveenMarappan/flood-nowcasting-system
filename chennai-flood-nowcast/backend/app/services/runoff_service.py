class RunoffEstimationService:
    def __init__(self):
        # Default configurable runoff coefficient.
        self.runoff_coefficient = 0.8
        
    def estimate_runoff(self, rainfall_mm: float) -> float:
        """
        A simple configurable wrapper reflecting runoff generation logically.
        Runoff = rainfall * coefficient
        """
        return rainfall_mm * self.runoff_coefficient
