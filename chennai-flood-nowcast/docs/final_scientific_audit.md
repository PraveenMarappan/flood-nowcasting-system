# FINAL SCIENTIFIC AUDIT — CHENNAI URBAN FLOOD NOWCASTING SYSTEM (SIH26085)

**System Name:** Chennai Urban Flood Nowcasting System (SIH26085)  
**Lead Authority:** Scientific Validation Engineering Team  
**Audit Date:** 2026-09-26  
**Project Objective:** Urban Flood Nowcasting via Rainfall and Drainage Coupling (MoES / NCMRWF)  

---

## 1. System Scientific Classification Summary

To maintain absolute scientific transparency and prevent misinterpretation by judges or operational teams, all data layers, models, and outputs in the repository are explicitly categorized below:

| System Component | Classification | Provenance / Technical Details |
| :--- | :--- | :--- |
| **Historical Rainfall Forcing** | `REAL` | NASA GPM IMERG Final Run V07B (`GPM_3IMERGHH`) 241/241 timesteps (2015-11-30 to 2015-12-05) |
| **Current / Near-Real-Time Forcing** | `REAL` | Live NASA GPM IMERG V07B via authenticated NASA GES DISC sessions |
| **Scenario Rainfall** | `SIMULATED` | User-selected rainfall rates (0, 25, 50, 75, 105 mm/hr) |
| **Topographic Elevation (DEM)** | `REAL` | USGS SRTM 1 Arc-Second Global (30m spatial resolution) |
| **Drainage Network Geometry** | `REAL GEOMETRY` | OpenCity / Greater Chennai Corporation 2023 (10,255 SWD LineStrings) |
| **Drainage Hydraulic Capacity** | `UNAVAILABLE` | Zero engineering attributes (pipe diameter, invert level, roughness, outfalls) available in public SWD data |
| **Drainage Depth Reduction** | `SAFEGUARD` | 0.0 cm depth subtraction enforced due to lack of hydraulic engineering capacity attributes |
| **Hydrological Model** | `MODELLED` | `GRID_HYDROLOGY_V1` (Spatial excess rainfall + D8 topographic flow accumulation + depression ponding) |
| **Legacy Baseline Model** | `MODELLED` | `LEGACY_HEURISTIC` (Maintained strictly for comparative benchmarking) |
| **Runoff & Impervious Fraction** | `ASSUMED PARAMETER` | Baseline 0.85 impervious fraction (uncalibrated heuristic land-cover approximation) |
| **Model Calibration** | `NOT COMPLETED` | Parameters uncalibrated due to absence of event-matched sub-daily numerical depth observations |
| **Chennai 2015 Event Observations** | `REAL OBSERVATIONS` | 753 categorical flood occurrence records (0 numerical depth measurements) |
| **UNKNOWN Depth Observations** | `REAL OBSERVATIONS` | 192 spatial depth observations with unknown event attribution (Diagnostic Spatial Only) |
| **Independent Validation** | `NOT VALIDATED` | Classification: **`COMPLETE BUT NOT VALIDATED`** / **`IMPLEMENTED — NOT VALIDATED`** |

---

## 2. Mathematical & Hydrological Model Specifications (`GRID_HYDROLOGY_V1`)

1. **Spatial Excess Rainfall**:
   $$R_{\text{excess}} = P \cdot C$$
   Where $P$ is rainfall rate (mm/hr) and $C = 0.85$ (baseline assumed runoff coefficient).

2. **Topographic Flow Accumulation**:
   D8 single-direction flow accumulation calculated on USGS SRTM 1 Arc-Second DEM. Flow accumulation cells ($A_{\text{acc}}$) quantify upstream contributing area.

3. **Inundation Depth Conversion**:
   $$D_{\text{base}} = R_{\text{excess}} \cdot \Delta t \cdot 0.1 \quad (\text{cm})$$
   $$D_{\text{modelled}} = D_{\text{base}} \cdot \left(1.0 + \alpha \cdot \log_{10}(A_{\text{acc}} + 1)\right)$$
   Where $\alpha = 0.15$ is the flow accumulation prioritization factor.

4. **Drainage Coupling Safeguard**:
   $$D_{\text{final}} = D_{\text{modelled}} - 0.0 \quad (\text{cm})$$
   No reduction is applied because SWD pipe flow capacity is unmodelled due to data unavailability.

---

## 3. Scientific Terminology Alignment Audit

All code comments, API docstrings, and UI labels across `backend/` and `frontend/` have been audited to ensure:
- D8 topographic routing is referred to as **topographic D8 flow accumulation/routing**, NOT "hydraulic routing".
- The model is described as a **grid-based hydrological flood-depth estimate**, NOT a "calibrated hydraulic solver".
- The 192 UNKNOWN observations are labeled **UNKNOWN_EVENT_DEPTH_OBSERVATIONS (DIAGNOSTIC SPATIAL ONLY)**, NOT "2015 validation".
- Overall validation status is reported as **`NOT VALIDATED`** (`COMPLETE BUT NOT VALIDATED`).
