# Chennai DEM Integration Documentation

## Overview

The Chennai Flood Nowcast uses actual Digital Elevation Models (DEM) to enhance the base hydrological simulation natively rather than inventing topography structure. 
To guarantee data trust, the terrain service explicitly reports `UNAVAILABLE` when a real DEM raster is missing, rather than injecting fake heights silently.

## 1. DEM Data Configuration
- **DEM source:** USGS/NASA SRTM (Shuttle Radar Topography Mission) or NASADEM.
- **Dataset:** SRTM 1 Arc-Second Global (30m resolution).
- **Resolution:** ~30 meters (Pixel dimension ~ `0.000277` arc-degrees)
- **CRS:** WGS84 (EPSG:4326) natively; mathematical projections can be added if needed for precise flow modeling.
- **Chennai coverage:** Minimum bounding box required covers [South: 12.85, North: 13.25, West: 80.05, East: 80.35].

## 2. Download & File Location Procedure
Because the DEM payload is large and pulling it programmatically via an authenticated pipeline takes considerable resources, it is expected to be mounted manually at this stage.

1. Obtain a GeoTIFF using NASA EarthExplorer or OpenTopography.
2. File must be named: `chennai_dem.tif`
3. Path structure: `data/dem/chennai_dem.tif`

The repository `.gitignore` has been strictly instructed to ignore TIFF rasters in that directory to prevent GitHub blobs from exploding.

## 3. Endpoints & Integrations
The `app.services.terrain_service.TerrainService` class wraps the `rasterio` raster querying utility. Out-of-bounds clicks, missing grid squares (NoData), or internal memory faults all safely terminate into a JSON-based error wrapper, returning `status: UNAVAILABLE` directly to the active React DOM.

**APIs Created/Updated:**
* `GET /api/terrain/status`
* `GET /api/terrain/summary`
* `GET /api/terrain/elevation?latitude=..&longitude=..`
* `GET /api/flood/forecast` (Modified to securely scale depth predictions based on a simplistic elevation bracket multiplier)

## 4. Flood Model Interactions (Prototype)
A highly transparent prototype rule-base implements the DEM logic inside `/api/flood/forecast`.
- Local elevations less than 5m suffer a 1.8x depth penalty (heavy water accumulation tendency).
- Local elevations between 5m-15m receive a low penalty (1.2x).
- Highland elevations over 15m immediately shed water quickly, incurring a 0.5x reduction compared to baseline.

***All Flood Model data explicitly uses the MODELLED badge in React to emphasize it is purely an approximation mapping!***

## 5. Known Limitations & Validation
- Elevation values do not map perfectly to storm drains. Real drainage infrastructure heavily distorts how surface runoff obeys gravity.
- 30-meter resolution provides a macro-view, predicting flood volume effectively across sectors, but it cannot guarantee the safety of an individual street corner.
- **DO NOT** claim flood depths predicted here reflect a verified 30-meter high-fidelity simulation. They are mathematically linked, but require a much harsher physical engine (like SWMM or LISFLOOD-FP) for true scientific credibility.
