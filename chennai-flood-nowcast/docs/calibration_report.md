# MODEL CALIBRATION REPORT — CHENNAI URBAN FLOOD NOWCASTING SYSTEM

**Model Version:** `GRID_HYDROLOGY_V1`  
**Calibration Status:** **`NOT COMPLETED`**  
**Report Date:** 2026-09-26  

---

## 1. Overview & Principles

The hydrological parameters in `GRID_HYDROLOGY_V1` govern spatial excess rainfall, topographic flow accumulation scaling, and depression storage/ponding depth.

To maintain strict scientific integrity, model parameters are **NOT** tuned against unverified observations or synthetic data. Calibration requires event-matched, sub-daily numerical flood-depth gauge measurements divided into distinct training and validation events.

---

## 2. Baseline Parameter Configurations

| Parameter Name | Baseline Value | Parameter Bounds | Units | Provenance | Calibration Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `impervious_surface_fraction` | `0.85` | `[0.30, 0.95]` | ratio | Baseline Spatial Heuristic | `UNCALIBRATED` |
| `flow_accumulation_alpha` | `0.15` | `[0.05, 0.50]` | factor | Baseline Topographic Heuristic | `UNCALIBRATED` |
| `ponding_beta` | `1.00` | `[0.50, 2.00]` | exponent | Baseline Ponding Heuristic | `UNCALIBRATED` |
| `recession_tau_hours` | `3.0` | `[1.0, 12.0]` | hours | Baseline Drainage Decay | `UNCALIBRATED` |

---

## 3. Calibration Status & Blocker

- **Training Event Samples:** 0
- **Validation Event Samples:** 0
- **Calibration Gate Passed:** **`FALSE`**
- **Reason:** No event-matched sub-daily numerical depth observations are available for the 2015 Chennai event. All baseline parameters are retained as initial uncalibrated heuristics.
