import numpy as np
import math
from typing import Dict, Any, Tuple

class DEMProcessingService:
    @staticmethod
    def calculate_cell_area_m2(lat_deg: float, res_deg: float = 0.0002777777777777778) -> float:
        """
        Calculates physical grid cell area in square meters using projected geodesic approximation.
        Prevents treating lat/lon degrees directly as meters.
        For Chennai (~13 deg N, SRTM 1-arcsec / 0.000277778 deg):
        1 deg lat ~= 110,574 m
        1 deg lon ~= 111,320 * cos(lat) m
        """
        lat_rad = math.radians(lat_deg)
        dy = 110574.0 * res_deg
        dx = 111320.0 * math.cos(lat_rad) * res_deg
        return max(1.0, dx * dy)

    @staticmethod
    def calculate_slope(dem: np.ndarray, cell_size_m: float = 30.0, nodata_val: float = -9999.0) -> np.ndarray:
        """
        Calculates terrain slope array in m/m using central differences.
        """
        rows, cols = dem.shape
        slope = np.zeros((rows, cols), dtype=np.float32)

        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                if dem[r, c] == nodata_val or np.isnan(dem[r, c]):
                    continue
                
                # 3x3 neighborhood gradient estimation (Sobel / Zevenbergen-Thorne)
                dz_dx = ((dem[r-1, c+1] + 2*dem[r, c+1] + dem[r+1, c+1]) - 
                         (dem[r-1, c-1] + 2*dem[r, c-1] + dem[r+1, c-1])) / (8.0 * cell_size_m)
                
                dz_dy = ((dem[r+1, c-1] + 2*dem[r+1, c] + dem[r+1, c+1]) - 
                         (dem[r-1, c-1] + 2*dem[r-1, c] + dem[r-1, c+1])) / (8.0 * cell_size_m)

                slope[r, c] = math.sqrt(dz_dx**2 + dz_dy**2)

        return slope

    @staticmethod
    def fill_depressions(dem: np.ndarray, nodata_val: float = -9999.0, epsilon: float = 0.01) -> np.ndarray:
        """
        Simple topological depression filling (Planchon & Darboux variant floor).
        Ensures monotonic descent pathways for flow direction routing.
        """
        filled = dem.copy()
        rows, cols = dem.shape

        # Initial high fill for non-boundary cells
        max_val = np.nanmax(dem) + 10.0
        mask = (dem != nodata_val) & (~np.isnan(dem))

        # Iterative depression fill
        changed = True
        iterations = 0
        max_iters = 50

        while changed and iterations < max_iters:
            changed = False
            iterations += 1

            for r in range(1, rows - 1):
                for c in range(1, cols - 1):
                    if not mask[r, c]:
                        continue

                    min_nbr = min(
                        filled[r-1, c], filled[r+1, c],
                        filled[r, c-1], filled[r, c+1]
                    )

                    if filled[r, c] < dem[r, c]:
                        filled[r, c] = dem[r, c]
                        changed = True
                    elif filled[r, c] > min_nbr + epsilon and min_nbr >= dem[r, c]:
                        filled[r, c] = min_nbr + epsilon
                        changed = True

        return filled
