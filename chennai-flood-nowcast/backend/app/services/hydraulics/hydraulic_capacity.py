import math
from typing import Dict, Any, Optional

class HydraulicCapacityCalculator:
    """
    Computes hydraulic flow capacity using Manning's Equation:
    Q = (1 / n) * A * R^(2/3) * S^(1/2)

    Units (SI):
    - A: Cross-sectional flow area (m²)
    - P: Wetted perimeter (m)
    - R: Hydraulic radius A / P (m)
    - S: Bed slope / hydraulic gradient (m/m, dimensionless)
    - n: Manning roughness coefficient (s / m^(1/3))
    - Q: Hydraulic discharge capacity (m³/s)
    """

    DEFAULT_ASSUMED_WIDTH_M = 0.60
    DEFAULT_ASSUMED_HEIGHT_M = 0.75
    DEFAULT_ASSUMED_MANNING_N = 0.015
    DEFAULT_ASSUMED_SLOPE = 0.001  # 0.1% gradient

    @staticmethod
    def calculate_rectangular_open_capacity(
        width_m: float,
        depth_m: float,
        manning_n: float,
        slope: float,
        is_measured: bool = False,
        provenance: str = "ASSUMED_DESIGN_STANDARD"
    ) -> Dict[str, Any]:
        """Calculates capacity for open rectangular channel section."""
        if width_m <= 0 or depth_m <= 0 or manning_n <= 0 or slope <= 0:
            return {
                "capacity_m3_s": 0.0,
                "status": "INVALID_PARAMETERS",
                "area_m2": 0.0,
                "wetted_perimeter_m": 0.0,
                "hydraulic_radius_m": 0.0,
                "provenance": provenance,
                "measured": is_measured
            }

        area = width_m * depth_m
        perimeter = width_m + 2.0 * depth_m
        radius = area / perimeter
        q_cap = (1.0 / manning_n) * area * (radius ** (2.0 / 3.0)) * math.sqrt(slope)

        return {
            "capacity_m3_s": round(q_cap, 4),
            "status": "CALCULATED",
            "section_type": "RECTANGULAR_OPEN",
            "area_m2": round(area, 4),
            "wetted_perimeter_m": round(perimeter, 4),
            "hydraulic_radius_m": round(radius, 4),
            "width_m": width_m,
            "depth_m": depth_m,
            "manning_n": manning_n,
            "slope": slope,
            "provenance": provenance,
            "measured": is_measured
        }

    @staticmethod
    def calculate_box_culvert_capacity(
        width_m: float,
        height_m: float,
        manning_n: float,
        slope: float,
        is_measured: bool = False,
        provenance: str = "ASSUMED_DESIGN_STANDARD"
    ) -> Dict[str, Any]:
        """Calculates full-flow hydraulic capacity for closed rectangular RC box culvert."""
        if width_m <= 0 or height_m <= 0 or manning_n <= 0 or slope <= 0:
            return {
                "capacity_m3_s": 0.0,
                "status": "INVALID_PARAMETERS",
                "area_m2": 0.0,
                "wetted_perimeter_m": 0.0,
                "hydraulic_radius_m": 0.0,
                "provenance": provenance,
                "measured": is_measured
            }

        area = width_m * height_m
        perimeter = 2.0 * (width_m + height_m)
        radius = area / perimeter
        q_cap = (1.0 / manning_n) * area * (radius ** (2.0 / 3.0)) * math.sqrt(slope)

        return {
            "capacity_m3_s": round(q_cap, 4),
            "status": "CALCULATED",
            "section_type": "RECTANGULAR_BOX_CULVERT",
            "area_m2": round(area, 4),
            "wetted_perimeter_m": round(perimeter, 4),
            "hydraulic_radius_m": round(radius, 4),
            "width_m": width_m,
            "height_m": height_m,
            "manning_n": manning_n,
            "slope": slope,
            "provenance": provenance,
            "measured": is_measured
        }

    @staticmethod
    def calculate_circular_pipe_capacity(
        diameter_m: float,
        manning_n: float,
        slope: float,
        is_measured: bool = False,
        provenance: str = "ASSUMED_DESIGN_STANDARD"
    ) -> Dict[str, Any]:
        """Calculates full-flow capacity for circular pipe conduit."""
        if diameter_m <= 0 or manning_n <= 0 or slope <= 0:
            return {
                "capacity_m3_s": 0.0,
                "status": "INVALID_PARAMETERS",
                "area_m2": 0.0,
                "wetted_perimeter_m": 0.0,
                "hydraulic_radius_m": 0.0,
                "provenance": provenance,
                "measured": is_measured
            }

        area = (math.pi * (diameter_m ** 2)) / 4.0
        perimeter = math.pi * diameter_m
        radius = diameter_m / 4.0
        q_cap = (1.0 / manning_n) * area * (radius ** (2.0 / 3.0)) * math.sqrt(slope)

        return {
            "capacity_m3_s": round(q_cap, 4),
            "status": "CALCULATED",
            "section_type": "CIRCULAR_PIPE",
            "area_m2": round(area, 4),
            "wetted_perimeter_m": round(perimeter, 4),
            "hydraulic_radius_m": round(radius, 4),
            "diameter_m": diameter_m,
            "manning_n": manning_n,
            "slope": slope,
            "provenance": provenance,
            "measured": is_measured
        }

    @classmethod
    def get_default_pilot_parameters(cls) -> Dict[str, Any]:
        """Returns standard assumed engineering parameters for pilot catchment."""
        return {
            "width_m": cls.DEFAULT_ASSUMED_WIDTH_M,
            "height_m": cls.DEFAULT_ASSUMED_HEIGHT_M,
            "manning_n": cls.DEFAULT_ASSUMED_MANNING_N,
            "default_slope": cls.DEFAULT_ASSUMED_SLOPE,
            "provenance": "ASSUMED_DESIGN_STANDARD",
            "measured": False,
            "note": "Standard GCC engineering design guidelines for secondary storm water box drains (0.60m x 0.75m cast concrete). Not measured in field survey."
        }
