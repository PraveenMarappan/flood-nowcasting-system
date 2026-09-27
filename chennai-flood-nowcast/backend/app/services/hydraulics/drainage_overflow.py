from typing import Dict, Any

class DrainageOverflowEvaluator:
    """
    Evaluates hydraulic surcharge ratio and overflow discharge rate.

    Safety & Scientific Rules:
    - Never reduces surface flood depth based on drain proximity.
    - Surcharge ratio > 1.0 indicates ASSUMED CAPACITY EXCEEDED (Modelled Diagnostic).
    - Drainage effect on surface flood depth remains NOT_COMPUTABLE (0.0 cm depth reduction).
    """

    @staticmethod
    def evaluate_overflow(
        inflow_q_m3_s: float,
        capacity_q_m3_s: float
    ) -> Dict[str, Any]:
        """Evaluates hydraulic surcharge ratio and overflow discharge."""
        if capacity_q_m3_s <= 0:
            return {
                "surcharge_ratio": 0.0,
                "overflow_rate_m3_s": 0.0,
                "capacity_status": "INDETERMINATE_ZERO_CAPACITY",
                "classification": "MODELLED HYDRAULIC CAPACITY DIAGNOSTIC",
                "drainage_effect_on_flood_depth": 0.0,
                "drainage_effect_status": "NOT_COMPUTABLE"
            }

        surcharge_ratio = inflow_q_m3_s / capacity_q_m3_s
        overflow_rate = max(0.0, inflow_q_m3_s - capacity_q_m3_s)

        capacity_status = "WITHIN_ASSUMED_CAPACITY" if surcharge_ratio <= 1.0 else "ASSUMED_CAPACITY_EXCEEDED"

        return {
            "surcharge_ratio": round(surcharge_ratio, 4),
            "overflow_rate_m3_s": round(overflow_rate, 6),
            "capacity_status": capacity_status,
            "classification": "MODELLED HYDRAULIC CAPACITY DIAGNOSTIC",
            "drainage_effect_on_flood_depth": 0.0,
            "drainage_effect_status": "NOT_COMPUTABLE",
            "safety_disclaimer": "Proximity to drains does not reduce surface flood depth. Overflow is evaluated strictly as a diagnostic hydraulic metric."
        }
