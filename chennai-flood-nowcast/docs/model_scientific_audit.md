# Scientific Model Audit: Chennai Urban Flood Nowcasting System (`GRID_HYDROLOGY_V1`)

> **Audit Date**: 2026-09-24  
> **Model Version**: `GRID_HYDROLOGY_V1`  
> **Classification**: Grid-Based Hydrological Flood-Depth Estimate  
> **Validation Status**: `NOT_VALIDATED`  
> **Calibration Status**: `NOT_CALIBRATED`  
> **Drainage Mode**: `GEOMETRIC_ONLY`

---

## 1. Model Purpose
The `GRID_HYDROLOGY_V1` model provides a physically defensible, spatially distributed hydrological flood-depth estimate for the Chennai Metropolitan Region. It transitions the system from a global empirical multiplier (`LEGACY_HEURISTIC`) to a grid-based rainfall-runoff and topological flow accumulation engine designed for real-time nowcasting and scenario simulation.

---

## 2. Model Architecture
The hydrological engine is structured as a modular pipeline in `backend/app/services/hydrology/`:
- **`rainfall_runoff.py`**: Calculates excess rainfall depth $P_{\text{excess}}$ from forcing intensity and land-cover runoff coefficients.
- **`dem_processing.py`**: Computes projected cell area ($m^2$), slope gradient, and DEM sink filling.
- **`flow_accumulation.py`**: Executes D8 topological queue flow direction and flow accumulation routing.
- **`ponding.py`**: Computes terrain convergence factors based on slope and accumulated contributing area.
- **`flood_depth.py`**: Integrates excess rainfall, ponding factors, and exponential physical dissipation ($\tau = 2.0\text{ hrs}$).
- **`model_provenance.py`**: Attaches standardized scientific metadata tags (`REAL`, `DERIVED`, `ASSUMED`, `SIMULATED`, `NOT_CALIBRATED`, `NOT_VALIDATED`).

---

## 3. Governing Equations

### A. Excess Rainfall
$$P(\text{mm}) = \text{Rainfall Rate } (\text{mm/hr}) \times \Delta t (\text{hr})$$
$$P_{\text{excess}} (\text{mm}) = P(\text{mm}) \times C$$

### B. Geodesic Cell Area
$$A_{\text{cell}} (\text{m}^2) = (111320 \cdot \cos(\phi) \cdot \Delta\text{lon}) \times (110574 \cdot \Delta\text{lat}) \approx 925 \text{ m}^2 \quad (\text{at } 13^\circ\text{ N})$$

### C. Slope Gradient
$$S = \sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2} \quad (\text{m/m})$$

### D. Terrain Convergence / Ponding Factor
$$F_{\text{ponding}} = 1.0 + \min\left(2.5, \max\left(0.0, \frac{\log_{10}(A_{\text{cells}} + 1)}{\max(S, 0.001)} \cdot 0.002\right)\right)$$

### E. Surface Water Depth
$$D_{\text{base}} (\text{cm}) = \left(\frac{P_{\text{excess}}}{10}\right) \times F_{\text{ponding}}$$

### F. Exponential Dissipation Decay
$$R(t) = \exp\left(-\frac{t}{\tau}\right), \quad \tau = \frac{T_{1/2}}{\ln(2)} \quad (T_{1/2} = 2.0 \text{ hours})$$

---

## 4. Input Datasets

| Dataset | Provider / Source | Resolution / Format | Provenance Label |
| :--- | :--- | :--- | :--- |
| **Precipitation Forcing** | NASA GPM IMERG Early/Final Run | ~0.1° (~10 km), GeoTIFF/HDF5 | `REAL` (Observed) / `SIMULATED` |
| **Digital Elevation Model** | USGS SRTM 1 Arc-Second | 1 Arc-Second (~30m), GeoTIFF | `REAL` |
| **Drainage Network** | Greater Chennai Corporation (2023) | 10,255 LineStrings (GeoJSON) | `REAL` (Geometry Only) |
| **Road Network** | OpenStreetMap (OSM) | 73,174 LineStrings (GeoJSON) | `REAL` |

---

## 5. Spatial Resolution
- **Forcing Resolution**: ~0.1° (~10-11 km). Resampling onto the computational grid distributes the observation spatially but **does NOT create street-level rainfall measurements**.
- **Computational Grid**: 30m $\times$ 30m cells ($\approx 925\text{ m}^2$).
- **Road Network Mapping**: Nearest-cell spatial lookup onto 73,174 OSM segments.

---

## 6. Temporal Resolution
- **Forcing Input**: 30-minute IMERG timesteps.
- **Model Calculation**: 1.0-hour standard operational timestep ($\Delta t = 1.0$).
- **Forecast Window**: 0 to 180 minutes (+30m steps).

---

## 7. DEM Processing
- **Coordinate Reference System**: WGS 84 (EPSG:4326).
- **Sink Filling**: Deterministic single-pass pit filling to ensure valid topological flow routing.
- **Limitation**: DEM processing removes numerical DEM artifacts but may also flatten physical micro-depressions.

---

