import json
from pathlib import Path
from typing import Dict, Any

class RainfallRunoffService:
    def __init__(self, config_path: Path = None):
        if config_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            config_path = base_dir / "data" / "model_config" / "runoff_coefficients.json"
        
        self.config_path = config_path
        self.config = self._load_config()
        self.default_c = self.config.get("default_coefficient", 0.85)

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "default_coefficient": 0.85,
            "provenance_status": "ASSUMED",
            "categories": {}
        }

    def get_coefficient_for_category(self, category: str = "BUILT_UP") -> float:
        categories = self.config.get("categories", {})
        if category in categories:
            return float(categories[category].get("runoff_coefficient", self.default_c))
        return self.default_c

    def calculate_excess(self, rainfall_rate_mm_hr: float, timestep_hours: float = 1.0, runoff_coefficient: float = None, category: str = "BUILT_UP") -> Dict[str, Any]:
        """
        Calculates rainfall depth and excess runoff for a given timestep.
        Equation: P_excess (mm) = P (mm) * C
        where P (mm) = rainfall_rate (mm/hr) * timestep_hours (hr)
        """
        if timestep_hours <= 0:
            raise ValueError(f"timestep_hours must be > 0, got {timestep_hours}")
            
        C = runoff_coefficient if runoff_coefficient is not None else self.get_coefficient_for_category(category)
        
        # Rainfall rate (mm/hr) to precipitation depth P (mm) over timestep_hours
        p_depth_mm = max(0.0, rainfall_rate_mm_hr * timestep_hours)
        
        # Rainfall excess (mm)
        p_excess_mm = p_depth_mm * C
        
        # Runoff rate (mm/hr)
        runoff_rate_mm_hr = max(0.0, rainfall_rate_mm_hr * C)
        
        return {
            "rainfall_rate_mm_hr": float(rainfall_rate_mm_hr),
            "timestep_hours": float(timestep_hours),
            "precipitation_depth_mm": round(float(p_depth_mm), 4),
            "runoff_coefficient": round(float(C), 4),
            "excess_rainfall_mm": round(float(p_excess_mm), 4),
            "runoff_rate_mm_hr": round(float(runoff_rate_mm_hr), 4),
            "coefficient_provenance": self.config.get("provenance_status", "ASSUMED"),
            "equation": "P_excess = P * C",
            "units": {
                "rainfall_rate": "mm/hr",
                "precipitation_depth": "mm",
                "runoff_coefficient": "dimensionless",
                "excess_rainfall": "mm"
            }
        }
