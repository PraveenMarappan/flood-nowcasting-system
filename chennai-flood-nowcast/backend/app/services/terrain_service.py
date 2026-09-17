import rasterio
import math
import logging
import json
from pathlib import Path
import numpy as np

# Set up logging gracefully
logging.basicConfig(level=logging.INFO)

class TerrainService:
    def __init__(self):
        # Graceful fallback architecture looking for downloaded USGS file securely
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.dem_file = self.base_dir / "data" / "dem" / "chennai_dem.tif"
        self.derivatives_dir = self.base_dir / "data" / "dem" / "derivatives"
        self.meta_file = self.derivatives_dir / "derivatives.json"
        
        self._status = "ESTIMATED"
        self.rasterio_src = None
        self._dem_cache = None
        self._flow_acc_cache = None
        self.meta = {}
        
        self._ensure_initialized()

    def _ensure_initialized(self):
        if self._status != "REAL" and self.dem_file.exists():
            try:
                # Load strictly in read-only to preserve memory overhead efficiently 
                self.rasterio_src = rasterio.open(self.dem_file, mode='r')
                self._dem_cache = self.rasterio_src.read(1)
                self._status = "REAL"
                logging.info(f"TerrainService: SRTM DEM loaded securely from {self.dem_file.name}")
                
                if self.meta_file.exists():
                    with open(self.meta_file, 'r') as f:
                        self.meta = json.load(f)
                    acc_path = self.derivatives_dir / "flow_accumulation.npy"
                    if acc_path.exists():
                        self._flow_acc_cache = np.load(acc_path)
            except Exception as e:
                logging.error(f"TerrainService: Error initializing DEM locally - {e}")
                self._status = "ESTIMATED"
                
    def get_summary(self) -> dict:
        self._ensure_initialized()
        if self._status != "REAL" or not self.meta:
            return {"status": "UNAVAILABLE", "message": "Preprocessed terrain derivatives missing"}
            
        return dict(self.meta, status="AVAILABLE")
                
    def get_status(self) -> dict:
        self._ensure_initialized() # Check if user manually uploaded file between requests natively
        
        info = {
            "status": self._status,
            "source": "USGS SRTM 1 Arc-Second" if self._status == "REAL" else "Interpolated Fallback Proxy",
            "message": "Real terrain loaded" if self._status == "REAL" else "DEM missing. Running simulated heuristics.",
            "calibration_status": "NOT_CALIBRATED",
            "bounds": None
        }
        
        if self.rasterio_src:
            bounds = self.rasterio_src.bounds
            info["bounds"] = {
                "left": bounds.left,
                "bottom": bounds.bottom,
                "right": bounds.right,
                "top": bounds.top
            }
            
        return info

    def get_elevation(self, latitude: float, longitude: float) -> dict:
        self._ensure_initialized()
        
        if self._status != "REAL" or self.rasterio_src is None:
            return {
                "status": "UNAVAILABLE",
                "source": "DEM simulation",
                "elevation_m": None, # Adhering to UNAVAILABLE rules precisely instead of fabricating 
                "error": "Real DEM not loaded locally."
            }
            
        try:
            row, col = self.rasterio_src.index(longitude, latitude)
            
            if 0 <= row < self._dem_cache.shape[0] and 0 <= col < self._dem_cache.shape[1]:
                val = self._dem_cache[row, col]
                if not math.isnan(val) and val != self.rasterio_src.nodata:
                    return {
                        "status": "REAL",
                        "source": "USGS SRTM 1 Arc-Second DEM",
                        "elevation_m": round(float(val), 2),
                        "row": row,
                        "col": col
                    }
            return {
                "status": "UNAVAILABLE",
                "source": "DEM simulation",
                "elevation_m": None,
                "error": "nodata cell found at this coordinate"
            }
        except IndexError:
             return {
                "status": "UNAVAILABLE",
                "source": "DEM simulation",
                "elevation_m": None,
                "error": "Location outside valid spatial bounds."
            }
        except Exception as e:
             return {
                "status": "UNAVAILABLE",
                "source": "DEM simulation",
                "elevation_m": None,
                "error": str(e)
            }

    def get_derivatives(self, latitude: float, longitude: float) -> dict:
        elevation_data = self.get_elevation(latitude, longitude)
        if elevation_data["status"] != "REAL":
            return {
                "status": "UNAVAILABLE",
                "source": "Terrain Derivatives",
                "error": "Cannot calculate derivatives without REAL elevation.",
                "flow_accumulation_cells": 0,
                "flow_accumulation_area_m2": 0.0,
                "acc_prioritization_factor": 1.0
            }
            
        row = elevation_data["row"]
        col = elevation_data["col"]
        
        flow_acc_cells = 0
        flow_acc_area = 0.0
        
        if self._flow_acc_cache is not None and self.meta:
            bounds = self.meta.get("aoi_bounds", {})
            if bounds:
                try:
                    crop_row_min, crop_col_min = self.rasterio_src.index(bounds["left"], bounds["top"])
                    local_r = row - crop_row_min
                    local_c = col - crop_col_min
                    
                    if 0 <= local_r < self._flow_acc_cache.shape[0] and 0 <= local_c < self._flow_acc_cache.shape[1]:
                        acc_val = self._flow_acc_cache[local_r, local_c]
                        if acc_val > 0:
                            flow_acc_cells = int(acc_val)
                            flow_acc_area = float(acc_val * self.meta.get("cell_area_approx_m2", 900))
                except Exception:
                    pass
                        
        # 5. IMPORTANT SCIENTIFIC CORRECTION: Must not directly treat flow_accumulation as depth
        acc_prioritization_factor = 1.0
        if flow_acc_cells > 0:
            # Bounded factors to prevent extreme numerical values
            acc_prioritization_factor = min(2.5, 1.0 + (math.log10(flow_acc_cells) * 0.2))
            
        return {
            "status": "MODELLED",
            "source": "SRTM DEM Spatial Preprocessed Routing",
            "elevation_m": elevation_data["elevation_m"],
            "flow_accumulation_cells": flow_acc_cells,
            "flow_accumulation_area_m2": flow_acc_area,
            "acc_prioritization_factor": round(acc_prioritization_factor, 3) 
        }
