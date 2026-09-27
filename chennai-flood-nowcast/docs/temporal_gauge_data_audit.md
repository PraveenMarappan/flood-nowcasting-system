# Temporal Gauge Data Audit & Hydrological Observation Report — Chennai 2015 Flood

## Executive Summary
This document presents an exhaustive, evidence-based audit of public datasets, government reports, academic repositories, and open science data clearinghouses conducted for the Chennai 2015 extreme flood event.

As mandated by scientific validation standards and explicit project protocol:
- **Zero Data Fabrication:** No synthetic gauge records or continuous interpolations have been manufactured.
- **Strict Data Provenance Separation:** Verified reservoir water-level observations from official Comptroller and Auditor General of India (CAG) / WRD reports are ingested and audited, but are **EXPLICITLY NOT** labeled as urban street-level flood-depth gauge observations.
- **No Conflation of Physical Variables:** Reservoir water level ($ft$) and channel discharge ($cusec$) are physically distinct from urban overland inundation depth ($cm$). Direct model-vs-observation scoring (MAE/RMSE) between street flood models and reservoir levels is strictly prohibited.

---

## 1. Verified Historical Hydrological Dataset: Chembarambakkam Reservoir (Dec 1–2, 2015)

### Source & Official Provenance
- **Primary Source:** Comptroller and Auditor General of India (CAG) Performance Audit Report: *"Performance Audit of Flood management and response in Chennai and its suburban areas"* (Government of India / Tamil Nadu Water Resources Department - WRD).
- **Event:** Chennai December 2015 Extreme Flood.
- **Location:** Chembarambakkam Tank (Reservoir), Kanchipuram / Chennai Region.
- **Variable:** Reservoir Water Level ($ft$), Inflow ($cusec$), Outflow ($cusec$).
- **Source Type:** `GOVERNMENT_REPORT` (`CAG / WRD`).
- **Observational Status:** `observational: true`, `synthetic: false`.

### Verified Timestamped Observation Series (10 Records)

| Timestamp (UTC) | Water Level ($ft$) | Inflow ($cusec$) | Outflow ($cusec$) | Source Agency | Data Provenance Classification |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `2015-12-01 06:00:00` | 22.08 | 960 | 900 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |
| `2015-12-01 09:00:00` | 22.30 | 7,500 | 3,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |
| `2015-12-01 12:00:00` | 22.70 | 14,000 | 12,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |
| `2015-12-01 16:00:00` | 23.06 | 24,932 | 20,600 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |
| `2015-12-01 18:00:00` | 23.20 | 29,000 | 29,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |
| `2015-12-01 20:00:00` | **23.40** | **31,000** | 29,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` (PEAK) |
| `2015-12-02 00:00:00` | **23.40** | 29,000 | 29,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` (PEAK) |
| `2015-12-02 02:00:00` | 23.30 | 26,000 | 29,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |
| `2015-12-02 06:00:00` | 23.07 | 26,000 | 29,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |
| `2015-12-02 12:00:00` | 22.64 | 23,000 | 29,000 | CAG / WRD | `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` |

### Hydrograph Summary Statistics
- **Observed Peak Water Level:** $23.40\,ft$ (Occurred at `2015-12-01 20:00` and maintained through `2015-12-02 00:00`).
- **Minimum Water Level:** $22.08\,ft$ (at `2015-12-01 06:00`).
- **Total Water Level Rise:** $1.32\,ft$ ($0.402\,m$).
- **Maximum Peak Inflow:** $31,000\,cusec$ ($877.8\,m^3/s$).
- **Maximum Peak Outflow / Release:** $29,000\,cusec$ ($821.2\,m^3/s$).
- **Time to Peak:** 14.0 hours from initial observation (`06:00` to `20:00` on Dec 1).

---

## 2. Explicit Data-Provenance Classification Matrix

To maintain strict scientific integrity, temporal validation categories are strictly demarcated:

| Provenance Category | Status | Rationale & Evidence |
| :--- | :--- | :--- |
| `TEMPORAL_HYDROLOGICAL_VALIDATION` | **AVAILABLE** | Verified 10-point sub-daily reservoir water level and discharge series available from official CAG/WRD report. |
| `CHEMBARAMBAKKAM_RESERVOIR_VALIDATION` | **VALIDATED_DATASET_AVAILABLE** | Official government audit record of reservoir storage dynamics for Dec 1–2, 2015. |
| `TEMPORAL_URBAN_FLOOD_DEPTH_GAUGE_VALIDATION` | **NOT VALIDATED** | No continuous or sub-daily street-level urban flood-depth gauge time-series exists in the public domain for 2015. |
| `TEMPORAL_ADYAR_RIVER_GAUGE_VALIDATION` | **NOT VALIDATED** | Sub-daily continuous river hydrograph gauge records for the main stem of Adyar River are not publicly available for 2015. |
| `TEMPORAL_STREET_FLOOD_DEPTH_VALIDATION` | **NOT VALIDATED** | Urban inundation nowcasting model cannot be scored against reservoir levels due to physical dissimilarity. |

---

## 3. Scientific Rules Governing Usage

1. **No Artificial Scoring:** Urban grid-based surface runoff/ponding depth ($cm$) is physically distinct from reservoir storage ($ft$). Direct model error metrics ($MAE$, $RMSE$, $R^2$, $NSE$, $Pearson\ r$) are **NOT** calculated between street flood models and reservoir levels.
2. **Boundary Condition & Forcing Utility:** The Chembarambakkam hydrograph provides verified evidence of the upstream hydrological boundary conditions that caused the catastrophic downstream flooding of the Adyar river basin on Dec 1–2, 2015.
3. **Dynamic Dashboard Transparency:** The validation dashboard displays **`Temporal Hydrological Data: AVAILABLE`** (referencing the Chembarambakkam reservoir series) alongside **`Urban Flood-Depth Temporal Gauge: NOT VALIDATED`**.

---

## 4. System Status Summary

- **Temporal Hydrological Observations:** `AVAILABLE` (Chembarambakkam 2015, CAG/WRD, 10 records)
- **Urban Flood-Depth Temporal Validation:** `NOT VALIDATED`
- **Spatial Numerical Depth Validation:** `SPATIAL HOLDOUT VALIDATED` (192 OpenCity points, 39 Holdout MAE = 25.18 cm)
- **Overall Model Validation Status:** `PARTIALLY VALIDATED — SPATIAL HOLDOUT ESTABLISHED`
