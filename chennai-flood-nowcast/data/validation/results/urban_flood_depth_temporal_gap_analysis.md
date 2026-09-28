# Urban Flood-Depth Temporal Validation Gap Analysis

## Executive Summary
This document provides an exhaustive scientific audit and gap analysis regarding sub-daily urban flood-depth gauge time-series observations for the Chennai December 2015 extreme rainfall event. 

In accordance with strict scientific integrity rules governing `GRID_HYDROLOGY_V1`:
- **Temporal Reservoir Gauge**: **VALIDATED — TEMPORAL HOLDOUT** (Chembarambakkam Tank, 23 verified sub-daily observations, CAG Report No. 4 of 2017).
- **Urban Flood-Depth Temporal Gauge**: **NOT VALIDATED** (Sub-Daily Urban Flood-Depth Time-Series Unavailable).

Under no circumstances are reservoir water levels (ft) or synthetic interpolations permitted to be substituted for urban street-level flood depth observations (cm).

---

## 1. Audit Scope & Methodology
The audit evaluated public repositories, government archives, academic literature, open data platforms, and satellite observational products for sub-daily, timestamped urban street-level inundation observations during the November 30 – December 5, 2015 storm event.

### Target Validation Requirements
- **Quantity**: Sub-daily continuous or multi-timestamp series.
- **Variable**: Inundation depth (cm/m) at street, intersection, or urban canal locations.
- **Temporal Resolution**: Hourly or sub-hourly timestamps matching model forcing (30-min GPM IMERG timesteps).
- **Spatial Resolution**: Precise geotagged latitude/longitude within Chennai Metropolitan Area.

---

## 2. Public Sources Searched

| Source / Repository | Agency / Entity | Coverage Searched | Outcome |
| :--- | :--- | :--- | :--- |
| **Greater Chennai Corporation (GCC)** | Local Government | Smart City IoT Sensor Logs, Control Room Records | No digital sub-daily depth gauge records exist for 2015. |
| **Water Resources Department (WRD)** | Tamil Nadu Govt | River & Tank Level Logs | Reservoir levels available; no urban street depth time-series. |
| **TNSDMA** | State Disaster Mgmt | 2015 Post-Disaster Reports | Categorical spatial notes; no continuous depth series. |
| **CMWSSB** | Water Supply Board | Pumping Station Logs | Pumping hours recorded; no inundation depth time-series. |
| **OpenCity.in** | Open Data Chennai | 2015 Flood Inundation Points (192 records) | **Spatial numerical depth available**; lacks timestamps. |
| **IMD** | India Met Dept | Automatic Weather Stations (AWS) | Rainfall rate available; no flood depth recorded. |
| **Central Water Commission (CWC)** | Central Govt | River Gauge Stations (Adyar / Cooum) | Peak stage recorded; lack sub-daily street-level hydrographs. |
| **IIT Madras / Anna University** | Academia | Published 2015 Flood Research | High-water mark post-event surveys; no continuous time-series. |
| **Zenodo / Figshare / HydroShare** | Open Science | Global Flood Datasets | No sub-daily 2015 Chennai street-level gauge datasets found. |

---

## 3. Candidate Datasets Rejection Log

| Candidate Dataset | Source | Provided Format | Reason for Rejection for Temporal Validation |
| :--- | :--- | :--- | :--- |
| **OpenCity 192 Inundation Points** | OpenCity | 192 Geotagged spatial points with measured depth (inches) | **Static peak depth points lacking sub-daily timestamps**. Used exclusively for *Spatial Numerical Depth Validation*. |
| **Chembarambakkam Reservoir Hydrograph** | CAG / WRD | 23 sub-daily water level & storage timestamps | **Reservoir level data**. Serves as *Temporal Reservoir Gauge Validation*, strictly separated from urban street inundation. |
| **Chennai Occurrence Points (753 records)** | Crowdsourced | Geotagged locations | **Binary flood occurrence (Yes/No)**; lacks numerical depth and sub-daily timestamping. Used for *Occurrence Validation*. |
| **NRSC Radar Inundation Extent** | ISRO / NRSC | Satellite flood extent polygons | **Snapshot spatial coverage**; lacks continuous temporal profile and street-level depth values. |

---

## 4. Exact Data Required for Future Temporal Validation
To achieve `VALIDATED — TEMPORAL HOLDOUT` status for the Urban Flood-Depth Temporal Gauge layer, the system requires:
1. **Timestamped Hydrographs**: At least 20 sub-daily (15-min to 1-hr interval) water depth measurements at urban street intersections or urban channels.
2. **Quality Control**: Verified gauge calibration and zero-datum baseline relative to ground level.
3. **Geospatial Metadata**: High-precision GPS coordinates for cell matching against `GRID_HYDROLOGY_V1` DEM grid.

---

## 5. Actionable Data Acquisition & Integration Plan
1. **GCC Smart City IoT Telemetry**: Partner with GCC to ingest real-time IoT flood depth sensors installed post-2020 across 200+ vulnerable locations.
2. **Citizen Science Telemetry**: Deploy a standardized, timestamped mobile crowd-sourcing app for real-time flood depth reporting during monsoon events.
3. **Automatic Ultrasonic Gauges**: Install ultrasonic water level loggers along key Adyar/Cooum urban canal cross-sections.
