# Chennai Flood Nowcasting — Model Assumptions & Documentation

## 1. Rainfall Forcing

| Parameter | Value | Status |
|-----------|-------|--------|
| Input units | mm/hr (rate) | REAL — NASA specification |
| Live dataset | GPM_3IMERGHHE (Early Run) | REAL |
| Historical dataset | GPM_3IMERGHH (Final Run) | REAL |
| Version | V07B | REAL |
| IMERG temporal resolution | 30 minutes | REAL |
| IMERG spatial resolution | 0.1° × 0.1° | REAL |

## 2. Model Timestep

| Context | `timestep_hours` | Reason |
|---------|-----------------|--------|
| Production (live API) | 1.0 | Default — represents 1-hour accumulation assumption |
| Historical IMERG replay | 0.5 | Matches IMERG 30-minute temporal resolution |

### Why `timestep_hours = 0.5` for replay

IMERG provides a rainfall **rate** (mm/hr) sampled every 30 minutes. To convert the rate to accumulated depth for one IMERG timestep:

```
accumulated_mm = rainfall_rate_mm_hr × 0.5 hr = half the hourly rate
```

Using `timestep_hours = 1.0` (the production default) would double the actual 30-minute accumulation, overstating runoff by 2×.

The production default of `1.0` is preserved for all live API callers. Only the isolated historical replay uses `0.5`.

### Equation

```
runoff_rate_mm_hr = rainfall_mm_hr × C
runoff_depth_mm  = runoff_rate_mm_hr × timestep_hours
runoff_depth_cm  = runoff_depth_mm × 0.1
water_depth_cm   = runoff_depth_cm × terrain_concentration_factor
```

## 3. Runoff Coefficient

| Parameter | Value | Status |
|-----------|-------|--------|
| Impervious fraction (C) | 0.85 | HEURISTIC — NOT calibrated |
| Source | Assumed urban Chennai impervious fraction | ESTIMATED |
| Land cover verification | Not done | NOT_VALIDATED |

**C = 0.85 is a heuristic assumption.** It is NOT derived from verified land-use/land-cover data. Future work should replace this with spatially variable C values from satellite-derived land cover classification.

## 4. Terrain Concentration Factor

| Parameter | Value | Status |
|-----------|-------|--------|
| Source | USGS SRTM 1 Arc-Second DEM | REAL (when DEM loaded) |
| Derivative | Flow accumulation → log10 scaling | MODELLED |
| Range | 1.0 to 2.5 (bounded) | HEURISTIC |
| Formula | `min(2.5, 1.0 + log10(flow_acc_cells) × 0.2)` | HEURISTIC |

When the DEM is not available, the concentration factor defaults to 1.0.

## 5. Flood Depth Model

| Parameter | Value | Status |
|-----------|-------|--------|
| Model type | Spatial heuristic estimate | MODELLED |
| Version | v3-spatial-heuristic | MODELLED |
| Calibration | NOT_CALIBRATED | NOT_VALIDATED |
| Spatial resolution | Point-based (evaluated per coordinate) | MODELLED |

The current flood depth model is a **spatial heuristic estimate**. It is NOT a physically-based hydrodynamic model. It does not solve the shallow water equations, the Saint-Venant equations, or any equivalent PDE system.

## 6. Drainage Infrastructure

| Parameter | Value | Status |
|-----------|-------|--------|
| Geometry source | OpenCity / Greater Chennai Corporation | REAL (geometry only) |
| Hydraulic coupling | NOT available | UNAVAILABLE |
| Engineering parameters | NOT available | UNAVAILABLE |
| Capacity | NOT available | UNAVAILABLE |
| Pipe diameter | NOT available | UNAVAILABLE |
| Slope | NOT available | UNAVAILABLE |
| Invert elevation | NOT available | UNAVAILABLE |
| Manning roughness | NOT available | UNAVAILABLE |
| Flow direction | NOT available | UNAVAILABLE |
| Used in flood model | NO | — |

Drainage geometry is available but is **NOT hydraulically coupled** to the flood model. No drainage capacity reduction is applied.

## 7. Historical Forcing Coverage

| Parameter | Value |
|-----------|-------|
| Event window requested | 2015-11-30T00:00:00Z to 2015-12-05T00:00:00Z |
| Expected IMERG files | ~240 (5 days × 48 half-hourly) |
| Currently available | 1 file |
| Available timestamp | 2015-11-30T00:00:00Z |
| Verified rainfall | 5.09 mm/hr at (13.0827°N, 80.2707°E) |
| Status | PARTIAL / INCOMPLETE |

**One HDF5 file is NOT a complete 2015 event replay.** The pipeline supports N files when additional historical IMERG files are acquired.

## 8. Validation Observations

| Parameter | Value |
|-----------|-------|
| Total observations | 945 |
| With observed depth | 192 |
| With categorical status | 753 (Chennai_2015) |
| Reliable timestamps | NONE |
| Event attribution (192 depth) | UNKNOWN |
| Event attribution (753 categorical) | Chennai_2015 |

### Important limitations

- **No timestamps**: Validation observations have no reliable timestamps. Therefore, time-series validation is NOT possible.
- **Unknown event for depth records**: The 192 records with observed depth have `event = UNKNOWN`. They may or may not correspond to the 2015 event.
- **No quantitative depth for Chennai_2015 records**: The 753 Chennai_2015 records have categorical flood/stagnation information but no observed depth values.

## 9. Occurrence Threshold

| Parameter | Value | Status |
|-----------|-------|--------|
| Default value | `null` (not set) | NOT_COMPUTABLE |
| Source | Not yet supplied | — |
| Tuned against validation | No | — |

The occurrence classification threshold is NOT scientifically supplied yet. Therefore, precision/recall/F1 metrics are NOT computable until a threshold is explicitly configured with a documented source.

## 10. Production Validation Status

| System | Status |
|--------|--------|
| `/api/flood/validation` | NOT_VALIDATED |
| Historical replay | PARTIAL |
| Event replay | INCOMPLETE |
| Model validation | NOT_VALIDATED |

The production API continues to report `NOT_VALIDATED` until:
1. The full event forcing window is acquired and replayed
2. The validation methodology and results are scientifically reviewed
3. A human reviewer approves the validation results

## 11. Status Definitions

| Status | Meaning |
|--------|---------|
| REAL | Data comes from a verified real-world source |
| MODELLED | Computed by the model, subject to model assumptions |
| HEURISTIC | Based on a simplified assumption, not physically derived |
| ESTIMATED | An approximation, not verified against observations |
| NOT_VALIDATED | No scientific validation has been completed |
| NOT_CALIBRATED | Model parameters have not been calibrated against observations |
| PARTIAL | Only a subset of required data/processing is complete |
| INCOMPLETE | The full scope has not been covered |