## 8. Rainfall-Runoff Transformation
- Converts precipitation depth to runoff excess using land-cover coefficient $C$.
- Land-cover proxy: Built-up urban ($C = 0.85$), Vegetation ($C = 0.40$), Water body ($C = 1.0$).
- Mass conservation verified: $V_{\text{excess}} = (P_{\text{excess}} / 1000) \times A_{\text{cell}}$ within $10^{-5}$ tolerance.

---

## 9. Flow Accumulation
- **Routing Engine**: D8 single-flow direction algorithm.
- **Accumulation**: Downstream accumulation queue counts upstream contributing cells $A_{\text{cells}}$.
- **Contributing Area**: $A_{\text{contrib}} = A_{\text{cells}} \times A_{\text{cell}}$ ($\text{m}^2$).

---

## 10. Ponding / Storage
- Empirical terrain convergence factor $F_{\text{ponding}}$ scales runoff depth based on slope $S$ and accumulated upstream flow $A_{\text{cells}}$.
- Parameter provenance: `DERIVED` ratio with `ASSUMED` empirical scaling multiplier.

---

## 11. Flood-Depth Calculation
- Combines excess rainfall depth and ponding factor to calculate initial depth $D_{\text{base}}$.
- Exponential decay function dissipation ($\tau = 2.0\text{ hrs}$) models post-cessation drainage recession.

---

## 12. Drainage Treatment
- **Mode**: `GEOMETRIC_ONLY`.
- Proximity, density, and DBI diagnostics are calculated for user display.
- **Safety Rule**: Drain proximity does **NOT** subtract water depth because hydraulic capacity, pipe diameters, invert elevations, and outfall conditions are `UNKNOWN`.

---

## 13. Parameter Provenance

| Parameter | Value | Unit | Provenance | Source / Rationale |
| :--- | :--- | :--- | :--- | :--- |
| Runoff Coeff ($C$) | 0.85 | dimensionless | `ASSUMED` | Urban built-up land cover proxy |
| Cell Area ($A_{\text{cell}}$) | ~925 | m² | `DERIVED` | Geodesic calculation at 13° N |
| Slope ($S$) | Derived | m/m | `DERIVED` | Central difference gradient on DEM |
| Ponding Multiplier | 0.002 | dimensionless | `ASSUMED` | Empirical convergence scaling |
| Decay Half-Life ($T_{1/2}$) | 2.0 | hours | `ASSUMED` | Literature-based urban drainage recession |
| Max Depth Cap | 200.0 | cm | `ASSUMED` | Physical safety boundary |

---

## 14. Calibration Status
- **Status**: `NOT_CALIBRATED`.
- Calibration framework (`CalibrationService`) is fully operational ($\text{MAE}, \text{RMSE}, \text{Bias}$), awaiting continuous event-matched historical forcing data.

---

## 15. Validation Status
- **Status**: `NOT_VALIDATED`.
- **Historical Forcing**: 128 / 241 timesteps of the 2015 storm event available (113 timesteps missing).
- **Depth Benchmarks**: 192 static ground-truth depth records exist without exact event timestamps (`UNKNOWN_EVENT_DEPTH_OBSERVATIONS`: $\text{MAE} = 25.242\text{ cm}, \text{RMSE} = 31.186\text{ cm}, \text{Bias} = -25.242\text{ cm}$).

---

## 16. Known Limitations
1. **Coarse Forcing**: NASA IMERG (~0.1°) spatially distributed onto a 30m grid is not street-level observation.
2. **Hydrological vs Hydraulic**: Model computes a grid-based hydrological estimate, not a full 2D Shallow Water Equations (SWE) hydrodynamic simulation.
3. **No Hydraulic Drainage Capacity**: SWD network data lacks pipe diameters, slopes, and outfall conditions.
4. **Validation Data Gaps**: Lack of continuous 241-timestep forcing prevents event-matched validation.

---

## 17. Reproducibility
- All calculations are 100% deterministic.
- Model state depends strictly on input parameters, DEM geotiff, and forcing intensity.
- Test suite: `tests/test_grid_hydrology.py` enforces mass conservation, D8 flow routing, and recession monotonicity.

---

## 18. Legacy vs GRID_HYDROLOGY_V1 Comparison

| Scenario | Metric | LEGACY_HEURISTIC | GRID_HYDROLOGY_V1 | Shift |
| :--- | :--- | :--- | :--- | :--- |
| **0.0 mm/hr** | Max Depth | 0.00 cm | 0.00 cm | 0.00 cm |
| **25.0 mm/hr** | Max Depth | 2.25 cm | 2.38 cm | +0.13 cm |
| **50.0 mm/hr** | Max Depth | 4.50 cm | 4.76 cm | +0.26 cm |
| **75.0 mm/hr** | Max Depth | 6.76 cm | 7.14 cm | +0.38 cm |
| **105.0 mm/hr** | Max Depth | 9.46 cm | 10.00 cm | +0.54 cm |
| **+180m Forecast** | Cessation Depth | 9.00 cm | 5.62 cm | Smooth exponential physical decay |
