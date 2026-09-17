import os
import sys
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.transform import from_bounds
import datetime
from pathlib import Path

# D8 encoding mapping: 
# 1=E, 2=SE, 3=S, 4=SW, 5=W, 6=NW, 7=N, 8=NE
# Corresponding row/col offsets
D8_OFFSETS = [
    (0, 1),   # 1 E
    (1, 1),   # 2 SE
    (1, 0),   # 3 S
    (1, -1),  # 4 SW
    (0, -1),  # 5 W
    (-1, -1), # 6 NW
    (-1, 0),  # 7 N
    (-1, 1)   # 8 NE
]

def preprocess():
    base_dir = Path(__file__).resolve().parent.parent.parent
    dem_path = base_dir / "data" / "dem" / "chennai_dem.tif"
    out_dir = base_dir / "data" / "dem" / "derivatives"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not dem_path.exists():
        print(f"Error: Base DEM not found at {dem_path}")
        return

    # Configuration: Pilot AOI limits to prevent massive unoptimized traversal overhead in hackathon
    # Defaults roughly map central Chennai bounds if env vars missing
    min_lat = float(os.getenv("PILOT_MIN_LAT", "13.00"))
    max_lat = float(os.getenv("PILOT_MAX_LAT", "13.10"))
    min_lon = float(os.getenv("PILOT_MIN_LON", "80.18"))
    max_lon = float(os.getenv("PILOT_MAX_LON", "80.30"))

    print(f"Executing Preprocessing Workflow against Pilot AOI bounds: LAT[{min_lat}, {max_lat}] LON[{min_lon}, {max_lon}]")

    with rasterio.open(dem_path) as src:
        # Determine the window corresponding to the AOI
        row_min, col_min = src.index(min_lon, max_lat) # top-left
        row_max, col_max = src.index(max_lon, min_lat) # bottom-right
        
        # Ensure bounds are within raster limits
        row_min = max(0, row_min)
        col_min = max(0, col_min)
        row_max = min(src.height, row_max)
        col_max = min(src.width, col_max)
        
        width = col_max - col_min
        height = row_max - row_min
        
        if width <= 0 or height <= 0:
            print("AOI bounds fall outside the DEM or resulted in zero dimensions.")
            return
            
        print(f"Cropped Raster Dimensions: {width} x {height}")
        window = Window(col_min, row_min, width, height)
        
        elevation = src.read(1, window=window)
        nodata = src.nodata
        
        # Metadata derivation
        transform = src.window_transform(window)
        crs = src.crs

        # Cell size approximation in meters (lat/lon to metric assumption)
        # 1 arc-second is roughly 30 meters at equator
        res_x_deg, res_y_deg = transform[0], -transform[4] 
        cell_area_m2 = (res_x_deg * 111320) * (res_y_deg * 111320) # Naive approximation for prototype metadata
        
    # Process Flow Direction (D8)
    print("Calculating D8 Flow Direction iteratively...")
    rows, cols = elevation.shape
    
    # Init direction array. 0 = sink/flat/unresolvable, 1-8 = direction, 255 = nodata
    flow_dir = np.zeros_like(elevation, dtype=np.uint8)
    
    if nodata is None:
        nodata = -9999
    
    # 1D array flattened topological evaluation arrays
    valid_mask = ~np.isnan(elevation) & (elevation != nodata)
    
    # Naive iterative D8 descent
    for r in range(rows):
        for c in range(cols):
            if not valid_mask[r, c]:
                flow_dir[r, c] = 255 # Nodata
                continue
                
            center_val = elevation[r, c]
            steepest_drop = 0
            best_dir = 0
            
            for d_idx, (dr, dc) in enumerate(D8_OFFSETS, start=1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if valid_mask[nr, nc]:
                        drop = center_val - elevation[nr, nc]
                        # Handling flats/equal-elevations inherently by > check
                        if drop > steepest_drop:
                            steepest_drop = drop
                            best_dir = d_idx
                            
            flow_dir[r, c] = best_dir # Note: Sinks remain 0 as steepest_drop never > 0

    # Flow Accumulation - Topological Queue Sort Algorithm
    print("Calculating Flow Accumulation via topological queue traversal...")
    in_degree = np.zeros_like(elevation, dtype=np.int32)
    
    # 1. Calculate in-degrees
    for r in range(rows):
        for c in range(cols):
            d = flow_dir[r, c]
            if 1 <= d <= 8:
                dr, dc = D8_OFFSETS[d - 1]
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    in_degree[nr, nc] += 1

    # 2. Base accumulation array (every valid cell contributes 1)
    accumulation_cells = np.zeros_like(elevation, dtype=np.int32)
    accumulation_cells[valid_mask] = 1
    
    # 3. Initialize queue with source nodes (in_degree == 0)
    queue = []
    for r in range(rows):
        for c in range(cols):
            if valid_mask[r, c] and in_degree[r, c] == 0:
                queue.append((r, c))
                
    # 4. Topological traversal
    head = 0
    while head < len(queue):
        r, c = queue[head]
        head += 1
        
        d = flow_dir[r, c]
        if 1 <= d <= 8:
            dr, dc = D8_OFFSETS[d - 1]
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and valid_mask[nr, nc]:
                accumulation_cells[nr, nc] += accumulation_cells[r, c]
                in_degree[nr, nc] -= 1
                if in_degree[nr, nc] == 0:
                    queue.append((nr, nc))
                    
    # Format and save GeoTIFFs
    profile = {
        'driver': 'GTiff',
        'dtype': 'uint8',
        'nodata': 255,
        'width': width,
        'height': height,
        'count': 1,
        'crs': crs,
        'transform': transform,
        'compress': 'deflate'
    }

    dir_path = out_dir / "flow_direction.tif"
    with rasterio.open(dir_path, 'w', **profile) as dst:
        dst.write(flow_dir, 1)
        
    profile_acc = profile.copy()
    profile_acc['dtype'] = 'int32'
    profile_acc['nodata'] = -1
    acc_out = np.where(valid_mask, accumulation_cells, -1).astype(np.int32)
    
    acc_path = out_dir / "flow_accumulation.tif"
    with rasterio.open(acc_path, 'w', **profile_acc) as dst:
        dst.write(acc_out, 1)
        
    # Optional optimized cache saving
    np.save(out_dir / "flow_accumulation.npy", acc_out)
    
    # Generate Metadata
    bounds_dict = rasterio.transform.array_bounds(height, width, transform)
    meta = {
        "dem_source": str(dem_path.name),
        "algorithm_version": "v3.0.topological",
        "preprocessing_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "resolution_deg": [res_x_deg, res_y_deg],
        "cell_area_approx_m2": cell_area_m2,
        "aoi_bounds": {
            "left": bounds_dict[0],
            "bottom": bounds_dict[1],
            "right": bounds_dict[2],
            "top": bounds_dict[3]
        },
        "raster_dimensions": [width, height],
        "valid_cell_count": int(np.sum(valid_mask)),
        "elevation_range": [float(np.nanmin(elevation[valid_mask])), float(np.nanmax(elevation[valid_mask]))],
        "max_flow_accumulation_cells": int(np.max(acc_out)),
        "max_flow_accumulation_area_m2": float(np.max(acc_out) * cell_area_m2),
        "status": {
            "flow_direction": "PROCESSED",
            "flow_accumulation": "PROCESSED"
        }
    }
    
    with open(out_dir / "derivatives.json", "w") as f:
        json.dump(meta, f, indent=4)
        
    print("Preprocessing completed successfully.")

if __name__ == "__main__":
    preprocess()
