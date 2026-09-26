# Final Scientific Validation Audit: Chennai Urban Flood Nowcasting System

**Date:** 2026-09-26  
**Project:** SIH26085 — Urban Flood Nowcasting System  
**Model Version:** `GRID_HYDROLOGY_V1`  
**Forcing Dataset:** NASA GPM IMERG Final V07B (`GPM_3IMERGHH`)  
**Window:** 2015-11-30T00:00:00Z to 2015-12-05T00:00:00Z  

---

## Executive Audit Summary

| Audit Item | Status / Value | Scientific Rationale |
| :--- | :--- | :--- |
| **Forcing Completeness** | **241 / 241 (100% Complete)** | All 241 half-hourly HDF5 files acquired from NASA GES DISC and verified with SHA256 and HDF5 `Grid/precipitation` structure. |
| **Historical Replay Status** | **COMPLETE** | Full 241-timestep chronological hydrological simulation executed with 0 missing steps. |
| **Active Model Version** | **`GRID_HYDROLOGY_V1`** | Grid-based rainfall-runoff with D8 flow accumulation and ponding factor. |
| **Legacy Comparison** | **`LEGACY_HEURISTIC`** | Preserved as baseline comparison model. |
| **Event Attribution** | **STRICTLY SEPARATED** | 753 `Chennai_2015` records (categorical, 0 depth) and 192 `UNKNOWN` depth records kept strictly distinct. |
| **Drainage Coupling** | **`UNAVAILABLE`** | Drainage effect on depth = 0.0 cm until physical pipe hydraulic attributes exist. |
| **Scientific Validation Status** | **`COMPLETE BUT NOT VALIDATED`** | Forcing & replay are complete; validation status remains `NOT VALIDATED` due to lack of event-matched depth observations. |

---

## Responses to Scientific Audit Questions

### 1. Actual Model Used by Historical Replay
- The active model executed by historical replay is `GRID_HYDROLOGY_V1`.
- Legacy heuristic (`LEGACY_HEURISTIC`) is preserved strictly as a baseline comparison option.

### 2. Forcing Completeness & Integrity
- All 241 expected half-hour timesteps (2015-11-30 00:00 UTC to 2015-12-05 00:00 UTC) exist on disk in `data/forcing/historical/raw/`.
- Every file was authenticated via NASA Earthdata session, checked for HTTP 200, validated for HDF5 `Grid/precipitation` dataset, and recorded in `raw_manifest.json` with file size and SHA256 checksum.

### 3. Data Integrity Policies
- Zero missing timestamps were fabricated, interpolated, padded with zeros, or synthetically generated.
- No duplicate granules or unverified products were introduced.

### 4. Depth Metric Attributions
- The 192 numerical depth observations belong to `UNKNOWN_EVENT_DEPTH_OBSERVATIONS`.
- MAE (25.2106 cm), RMSE (31.1606 cm), Bias (-25.2106 cm), and Median AE (21.41 cm) are computed exclusively on this 192-point population.
- They are NOT attributed to the 2015 Chennai flood event.

### 5. 2015 Event Validation Status
- The 753 `Chennai_2015` records contain categorical flood presence only and 0 numerical depth measurements.
- Metrics for `Chennai_2015` are classified as `NOT_COMPUTABLE`.

### 6. Drainage Hydraulic Coupling
- Drainage hydraulic coupling is explicitly marked `UNAVAILABLE` (`DRAINAGE_GEOMETRIC_ONLY`).
- `drainage_effect_on_flood_depth = 0.0 cm`.

### 7. Dashboard Provenance Alignment
- The dashboard UI strictly displays `NOT VALIDATED` status, `GRID_HYDROLOGY_V1` model version, and 241/241 forcing completeness, ensuring clear distinction between complete forcing and complete validation.
