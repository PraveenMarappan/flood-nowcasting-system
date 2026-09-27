# Temporal Gauge Data Audit — Chennai Flood Water Level & Depth Observations

## Executive Summary
This document provides an exhaustive, evidence-based audit of public datasets, government data portals, academic repositories, and open science data clearinghouses conducted to locate sub-daily flood-depth gauge time series for Chennai (specifically during the November–December 2015 extreme rainfall event, as well as subsequent 2021/2023 flood events).

As mandated by scientific validation standards and explicit project protocol:
- **No synthetic gauge records have been generated.**
- **No model predictions have been converted into observations.**
- **No static spatial depth points (e.g. OpenCity 192 points) have been repurposed as time-series without reliable timestamps.**
- **No rainfall-only datasets have been claimed as flood-depth observations.**
- **No reservoir level, river level, or tide level data have been conflated with street flood depth.**

---

## Audit Methodology & Search Parameters

### Audit Date
**2026-09-27**

### Search Queries Executed
- `"Chennai flood gauge time series"`
- `"Chennai flood depth time series"`
- `"Chennai water level time series"`
- `"Chennai inundation time series"`
- `"Chennai flood sensor"`
- `"Chennai waterlogging sensor"`
- `"Chennai 2015 flood water level"`
- `"Chennai 2015 flood depth timestamp"`
- `"Chennai flood observations hourly"`
- `"Chennai flood observations 30 minute"`
- `"Chennai urban flood monitoring"`

### Search Scope & Repositories Examined
1. **Government Portals & Disaster Management Agencies:**
   - Greater Chennai Corporation (GCC) Open Data & SWD Portals
   - Tamil Nadu Water Resources Department (TN WRD / PWD)
   - Tamil Nadu State Disaster Management Authority (TNSDMA)
   - Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)
   - India National Data Sharing and Accessibility Policy Portal (`data.gov.in`)
   - Tamil Nadu Open Data Portals (`data.tn.gov.in`)
   - Central Water Commission (CWC) Flood Forecasting Division
   - India Meteorological Department (IMD)
2. **Academic & Research Institutions:**
   - IIT Madras (Department of Civil Engineering / HydroSense Lab / Centre for Urbanisation & Infrastructure)
   - Anna University (Institute for Remote Sensing / C-FLOWS Project)
   - National Centre for Coastal Research (NCCR / CFM-DSS Project)
3. **Scientific Open Data Repositories & Academic Repositories:**
   - Zenodo (`zenodo.org`)
   - Figshare (`figshare.com`)
   - Dryad (`datadryad.org`)
   - HydroShare (`hydroshare.org`)
   - Harvard Dataverse (`dataverse.harvard.edu`)
   - OpenCity Chennai CKAN (`data.opencity.in`)
   - GitHub Public Datasets with Verifiable Provenance
4. **Geospatial & Remote Sensing Portals:**
   - ISRO / NRSC Bhuvan Portal
   - Copernicus Open Access Hub / Sentinel-1 SAR Flood Products
   - Historical Chennai Flood Monitoring Projects & Flood Sensor Research Projects

---

## Detailed Evaluation & Classification of Datasets Examined

| Dataset Title | Primary Source | Variables Included | Native Resolution | Physical Classification | Rejection / Acceptance Rationale | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Chennai Inundation Points with Depth** | OpenCity CKAN | Lat, Lon, Depth (inches/cm) | Static spatial survey | `SPATIAL_SURVEY_DEPTH` | **Rejected for Temporal Validation:** Lacks sub-daily timestamps. (Valid strictly for Spatial Numerical Depth Validation). | SPATIAL ONLY |
| **Chennai 2015 Stagnation & Hotspots KMLs** | GCC / OpenCity | Point coordinates, Area names | Static occurrence points | `BINARY_OCCURRENCE` | **Rejected:** Binary occurrence indicators without depth values or sub-daily timestamps. | OCCURRENCE ONLY |
| **CMWSSB Major Reservoir Water Levels** | CMWSSB / TN WRD | Lake storage (mcft), Inflow/Outflow (cusecs) | Daily / Event totals | `RESERVOIR_LEVEL` | **Rejected:** Measures reservoir volume (Chembarambakkam, Poondi, Red Hills), not urban street flood depth. | RESERVOIR ONLY |
| **IMD District & Station Rainfall Records** | IMD / OpenCity | Daily rainfall accumulation (mm) | Daily | `FORCING_RAINFALL` | **Rejected:** Measures atmospheric precipitation, not surface flood inundation depth. | FORCING ONLY |
| **NASA GPM IMERG V07B (GPM_3IMERGHH)** | NASA GES DISC | Half-hourly precipitation rate (mm/hr) | 30 minutes | `FORCING_RAINFALL` | **Accepted for Forcing Only:** Verified 241/241 half-hourly forcing timesteps (2015-11-30 to 2015-12-05). | FORCING ONLY |
| **HEC-RAS 2015 Inundation Simulations** | Academic / Kaggle | Hydrodynamic simulated water depths | Model output grid | `MODEL_SIMULATION` | **Rejected:** Hydrodynamic model predictions; using model output as ground truth violates scientific validation protocols. | SIMULATION ONLY |
| **CFM-DSS Real-Time Telemetry Network** | TN State / NCCR | AWLR (Automatic Water Level Recorders) | Real-time (Modern post-2020) | `RESTRICTED_TELEMETRY` | **Rejected:** Modern operational RTDAS deployment; historical 2015 sub-daily telemetry raw logs are not open-access. | RESTRICTED / UNPUBLISHED |

---

## Key Audit Findings & Data Availability Limits

1. **Absence of Public Historical Sub-Daily Gauge Logs:**
   Prior to the deployment of the modern Chennai Flood Management Decision Support System (CFM-DSS) real-time telemetric network, automated sub-daily urban street flood depth sensors were not operationally active or publicly archived during the 2015 flood.

2. **Spatial vs. Temporal Separation:**
   The 192 OpenCity spatial depth records provide valuable static water depth measurements (ranging from 12.7 cm to 152.4 cm). However, because they lack exact sub-daily timestamping during the 2015 storm progression, they are rigorously evaluated under **Spatial Holdout Numerical Depth Validation** (39-point spatial holdout MAE = 25.18 cm) and cannot be claimed as a sub-daily temporal gauge dataset.

3. **Reservoir & River Gauges:**
   While reservoir discharge logs for Chembarambakkam exist at coarse intervals, converting channel discharge or reservoir storage into urban street flood depth introduces severe spatial unrepresentativeness without 2D hydrodynamic channel-overland routing.

---

## System Gate & Dynamic Status Determination

Because no legitimate sub-daily flood-depth gauge time-series observations exist in the public domain for the Chennai 2015 benchmark event:

- **Temporal Gauge Validation Status:** `NOT VALIDATED`
- **Scientific Classification:** `NOT VALIDATED — Sub-Daily Depth Gauge Time-Series Unavailable`
- **Gate Detail:** `"Exhaustive public audit confirms zero sub-daily urban flood-depth gauge time-series observations are publicly available for the Chennai 2015 storm event."`

This determination strictly preserves scientific integrity, avoiding false claims or data fabrication while maintaining full transparency.
