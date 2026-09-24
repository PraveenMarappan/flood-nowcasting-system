import numpy as np
from collections import deque
from typing import Tuple, Dict, Any, Optional

class D8FlowAccumulationService:
    # D8 Direction Offsets (row_change, col_change) for 8 compass directions
    DIRECTIONS = [
        (0, 1),   # 0: East
        (1, 1),   # 1: South-East
        (1, 0),   # 2: South
        (1, -1),  # 3: South-West
        (0, -1),  # 4: West
        (-1, -1), # 5: North-West
        (-1, 0),  # 6: North
        (-1, 1)   # 7: North-East
    ]
    
    DIST_MULT = [1.0, 1.41421356, 1.0, 1.41421356, 1.0, 1.41421356, 1.0, 1.41421356]

    @classmethod
    def calculate_flow_direction(cls, dem: np.ndarray, nodata_val: float = -9999.0) -> np.ndarray:
        rows, cols = dem.shape
        flow_dir = np.full((rows, cols), -1, dtype=np.int8)

        for r in range(rows):
            for c in range(cols):
                val = dem[r, c]
                if np.isnan(val) or val == nodata_val:
                    continue

                max_slope = -1.0
                best_dir = -1

                for d_idx, (dr, dc) in enumerate(cls.DIRECTIONS):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        n_val = dem[nr, nc]
                        if not np.isnan(n_val) and n_val != nodata_val:
                            drop = val - n_val
                            if drop > 0:
                                slope = drop / cls.DIST_MULT[d_idx]
                                if slope > max_slope:
                                    max_slope = slope
                                    best_dir = d_idx

                flow_dir[r, c] = best_dir

        return flow_dir

    @classmethod
    def calculate_flow_accumulation(cls, flow_dir: np.ndarray, dem: Optional[np.ndarray] = None, nodata_val: float = -9999.0) -> np.ndarray:
        """
        Topological queue flow accumulation calculation.
        Each valid cell starts with an accumulation of 1 (itself).
        Traverses downstream through the D8 flow direction network.
        """
        rows, cols = flow_dir.shape
        indegree = np.zeros((rows, cols), dtype=np.int32)
        downstream = np.full((rows, cols, 2), -1, dtype=np.int32)

        # 1. Compute downstream targets and indegrees
        for r in range(rows):
            for c in range(cols):
                d_idx = flow_dir[r, c]
                if d_idx >= 0:
                    dr, dc = cls.DIRECTIONS[d_idx]
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        downstream[r, c] = [nr, nc]
                        indegree[nr, nc] += 1

        # 2. Initialize queue with cells having 0 in-degree (headwaters)
        queue = deque()
        for r in range(rows):
            for c in range(cols):
                if indegree[r, c] == 0:
                    queue.append((r, c))

        # Flow accumulation initialized to 1 for all valid cells
        if dem is not None:
            flow_acc = np.where((~np.isnan(dem)) & (dem != nodata_val), 1, 0).astype(np.int32)
        else:
            flow_acc = np.ones((rows, cols), dtype=np.int32)

        # 3. Process topological queue
        while queue:
            r, c = queue.popleft()
            nr, nc = downstream[r, c]
            if nr >= 0 and nc >= 0:
                flow_acc[nr, nc] += flow_acc[r, c]
                indegree[nr, nc] -= 1
                if indegree[nr, nc] == 0:
                    queue.append((nr, nc))

        return flow_acc

    @classmethod
    def calculate_contributing_area(cls, flow_acc: np.ndarray, cell_area_m2: float) -> np.ndarray:
        return flow_acc.astype(np.float64) * cell_area_m2
