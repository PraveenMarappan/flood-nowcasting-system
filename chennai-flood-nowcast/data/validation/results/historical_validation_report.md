# 2015 Chennai Flood Event Replay & Historical Validation Report

## Executive Disclaimer

> [!IMPORTANT]
> **2015 Depth Validation:** `NOT_COMPUTABLE` (0 usable depth records for Chennai_2015)  
> **Overall Validation Status:** `NOT_VALIDATED`  
> **Event Replay Status:** `INCOMPLETE` (128 of 241 expected timesteps)  
>  
> **The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.**

---

## 1. Forcing Data & Replay Inventory
* **Event Window:** `2015-11-30T00:00:00Z` to `2015-12-05T00:00:00Z`
* **Dataset:** NASA GPM IMERG Final L3 Half-Hourly (`GPM_3IMERGHH.07` V07B)
* **Replay Timestep:** `0.5 hours` (30 minutes)
* **Expected Timesteps:** 241
* **Available Timesteps:** 141
* **Missing Timesteps:** 100
* **Event Replay Status:** `INCOMPLETE`
* **Processed-Window Peak Rainfall:** 34.07 mm/hr (NOT 2015 event peak rainfall)

---

## 2. Observation Dataset Partitioning

| Category | Total Records | With Observed Depth | Without Observed Depth | Event Depth Validation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Chennai_2015 Attributed** | 753 | **0** | 753 | **NOT_COMPUTABLE** |
| **UNKNOWN Event Attribution** | 192 | **192** | 0 | **AVAILABLE** (Spatial Comparison Only) |
| **Total Benchmark Features** | 945 | 192 | 753 | N/A |

> **Notice:** UNKNOWN event observations were NOT moved into the 2015 validation set.

---

## 3. Quantitative Depth Metrics (UNKNOWN Event Observations)

**Metric Population:** `UNKNOWN_EVENT_DEPTH_OBSERVATIONS`  
**Terminology:** Comparison against UNKNOWN-event depth observations / Spatial depth comparison using observations with unknown event attribution.

> [!WARNING]
> **The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.**

* **`unknown_event_depth_mae_cm`:** **25.24 cm**
* **`unknown_event_depth_rmse_cm`:** **31.19 cm**
* **`unknown_event_depth_bias_cm`:** **-25.24 cm**
* **`unknown_event_depth_median_absolute_error_cm`:** **21.41 cm**
* **`unknown_event_depth_sample_count`:** **192**

---

## 4. Drainage Diagnostics & Terminology

- **Diagnostic Terminology:** Drainage-constrained diagnostic locations
- **SWD Pipe Geometry:** Real spatial geometry loaded from GIS dataset
- **Drainage Diagnostics:** Proximity and density diagnostics computed
- **Hydraulic Capacity:** `UNKNOWN`
- **Hydraulic Conveyance:** `UNAVAILABLE` (No hydraulic conveyance calculated)
- **Hydraulic Coupling:** `UNAVAILABLE`
- **Drainage Effect on Flood Depth:** `0.0 cm` (Drainage does not alter numerical flood depth)

---

## 5. Methodological Limitations & Statuses

### A. 2015 Event Depth Validation Status
* **Status:** `NOT_COMPUTABLE`
* **Reason:** `NO_USABLE_DEPTH_OBSERVATIONS`
* **Details:** The 753 Chennai_2015 attributed records contain zero measured depth values.

### B. Occurrence Validation Status
* **Status:** `NOT_COMPUTABLE`
* **Reason:** `THRESHOLD_NOT_DEFINED`
* **Details:** No standardized inundation threshold is defined in project specifications.

### C. Time-Matched Validation Status
* **Status:** `NOT_COMPUTABLE`
* **Reason:** `OBSERVATION_TIMESTAMPS_UNAVAILABLE`
* **Details:** Historical flood depths lack sub-daily timestamps.

---

## 6. Verification & Summary of Statuses
* **2015 Depth Validation:** `NOT_COMPUTABLE`
* **Unknown-Event Spatial Depth Comparison:** `AVAILABLE`
* **Event Replay Status:** `INCOMPLETE`
* **Occurrence Validation:** `NOT_COMPUTABLE`
* **Time-Matched Validation:** `NOT_COMPUTABLE`
* **Overall Validation Status:** `NOT_VALIDATED`
