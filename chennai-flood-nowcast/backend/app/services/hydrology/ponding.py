import numpy as np
import math
from typing import Dict, Any

class PondingDetectionService:
    @staticmethod
    def calculate_ponding_factor(
        slope: float,
        flow_acc_cells: int,
        min_slope_floor: float = 0.001,
        acc_scale_ref: float = 100.0
    ) -> float:
        """
        Calculates terrain convergence ponding factor based on slope and upstream flow accumulation.
        Low slope + high flow accumulation -> higher ponding factor.
        Formula: factor = 1.0 + (log10(flow_acc_cells + 1) / max(slope, min_slope_floor)) * 0.001
        Bounded to prevent numerical explosion [1.0, 3.5].
        """
        slope_bounded = max(slope, min_slope_floor)
        acc_term = math.log10(max(1, flow_acc_cells))
        
        # Hydrological convergence proxy (ratio of upstream area to local slope gradient)
        convergence = (acc_term / slope_bounded) * 0.002
        
        # Bounded between 1.0 (flat/ridge) and 3.5 (deep valley/lowland depression)
        factor = 1.0 + min(2.5, max(0.0, convergence))
        return round(float(factor), 4)
