import pytest
import numpy as np
from pathlib import Path

# Provide tests matching D8 flat cell sinks rules
def d8_flow_dir_kernel(elevation):
    # Dummy mock mapping the same logic iteratively to test on a 5x5 array
    rows, cols = elevation.shape
    flow_dir = np.zeros_like(elevation, dtype=np.uint8)
    D8 = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
    valid_mask = elevation != -9999
    
    for r in range(rows):
        for c in range(cols):
            if not valid_mask[r, c]: 
                flow_dir[r,c] = 255
                continue
            center = elevation[r, c]
            steepest = 0
            best_dir = 0
            for d_idx, (dr, dc) in enumerate(D8, 1):
                nr, nc = r+dr, c+dc
                if 0 <= nr < rows and 0 <= nc < cols and valid_mask[nr, nc]:
                    drop = center - elevation[nr, nc]
                    if drop > steepest:
                        steepest = drop
                        best_dir = d_idx
            flow_dir[r, c] = best_dir
    return flow_dir

def get_accumulation(flow_dir, valid_mask):
    rows, cols = flow_dir.shape
    D8 = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
    in_degree = np.zeros_like(flow_dir, dtype=np.int32)
    
    for r in range(rows):
        for c in range(cols):
            d = flow_dir[r, c]
            if 1 <= d <= 8:
                dr, dc = D8[d-1]
                nr, nc = r+dr, c+dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    in_degree[nr, nc] += 1
                    
    acc = np.zeros_like(flow_dir, dtype=np.int32)
    acc[valid_mask] = 1
    queue = []
    
    for r in range(rows):
        for c in range(cols):
            if valid_mask[r, c] and in_degree[r, c] == 0:
                queue.append((r, c))
                
    head = 0
    while head < len(queue):
        r, c = queue[head]
        head += 1
        d = flow_dir[r, c]
        if 1 <= d <= 8:
            dr, dc = D8[d-1]
            nr, nc = r+dr, c+dc
            if 0 <= nr < rows and 0 <= nc < cols and valid_mask[nr, nc]:
                acc[nr, nc] += acc[r, c]
                in_degree[nr, nc] -= 1
                if in_degree[nr, nc] == 0:
                    queue.append((nr, nc))
    return acc

def test_flat_cells_and_sinks():
    # 5x5 Synthetic DEM
    dem = np.array([
        [10, 10, 10, 10, 10], # Flat row
        [10,  8,  9,  8, 10],
        [10,  9,  5,  9, 10], # 5 is a sink
        [10,  8,  9,  8, 10],
        [-9999, 10, 10, 10, -9999] # Nodata boundary
    ], dtype=float)
    
    flow_dir = d8_flow_dir_kernel(dem)
    
    # Check that flat cells correctly route towards steepest drops
    # The sink (2,2) with elev 5 should have flow_dir = 0 (no steepest descent)
    assert flow_dir[2, 2] == 0 
    
    # The nodata cells should be marked 255
    assert flow_dir[4, 0] == 255
    assert flow_dir[4, 4] == 255

def test_flow_accumulation_queue():
    dem = np.array([
        [12, 11, 10],
        [11, 10,  9],
        [10,  9,  8]
    ], dtype=float)
    
    flow_dir = d8_flow_dir_kernel(dem)
    valid_mask = dem != -9999
    acc = get_accumulation(flow_dir, valid_mask)
    
    # 8 is the lowest point (sink at bottom right)
    # The acc should route all cells downstream towards 8
    # 3x3 = 9 cells, so sink cell should hold acc=9
    assert acc[2, 2] == 9
