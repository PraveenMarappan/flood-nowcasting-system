# GRID_HYDROLOGY_V1 ARCHITECTURE & MATHEMATICAL SPECIFICATIONS

**System Component:** Hydrological Engine (`GRID_HYDROLOGY_V1`)  
**Module Location:** `backend/app/services/flood_model_service.py` & `backend/app/services/hydrology/`  
**Classification:** Grid-Based Hydrological Flood-Depth Estimate  

---

## 1. Mathematical Formulation

`GRID_HYDROLOGY_V1` operates on a 30m grid aligned with the USGS SRTM DEM:

1. **Spatial Excess Rainfall Calculation**:
   $$P_{\text{excess}} = P \cdot C$$
   Where $P$ is precipitation rate (mm/hr) and $C = 0.85$ (baseline catchment runoff coefficient).

2. **Runoff Accumulation**:
   $$\text{Runoff Depth (cm)} = \frac{P_{\text{excess}} \cdot \Delta t}{10}$$
   Where $\Delta t$ is the accumulation timestep (0.5 hours for historical replay, 1.0 hour for current nowcast).

3. **Topographic D8 Flow Accumulation Prioritization**:
   $$\text{Concentration Factor} = 1.0 + \alpha \cdot \log_{10}(A_{\text{acc}} + 1)$$
   Where $A_{\text{acc}}$ is the D8 flow accumulation cell count from SRTM DEM, and $\alpha = 0.15$.

4. **Flood Depth Estimation**:
   $$\text{Flood Depth (cm)} = \text{Runoff Depth (cm)} \cdot \text{Concentration Factor}$$

5. **Drainage Subtraction Safeguard**:
   $$\text{Final Depth (cm)} = \text{Flood Depth (cm)} - 0.0$$

---

## 2. Model Boundaries & Scientific Disclosures

- **Topographic Routing:** D8 single-direction flow accumulation is used for terrain routing. It is **NOT** a full 2D hydrodynamic solver (e.g. Saint-Venant equations).
- **Drainage Effect:** Hydraulic drainage subtraction is disabled (`0.0 cm`) due to the absence of municipal pipe capacity attributes.
- **Validation Status:** `IMPLEMENTED — NOT VALIDATED` (Classification: **`COMPLETE BUT NOT VALIDATED`**).
