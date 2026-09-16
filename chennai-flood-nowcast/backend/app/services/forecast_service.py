class ForecastService:
    def __init__(self):
        self.model_version = "baseline-v1"
        self.calibration_status = "NOT_CALIBRATED"

    def generate_forecast(self, current_water_depth: float, current_rainfall: float, current_status: str, drainage_eval: dict):
        base_depth = current_water_depth
        status = current_status
        rain = current_rainfall
        
        return {
            "model_version": self.model_version,
            "calibration_status": self.calibration_status,
            "status": "MODELLED",
            "source": "BASELINE HEURISTIC PROJECTION",
            "forecast": [
                {"time": "+30m", "status": status, "depth": base_depth * 0.9 if rain == 0 else base_depth + (rain*0.1), "drainage_influence": drainage_eval["numerical_influence"]},
                {"time": "+60m", "status": status, "depth": base_depth * 0.7 if rain == 0 else base_depth + (rain*0.2), "drainage_influence": drainage_eval["numerical_influence"]},
                {"time": "+90m", "status": "LOW" if rain == 0 else status, "depth": base_depth * 0.5 if rain == 0 else max(base_depth, 10), "drainage_influence": drainage_eval["numerical_influence"]},
                {"time": "+120m", "status": "LOW" if rain == 0 else status, "depth": max(0, base_depth*0.2) if rain == 0 else max(base_depth, 10), "drainage_influence": drainage_eval["numerical_influence"]},
                {"time": "+150m", "status": "NORMAL" if rain == 0 else status, "depth": base_depth * 0.1 if rain == 0 else max(base_depth, 10), "drainage_influence": drainage_eval["numerical_influence"]},
                {"time": "+180m", "status": "NORMAL" if rain == 0 else status, "depth": base_depth * 0.05 if rain == 0 else max(base_depth, 10), "drainage_influence": drainage_eval["numerical_influence"]}
            ]
        }
