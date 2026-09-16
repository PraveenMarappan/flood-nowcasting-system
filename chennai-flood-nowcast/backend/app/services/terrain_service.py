import os
import math
import sys
import traceback
from pathlib import Path

class TerrainService:
    def __init__(self):
        # Locate the expected DEM file in data/dem directory robustly
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "dem"
        self.dem_file = self.base_dir / "chennai_dem.tif"
        self._status = "UNAVAILABLE"
        self._summary = None
        self._rasterio_error = None
        self.rasterio = None
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # We will load on first request to avoid locking into a failed state

    def _ensure_initialized(self):
        # If it's already REAL and we have rasterio, we don't need to try again
        if self._status == "REAL" and self.rasterio is not None:
            return

        # Try to import rasterio if we haven't successfully yet
        if self.rasterio is None:
            try:
                import rasterio
                self.rasterio = rasterio
                self._rasterio_error = None
            except Exception as e:
                self._rasterio_error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                self.rasterio = None

        self._load_raster_metadata()

    def _load_raster_metadata(self):
        if self.rasterio is None:
            self._status = "UNAVAILABLE"
            self._summary = {
                "error": "rasterio_import_error",
                "details": self._rasterio_error,
                "python_executable": sys.executable
            }
            return

        if not self.dem_file.exists():
            self._status = "UNAVAILABLE"
            self._summary = {
                "error": "DEM file not found",
                "path": str(self.dem_file),
                "python_executable": sys.executable,
                "rasterio_version": getattr(self.rasterio, "__version__", "unknown")
            }
            return

        if not os.access(self.dem_file, os.R_OK):
            self._status = "UNAVAILABLE"
            self._summary = {
                "error": "DEM file not readable (permission denied)",
                "path": str(self.dem_file)
            }
            return

        try:
            with self.rasterio.open(self.dem_file) as src:
                self._status = "REAL"
                
                res_x, res_y = src.res
                bounds = src.bounds
                
                if src.count < 1:
                    raise ValueError("No raster bands found in the DEM.")
                
                self._summary = {
                    "source": "SRTM DEM",
                    "status": "REAL",
                    "file": str(self.dem_file.relative_to(self.base_dir.parent.parent)),
                    "resolution": [res_x, res_y],
                    "crs": src.crs.to_string() if src.crs else "Unknown",
                    "width": src.width,
                    "height": src.height,
                    "bounds": {
                        "left": bounds.left,
                        "bottom": bounds.bottom,
                        "right": bounds.right,
                        "top": bounds.top
                    },
                    "nodata": src.nodata,
                    "python_executable": sys.executable,
                    "rasterio_version": getattr(self.rasterio, "__version__", "unknown")
                }
        except Exception as e:
            self._status = "UNAVAILABLE"
            self._summary = {
                "error": "failed_to_load_dem",
                "message": str(e),
                "path": str(self.dem_file),
                "python_executable": sys.executable,
                "rasterio_version": getattr(self.rasterio, "__version__", "unknown") if self.rasterio else "unknown"
            }

    def get_status(self):
        self._ensure_initialized()
        return {
            "status": self._status,
            "source": self._summary.get("source", "SRTM DEM") if self._summary else "SRTM DEM",
            "details": self._summary
        }

    def get_elevation(self, latitude: float, longitude: float) -> dict:
        self._ensure_initialized()
        
        if self._status != "REAL" or self.rasterio is None:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": None,
                "source": "SRTM DEM",
                "status": "UNAVAILABLE",
                "error": self._summary.get("error", "Real DEM not installed or loaded properly.") if self._summary else "Real DEM not installed or loaded properly.",
                "details": self._summary
            }

        try:
            with self.rasterio.open(self.dem_file) as src:
                bounds = src.bounds
                if not (bounds.left <= longitude <= bounds.right and bounds.bottom <= latitude <= bounds.top):
                    return {
                        "latitude": latitude,
                        "longitude": longitude,
                        "elevation_m": None,
                        "source": "SRTM DEM",
                        "status": "UNAVAILABLE",
                        "error": "location_outside_dem"
                    }
                
                # Transform coordinates to raster index
                row, col = src.index(longitude, latitude)
                
                if row < 0 or col < 0 or row >= src.height or col >= src.width:
                    return {
                        "latitude": latitude,
                        "longitude": longitude,
                        "elevation_m": None,
                        "source": "SRTM DEM",
                        "status": "UNAVAILABLE",
                        "error": "location_outside_dem_array"
                    }
                
                # Read specific pixel using a 1x1 window
                window = self.rasterio.windows.Window(col, row, 1, 1)
                data = src.read(1, window=window)
                
                if data.size == 0:
                    raise ValueError("Empty data array returned from raster read.")
                    
                actual_elevation = float(data[0, 0])
                
                if math.isnan(actual_elevation) or (src.nodata is not None and math.isclose(actual_elevation, src.nodata)):
                    return {
                        "latitude": latitude,
                        "longitude": longitude,
                        "elevation_m": None,
                        "source": "SRTM DEM",
                        "status": "UNAVAILABLE",
                        "error": "nodata_cell"
                    }
                    
                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "elevation_m": round(actual_elevation, 2),
                    "source": "SRTM DEM",
                    "status": "REAL"
                }

        except Exception as e:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": None,
                "source": "SRTM DEM",
                "status": "UNAVAILABLE",
                "error": str(e)
            }
