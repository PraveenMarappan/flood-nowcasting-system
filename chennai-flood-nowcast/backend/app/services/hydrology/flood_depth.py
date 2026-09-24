import math
import json
from pathlib import Path
from typing import Dict, Any, Optional

from app.services.hydrology.rainfall_runoff import RainfallRunoffService
from app.services.hydrology.ponding import PondingDetectionService
from app.services.hydrology.model_provenance import ModelProvenance

class FloodDepthEngine:
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            config_path = base_dir / "data" / "model_config" / "flood_model.json"
            
        self.config_path = config_path
        self.config = self._load_config()
        self.rainfall_runoff_service = RainfallRunoffService()
        self.model_version = "GRID_HYDROLOGY_V1"
        self.estimator_label = "GRID-BASED HYDROLOGICAL FLOOD-DEPTH ESTIMATE"

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "parameters": {
                "recession_half_life_hours": {"value": 2.0},
                "max_ponding_depth_cm": {"value": 200.0}
            }
        }

    def calculate_recession_multiplier(self, forecast_offset_minutes: int) -> float:
        """
        Calculates exponential physical recession multiplier for surface runoff dissipation.
        Formula: exp(-t / tau), where tau = half_life / ln(2)
        For half_life = 2.0 hrs (120 mins):
        t = 0 min -> 1.0
        t = 30 min -> ~0.841
        t = 60 min -> ~0.707
        t = 120 min -> ~0.500
        t = 180 min -> ~0.354
        """
        if forecast_offset_minutes <= 0:
            return 1.0
            
        half_life_hrs = float(self.config.get("parameters", {}).get("recession_half_life_hours", {}).get("value", 2.0))
        tau_mins = (half_life_hrs * 60.0) / math.log(2)
        
        recession_mult = math.exp(-forecast_offset_minutes / tau_mins)
        return max(0.01, round(float(recession_mult), 4))

    def compute_flood_depth(
        self,
        rainfall_rate_mm_hr: float,
        latitude: float,
        longitude: float,
        elevation_m: Optional[float],
        flow_acc_cells: int = 0,
        slope: float = 0.005,
        forecast_offset_minutes: int = 0,
        timestep_hours: float = 1.0,
        runoff_coefficient: Optional[float] = None,
        is_simulated: bool = False,
        current_water_depth_cm: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Grid-based hydrological flood depth estimation pipeline.
        
        1. Excess Rainfall: P_excess (mm) = P (mm/hr * timestep) * C
        2. Runoff Depth: R (cm) = P_excess (mm) / 10
        3. Terrain Convergence & Ponding: Factor = 1.0 + f(slope, flow_acc)
        4. Spatial Routing Base: Depth_base = R (cm) * Ponding_Factor
        5. Time Stepping & Recovery: Apply exponential recession for forecasts / cessation
        """
        # 1. 0-Rainfall Recovery Check at current time (no forecast offset, no initial depth)
        if rainfall_rate_mm_hr <= 0 and forecast_offset_minutes == 0 and current_water_depth_cm is None:
            prov = ModelProvenance.get_provenance_metadata(self.model_version, is_simulated=is_simulated)
            return {
                "water_depth_cm": 0.0,
                "risk_level": "NORMAL",
                "risk_color": "WHITE",
                "forecast_type": "CURRENT",
                "estimator": self.estimator_label,
                "model_version": self.model_version,
                "units": "cm",
                "provenance": prov
            }

        # 2. Runoff Excess Calculation
        excess_res = self.rainfall_runoff_service.calculate_excess(
            rainfall_rate_mm_hr=rainfall_rate_mm_hr,
            timestep_hours=timestep_hours,
            runoff_coefficient=runoff_coefficient,
            category="BUILT_UP"
        )
        
        p_excess_mm = excess_res["excess_rainfall_mm"]
        c_val = excess_res["runoff_coefficient"]
        runoff_depth_cm = p_excess_mm * 0.1

        # 3. Terrain Convergence & Ponding
        ponding_factor = PondingDetectionService.calculate_ponding_factor(
            slope=slope,
            flow_acc_cells=flow_acc_cells
        )
        
        # 4. Spatially Distributed Base Surface Water Depth
        if current_water_depth_cm is not None:
            base_depth_cm = current_water_depth_cm
        else:
            base_depth_cm = runoff_depth_cm * ponding_factor

        # 5. Time Stepping & Cessation Recovery Logic
        recession_mult = self.calculate_recession_multiplier(forecast_offset_minutes)
        forecast_type = "CURRENT" if forecast_offset_minutes == 0 else f"HYDROLOGICAL RECOVERY PROJECTION (+{forecast_offset_minutes}m)"

        if forecast_offset_minutes > 0:
            if rainfall_rate_mm_hr > 0 and current_water_depth_cm is None:
                # Active forcing projection
                water_depth_cm = base_depth_cm + (base_depth_cm * (1.0 - recession_mult) * 0.5)
            else:
                # Cessation recovery decay
                water_depth_cm = base_depth_cm * recession_mult
        else:
            water_depth_cm = base_depth_cm

        # Max depth safety cap
        max_cap = float(self.config.get("parameters", {}).get("max_ponding_depth_cm", {}).get("value", 200.0))
        water_depth_cm = min(max_cap, max(0.0, water_depth_cm))
        water_depth_rounded = round(float(water_depth_cm), 2)

        # 6. Risk Level Classification
        if water_depth_rounded > 30.0:
            risk_level, risk_color = "HIGH", "RED"
        elif water_depth_rounded > 10.0:
            risk_level, risk_color = "MODERATE", "ORANGE"
        elif water_depth_rounded > 0.1:
            risk_level, risk_color = "LOW", "LIGHT_BLUE"
        else:
            risk_level, risk_color = "NORMAL", "WHITE"

        prov = ModelProvenance.get_provenance_metadata(self.model_version, is_simulated=is_simulated)

        return {
            "status": "MODELLED",
            "model_version": self.model_version,
            "estimator": self.estimator_label,
            "forecast_type": forecast_type,
            "water_depth_cm": water_depth_rounded,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "rainfall_rate_mm_hr": round(float(rainfall_rate_mm_hr), 2),
            "timestep_hours": float(timestep_hours),
            "runoff_coefficient": c_val,
            "excess_rainfall_mm": p_excess_mm,
            "runoff_depth_cm": round(float(runoff_depth_cm), 2),
            "terrain_elevation_m": round(float(elevation_m), 2) if elevation_m is not None else None,
            "flow_accumulation_cells": flow_acc_cells,
            "ponding_factor": ponding_factor,
            "recession_multiplier": recession_mult,
            "drainage_mode": "GEOMETRIC_ONLY",
            "drainage_used": False,
            "provenance": prov
        }
