# Chennai DEM Data Directory

This directory is intended to store the real Digital Elevation Model (DEM) raster to be used by the flood nowcasting terrain service. 
Due to its large file size and NASA/USGS Earthdata authentication requirements for automated downloads, you must download the DEM manually and place it in this folder.

## Expected DEM

- **Source**: USGS/NASA SRTM 30m (1 arc-second) DEM, or NASA NASADEM.
- **Region**: Chennai (Latitude: 12.85 to 13.25, Longitude: 80.05 to 80.35).
- **Format**: GeoTIFF (`.tif`).
- **CRS**: WGS84 (EPSG:4326) or a compatible projected CRS for metric elevation.

## Instructions

1. Obtain a valid SRTM raster for Chennai. You can download one via [EarthExplorer](https://earthexplorer.usgs.gov/) or use `earthaccess` if previously authorized for topography sets. 
2. The exact raster file should be named: `chennai_dem.tif`.
3. Place `chennai_dem.tif` directly inside this `data/dem` directory.
4. The system's Terrain Service (`terrain_service.py`) automatically checks for this file. 
5. If the file is present, the API `/api/terrain/status` will report `REAL` and the flood model will ingest real elevation. If it is missing, the API will securely fallback to `status: UNAVAILABLE` to ensure no fake data is supplied to the React Frontend.

## Note on Repository 

`.gitignore` is configured to ignore `*.tif` files inside this directory to prevent committing massive binary files to Git.
