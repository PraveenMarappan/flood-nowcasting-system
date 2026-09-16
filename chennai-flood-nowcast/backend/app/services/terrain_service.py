import os
import math
from pathlib import Path

# Provide a safe fallback if rasterio isn't fully installed or throws error
try:
    import rasterio
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

class TerrainService:
    def __init__(self):
        # Locate the expected DEM file in data/dem directory
        self.base_dir = Path(__file__).parent.parent.parent.parent / "data" / "dem"
        self.dem_file = self.base_dir / "chennai_dem.tif"
        self.dataset = None
        self._status = "UNAVAILABLE"
        self._summary = None
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._load_raster_metadata()

    def _load_raster_metadata(self):
        if not RASTERIO_AVAILABLE:
            self._status = "UNAVAILABLE"
            self._summary = {"error": "rasterio library not installed"}
            return

        if not self.dem_file.exists():
            self._status = "UNAVAILABLE"
            self._summary = {"error": "DEM file chennai_dem.tif not found in data/dem"}
            return

        try:
            # We open the dataset once lightly to pull metadata.
            # rasterio handles metadata efficiently without pulling all data into RAM.
            with rasterio.open(self.dem_file) as src:
                self._status = "REAL"
                
                # Fetch resolution. In WGS84 degrees, ~0.000277 deg is ~30m.
                res_x, res_y = src.res
                bounds = src.bounds
                self._summary = {
                    "source": "SRTM DEM",
                    "status": "REAL",
                    "file": str(self.dem_file.name),
                    "resolution": f"{res_x}, {res_y} (Degrees)",
                    "crs": src.crs.to_string() if src.crs else "Unknown",
                    "width": src.width,
                    "height": src.height,
                    "nodata": src.nodata,
                    "bounds": {
                        "west": bounds.left,
                        "south": bounds.bottom,
                        "east": bounds.right,
                        "north": bounds.top
                    }
                }
        except Exception as e:
            self._status = "UNAVAILABLE"
            self._summary = {"error": f"Failed to load DEM: {str(e)}"}

    def get_status(self):
        return {
            "status": self._status,
            "source": self._summary.get("source", "SRTM DEM") if self._summary else "SRTM DEM",
            "details": self._summary
        }

    def get_elevation(self, latitude: float, longitude: float) -> dict:
        if self._status != "REAL":
            return {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": None,
                "source": "SRTM DEM",
                "status": "UNAVAILABLE",
                "error": "Real DEM not installed or loaded properly."
            }

        try:
            with rasterio.open(self.dem_file) as src:
                bounds = src.bounds
                # Check if requested point is inside DEM bounds
                if not (bounds.left <= longitude <= bounds.right and bounds.bottom <= latitude <= bounds.top):
                    return {
                        "latitude": latitude,
                        "longitude": longitude,
                        "elevation_m": None,
                        "source": "SRTM DEM",
                        "status": "UNAVAILABLE",
                        "error": "location_outside_dem"
                    }
                
                # Use standard generator to sample pixel array at given coords
                # sampling takes [(x, y)] format
                val = next(src.sample([(longitude, latitude)]))
                
                actual_elevation = float(val[0])
                
                # Check NoData
                if src.nodata is not None and math.isclose(actual_elevation, src.nodata):
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
                    "elevation_m": actual_elevation,
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
