from typing import Dict, Any

class DrainageRunoffCalculator:
    """
    Computes peak surface runoff inflow rate (Q_in) into drainage inlets.
    Formula (Rational Method):
    Q_in = (C * I * A) / Unit_Conversion

    SI Units:
    - C: Runoff coefficient (dimensionless, 0.0 to 1.0)
    - I: Rainfall intensity (mm/hr)
    - A_m2: Catchment tributary area (m²)
    - Q_in: Peak runoff inflow discharge (m³/s)

    Unit Conversion Logic:
    1 mm/hr = 10^-3 m / 3600 s = 1 / 3,600,000 m/s
    Q_in (m³/s) = C * (I / 3,600,000) * A_m2 = (C * I * A_m2) / 3,600,000
    """

    DEFAULT_URBAN_RUNOFF_COEFFICIENT = 0.85  # Standard urban dense concrete / asphalt runoff coefficient

    @classmethod
    def calculate_inflow_m3_s(
        cls,
        rainfall_intensity_mm_hr: float,
        catchment_area_m2: float,
        runoff_coefficient: float = DEFAULT_URBAN_RUNOFF_COEFFICIENT,
        is_measured: bool = False,
        provenance: str = "ASSUMED_URBAN_RUNOFF_COEFFICIENT"
    ) -> Dict[str, Any]:
        """Calculates runoff inflow discharge rate Q_in in m³/s."""
        if rainfall_intensity_mm_hr < 0 or catchment_area_m2 <= 0 or runoff_coefficient <= 0:
            return {
                "inflow_m3_s": 0.0,
                "status": "ZERO_OR_INVALID_INPUT",
                "rainfall_intensity_mm_hr": max(0.0, rainfall_intensity_mm_hr),
                "catchment_area_m2": catchment_area_m2,
                "runoff_coefficient": runoff_coefficient,
                "provenance": provenance,
                "measured": is_measured
            }

        # Conversion: I (mm/hr) * A (m²) * C / 3,600,000 = Q_in (m³/s)
        inflow_q = (runoff_coefficient * rainfall_intensity_mm_hr * catchment_area_m2) / 3600000.0

        return {
            "inflow_m3_s": round(inflow_q, 6),
            "status": "CALCULATED",
            "rainfall_intensity_mm_hr": rainfall_intensity_mm_hr,
            "catchment_area_m2": catchment_area_m2,
            "runoff_coefficient": runoff_coefficient,
            "provenance": provenance,
            "measured": is_measured,
            "unit_conversion": "1 mm/hr * 1 m² = 1/3.6e6 m³/s"
        }
