# Data Requirements for Chennai Urban Flood Model Calibration & Validation

> **Validation Status**: `NOT_VALIDATED`  
> **Current Limitation**: NASA GPM IMERG 2015 historical forcing dataset contains 128 of 241 expected half-hourly timesteps (113 missing). Existing historical inundation points (753 total) lack reliable event-matched depth observations.

To transition the Chennai Urban Flood Nowcasting System from `NOT_VALIDATED` to `PARTIAL` or `VALIDATED` status, the following 7 core data requirements must be fulfilled.

---

## 1. Complete Event Rainfall Forcing
- **Parameter**: Continuous high-temporal resolution precipitation forcing (mm/hr).
- **Required Resolution**: $\le 30$-minute timesteps (preferably 15-minute or gauge-adjusted IMERG / AWS).
- **Target Event**: Chennai November–December 2015 storm (2015-11-30 00:00Z to 2015-12-05 00:00Z, 241 consecutive 30-min timesteps).
- **Current Deficit**: 113 missing timesteps in local GPM IMERG repository.

## 2. Event-Matched Observed Flood Depths
- **Parameter**: In-situ observed water depth ($\text{cm}$) or inundation extent polygons.
- **Required Attributes**:
  - Precise Geodetic Coordinates (Latitude, Longitude, WGS 84).
  - Explicit ISO UTC Timestamp matching the forcing timeframe.
  - Measurement Accuracy / Error Margin (e.g., sensor gauge vs crowd-sourced level marker).
- **Current Deficit**: 753 historical records in `chennai_2015` have 0 reliable depth measurements; 192 depth records belong to `UNKNOWN` unassigned events.

## 3. High-Resolution Terrain & Urban Digital Elevation Model (DEM)
- **Parameter**: Urban Topography DEM / DTM.
- **Required Resolution**: $\le 10 \text{ meter}$ grid resolution with Vertical Accuracy $\le 0.5 \text{ meters}$.
- **Target Data**: Airborne LiDAR or high-accuracy stereo satellite DEM (e.g., Cartosat / TanDEM-X).
- **Current Data**: USGS SRTM 1 Arc-Second (~30m resolution, vertical error $\pm 5-10\text{m}$).

## 4. Hydraulic Storm Water Drain (SWD) Engineering Parameters
- **Parameter**: Pipe & Culvert Hydraulic Parameters.
- **Required Attributes**:
  - Drain internal cross-section / diameter ($m$).
  - Invert elevations ($m$ MSL) at nodes.
  - Manning's roughness coefficient $n$.
  - Flow direction & outfall tidal boundary condition (e.g., Bay of Bengal / Adyar / Cooum sea level head).
- **Current Status**: 10,255 LineString features available as spatial geometry only; hydraulic capacity parameters remain `UNAVAILABLE`.

## 5. Soil & Land-Cover Imperviousness
- **Parameter**: High-resolution Land-Use Land-Cover (LULC) & Infiltration maps.
- **Required Attributes**: High-resolution impervious fraction ($0.0 - 1.0$), Curve Numbers (CN), or Green-Ampt infiltration parameters ($K_{sat}, \psi, \theta$).
- **Current Status**: Configured proxy lookup (`runoff_coefficients.json`) marked `ASSUMED`.

## 6. Tidal & Outfall Boundary Conditions
- **Parameter**: Coastal tide gauge time series (Adyar estuary, Cooum river mouth, Ennore creek).
- **Required Resolution**: Hourly water level ($m$ MSL) during storm events.

## 7. Data Provenance & Verification Criteria
- **Mandatory Requirements**:
  - Verified source attribution (e.g., IMD / GCC / CMWSSB / TNSDMA / ISRO).
  - Peer-reviewed or agency-certified measurement protocol.
  - Explicit uncertainty bounds exposed in dataset metadata.
