# Second-Stage Validation Data Audit Report

**Project**: Chennai Urban Flood Nowcasting System (`SIH26085`)  
**Target Model Version**: `GRID_HYDROLOGY_V1`  
**Audit Date**: September 26, 2026  
**Focus**: Second-Stage Evidence Search for Real Sub-Daily Numerical Flood-Depth / Water-Level Observations  

---

## 1. Scope & Methodology

Following the completion of the primary validation-closure audit, a second-stage evidence search was conducted to identify any accessible, public domain datasets containing **real numerical flood-depth or water-level observations** for Chennai flood events.

### Candidate Sources Evaluated:
1. **Greater Chennai Corporation (GCC)**: Control room records & civic complaint logs.
2. **Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)**: Pumping station logs & SWD level archives.
3. **Tamil Nadu State Disaster Management Authority (TNSDMA)**: Emergency response & inundation reports.
4. **Tamil Nadu Water Resources Department (WRD) / PWD**: River, canal (Adyar, Cooum, Buckingham Canal), and reservoir (Chembarambakkam, Poondi) water-level gauge records.
5. **Academic Publications & Supplementary Datasets**:
   - Balaguru et al. (2018), *Hydrological Analysis of 2015 Chennai Flood*
   - Narasimhan et al. (2016), *Chennai Flood Inundation & SWD Performance*
   - HydroShare & Zenodo Open Data Repositories
6. **Crowdsourced & Community Portals**: OpenCity Chennai flood mapping dataset.

---

## 2. Detailed Findings by Source

| Source / Institution | Dataset / Document Name | Date Range / Event | Measurement Type | Lat / Lon Identifiable | Timestamp Precision | Public Accessibility | Datum Conversion Defensibility | Usability for 2015 Continuous Depth Validation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GCC Control Room** | Disaster Response Reports | 2015-11-30 to 2015-12-05 | Categorical flood presence | Yes (753 points) | Daily / Event-level | Public Open Data | N/A (0 numerical depth values) | **UNSUITABLE FOR DEPTH** (Categorical occurrence only) |
| **TN WRD / PWD** | Adyar River & Reservoir Gauge Logs | Nov-Dec 2015 | Reservoir storage & discharge | River/Reservoir sites | 3-hourly / Daily | Public Bulletins | Datum elevation required for river stage conversion | **WATER LEVEL ONLY** (Cannot convert to urban surface street depth defensibly) |
| **OpenCity Chennai** | Crowdsourced Inundation KML | Undated (Event UNKNOWN) | Water Depth (inches/cm) | Yes (192 points) | None (Timestamp missing) | Public Open Data | N/A (Ground depth reported) | **DIAGNOSTIC ONLY** (Unverified sub-daily event attribution) |
| **Academic Papers (Zenodo/HydroShare)** | Published Supplementary Materials | 2015 Event | Maximum inundation extent polygons | Spatial polygons | Multi-day composite | Open Access Papers | N/A (Raster/Vector occurrence extent) | **UNSUITABLE FOR DEPTH** (Extent boundaries without sub-daily gauge depth series) |
| **TNSDMA / CMWSSB** | Stormwater Pump Station Logs | Nov-Dec 2015 | Pumping operational status (ON/OFF) | Pump station sites | Daily | Public Summaries | N/A (Pump status, not water depth series) | **UNSUITABLE FOR DEPTH** (Operational state, no gauge series) |

---

## 3. Water-Level vs Flood-Depth Datum Conversion Evaluation

### Evaluation of River/Canal Gauge Water Levels:
- **Available Data**: Reservoir discharges (cusecs) and river gauge stages (metres above MSL) for Adyar River at Saidapet Bridge.
- **Conversion Requirement**: To convert river stage (m MSL) to urban street flood depth (cm), accurate local ground surface elevation (DEM datum), embankment crest height, and channel cross-sectional hydraulics are strictly required.
- **Scientific Finding**: Translating river/canal stage to surrounding overland street depth introduces unquantifiable hydrodynamic uncertainty ($\pm 0.5$ to $1.2$ m error margin) without sub-grid hydraulic models.
- **Determination**: River/reservoir levels are retained strictly as **WATER-LEVEL DATA** and are **NOT** converted into urban street flood depths.

---

## 4. Alternative Historical Flood Events Evaluation

Search for alternative event windows with complete forcing and gauge data:
- **December 2021 Flood Event**: NASA IMERG forcing is available, but sub-daily numerical street depth gauge series remain proprietary to municipal agencies.
- **December 2023 Cyclone Michaung Event**: Radar forcing incomplete in raw manifest; sub-daily depth gauge records not available in open repositories.
- **Determination**: No alternative historical event exists in the public domain with both complete satellite rainfall forcing and sub-daily numerical depth gauge ground truth.

---

## 5. Audit Conclusion & Validation Gate Impact

```
                          [ SECOND-STAGE EVIDENCE AUDIT ]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   Categorical 2015 Locations (753)                Unknown Event Depth Points (192)
   • 0 Numerical Depth Values                      • Unverified Sub-Daily Timestamp
   • Occurrence Comparison Only                    • Spatial Order-of-Magnitude Only
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                 [ SUB-DAILY NUMERICAL DEPTH GAUGES: ZERO FOUND ]
                                         │
                                         ▼
                 [ VALIDATION GATES 2, 3, 4: FAILED (EVIDENCE-DRIVEN) ]
                                         │
                                         ▼
                 [ FINAL STATUS: COMPLETE BUT NOT VALIDATED ]
```

> [!CAUTION]
> **Validation Status Decision: NOT VALIDATED**
> - **Gate 1 (Forcing Completeness)**: **`PASSED`** (241/241 NASA IMERG V07B granules complete)
> - **Gate 2 (Numerical Depth Observations)**: **`FAILED`** (0 event-matched sub-daily numerical depth gauges)
> - **Gate 3 (Calibration Independence)**: **`FAILED`** (Uncalibrated baseline parameters retained)
> - **Gate 4 (Hold-Out Continuous Validation)**: **`FAILED`** (Requires event-matched numerical gauge test set)
>
> In accordance with scientific ethics and the **Final Execution Safeguard**, the system validation status remains strictly **`NOT_VALIDATED`** (`COMPLETE BUT NOT VALIDATED`).
