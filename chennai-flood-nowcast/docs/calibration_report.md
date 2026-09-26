# Hydrological Model Calibration Report (Occurrence-Based)

**Project**: Chennai Urban Flood Nowcasting System (`SIH26085`)  
**Target Model Version**: `GRID_HYDROLOGY_V1`  
**Calibration Date**: September 26, 2026  
**Calibration Mode**: **`OCCURRENCE-BASED`**  
**Calibration Status**: **`COMPLETED — OCCURRENCE-BASED`**  
**Overall Validation Status**: **`NOT_VALIDATED`**  

---

## Executive Summary

An occurrence-based hydrological parameter calibration was completed for **`GRID_HYDROLOGY_V1`** using the 753 event-attributed spatial flood presence locations from the `Chennai_2015` dataset. 

Because sub-daily numerical street-depth gauge series are unavailable in public domain repositories for the 2015 event, parameter tuning was strictly restricted to spatial flood occurrence optimization to prevent scientific data leakage and avoid fake depth calibration claims.

---

## 1. Calibration Data Rules & Exclusion Hierarchy

1. **`Chennai_2015` Dataset (753 records)**: Used as the primary calibration target for spatial flood occurrence. Contains 753 event-attributed locations with 0 numerical flood-depth measurements.
2. **`UNKNOWN` Dataset (192 records)**: Excluded from calibration due to unverified event timestamps.
3. **River/Canal Stage Logs**: Excluded from street-depth calibration because channel stages cannot be defensibly converted to overland street depths without localized DEM datums.
4. **NASA GPM IMERG Forcing**: 241/241 30-minute historical granules (100% complete).

---

## 2. Parameter Search & Optimization Method

Bounded grid search optimization was conducted across the candidate hydrological parameter space:

- **Runoff Coefficient / Impervious Fraction ($C$)**: Baseline = `0.85`, Search Grid = `[0.50, 0.70, 0.80, 0.85, 0.88, 0.90, 0.92]`.
- **Flow Accumulation Alpha ($\alpha$)**: Baseline = `0.15`, Search Grid = `[0.10, 0.15, 0.20]`.
- **Slope Ponding Beta ($\beta$)**: Baseline = `1.00`, Search Grid = `[0.80, 1.00, 1.20]`.

### Objective Function:
Maximize Categorical F1-Score & Critical Success Index (CSI) evaluated against the 753 `Chennai_2015` spatial presence records at spatial tolerance $\Delta d = 50$ m.

---

## 3. Calibration Results & Parameter Updates

| Parameter | Baseline Value | Calibrated Optimal | Description |
| :--- | :--- | :--- | :--- |
| **Impervious Surface Fraction ($C$)** | `0.85` | **`0.88`** | Fraction of rainfall converted to surface runoff excess |
| **Flow Accumulation Alpha ($\alpha$)** | `0.15` | **`0.10`** | Terrain drainage convergence scaling exponent |
| **Ponding Exponent Beta ($\beta$)** | `1.00` | **`0.80`** | Micro-topographic depression storage exponent |

---

## 4. Baseline vs Calibrated Performance Comparison

| Metric | Baseline Score | Calibrated Score | Delta / Improvement |
| :--- | :--- | :--- | :--- |
| **Precision** | `0.9084` (90.84%) | **`0.9230` (92.30%)** | **`+0.0146` (+1.46%)** |
| **Recall / POD** | `1.0000` (100.00%) | **`1.0000` (100.00%)** | `0.0000` |
| **F1-Score** | `0.9520` (95.20%) | **`0.9600` (96.00%)** | **`+0.0080` (+0.80%)** |
| **Critical Success Index (CSI)** | `0.9084` (90.84%) | **`0.9230` (92.30%)** | **`+0.0146` (+1.46%)** |
| **False Alarm Ratio (FAR)** | `0.0916` (9.16%) | **`0.0770` (7.70%)** | **`-0.0146` (-1.46%)** |

---

## 5. Independent Validation Integrity Safeguard

- **Calibration Status**: `COMPLETED — OCCURRENCE-BASED`
- **Independent Validation Dataset**: `NONE AVAILABLE`
- **Independent Validation Status**: **`NOT_VALIDATED`**
- **Scientific Notice**: Completing occurrence calibration does NOT constitute independent numerical flood-depth validation. Overall system status remains **`NOT_VALIDATED`** (`COMPLETE BUT NOT VALIDATED`).
