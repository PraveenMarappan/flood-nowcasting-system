# INDEPENDENT VALIDATION REPORT — CHENNAI URBAN FLOOD NOWCASTING SYSTEM

**Model Version:** `GRID_HYDROLOGY_V1`  
**Legacy Baseline Version:** `LEGACY_HEURISTIC`  
**Overall Validation Status:** **`NOT VALIDATED`**  
**Scientific Classification:** **`COMPLETE BUT NOT VALIDATED`**  

---

## 1. Validation Gate Evaluation

To claim system validation, all 4 automated backend gates must evaluate to `PASSED`:

| Gate Name | Status | Detail |
| :--- | :--- | :--- |
| **Forcing Completeness Gate** | **`PASSED`** | 241/241 half-hourly NASA GPM IMERG V07B granules acquired & verified |
| **Event Depth Observations Gate** | **`FAILED`** | 0 event-matched sub-daily numerical depth measurements available for 2015 |
| **Calibration Gate** | **`FAILED`** | Parameter calibration uncompleted due to lack of ground-truth depth data |
| **Independent Validation Gate** | **`FAILED`** | Independent event validation unavailable |

---

## 2. Model Comparison Benchmark

| Metric / Dimension | `LEGACY_HEURISTIC` | `GRID_HYDROLOGY_V1` | Notes |
| :--- | :--- | :--- | :--- |
| **Rainfall-Runoff Logic** | Linear heuristic multiplier | Excess rainfall ($R \cdot C$) | Physically defensible runoff calculation |
| **Spatial Terrain Routing** | Elevation threshold proxy | Topographic D8 Flow Accumulation | Continuous terrain routing on SRTM DEM |
| **Ponding Estimation** | Fixed multiplier | Non-linear flow accumulation scaling | Hydrologically informed depression storage |
| **Hydraulic Drainage Coupling** | `UNAVAILABLE` | `UNAVAILABLE` (0.0 cm reduction) | Both models preserve no-subtraction safeguard |

---

## 3. Diagnostic UNKNOWN-Event Depth Comparison

The 192 available depth points have unverified event attribution (`UNKNOWN`) and are maintained strictly as diagnostic spatial comparisons:

- **Mean Absolute Error (MAE):** 25.211 cm
- **Root Mean Square Error (RMSE):** 31.161 cm
- **Model Mean Bias:** -25.211 cm
- **Median Absolute Error:** 21.41 cm
- **Sample Count:** 192 valid spatial point comparisons

> [!WARNING]
> These metrics belong to the `UNKNOWN` population and **must not** be interpreted or reported as 2015 event-validation metrics.
