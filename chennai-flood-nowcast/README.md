# SIH26085 — Urban Flood Nowcasting System
## "Drainage and Rainfall Coupling" (MoES / NCMRWF)

> **Lead Development & Scientific Validation Team**  
> **Repository Status:** `COMPLETE BUT NOT VALIDATED` (`IMPLEMENTED — NOT VALIDATED`)  

---

## 1. Problem Statement
Urban coastal metropolises such as Chennai, India, experience extreme seasonal monsoonal precipitation events (e.g. December 2015 flood). High-density urban sprawl, flat coastal terrain, and unquantified stormwater drainage networks require localized grid-level flood nowcasting models that strictly track data provenance and scientific boundaries.

## 2. Solution Overview
The **Chennai Urban Flood Nowcasting System (SIH26085)** couples real 30-minute NASA GPM IMERG V07B precipitation forcing, real 30m USGS SRTM 1 Arc-Second DEM elevation data, 10,255 real OpenCity/GCC stormwater drain LineStrings, and OSM road networks to provide street-level flood risk estimates via the physically defensible `GRID_HYDROLOGY_V1` hydrological model.

---

## 3. System Architecture & Provenance Matrix

```
[ NASA GPM IMERG V07B ] ──► [ Spatial Excess Rainfall ] ──┐
                                                           ├─► [ GRID_HYDROLOGY_V1 ] ──► [ Road Risk & UI ]
[ USGS SRTM 30m DEM ]   ──► [ D8 Flow Accumulation ]   ──┘
```

| Component | Source / Provenance | Technical Classification |
| :--- | :--- | :--- |
| **Historical Forcing** | NASA GES DISC GPM IMERG Final V07B (241/241 timesteps) | `REAL` |
| **Elevation Data** | USGS SRTM 1 Arc-Second Global DEM | `REAL` |
| **Stormwater Drains** | OpenCity / Greater Chennai Corporation 2023 | `REAL GEOMETRY` |
| **Drainage Hydraulics** | Zero municipal pipe engineering attributes available | `UNAVAILABLE (0.0 cm reduction)` |
| **Hydrological Model** | `GRID_HYDROLOGY_V1` | `MODELLED` |
| **Validation Status** | No sub-daily event-matched depth observations available | **`COMPLETE BUT NOT VALIDATED`** |

---

## 4. Operational & Running Instructions

### Backend Setup (FastAPI & Python 3.10+)
```bash
cd backend
python -m venv venv
# Activate virtual environment
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

### Frontend Setup (React & Vite)
```bash
cd frontend
npm install
npm run dev
```
Open browser at `http://localhost:5173`.

### Automated Test Suite Execution
```bash
cd backend
python -m pytest tests/ -q
```
Target: 108/108 tests passing.

---

## 5. API Endpoints

- `GET /api/health` — System health and active model version.
- `GET /api/rainfall/current` — Latest precipitation from NASA GPM IMERG V07B.
- `GET /api/flood/current?latitude=13.0827&longitude=80.2707` — Flood depth nowcast.
- `GET /api/roads/risk` — Viewport road risk calculation.
- `GET /api/drainage/diagnostics` — SWD proximity and geometric density diagnostics.
- `GET /api/validation/historical` — 241-timestep historical replay & provenance metrics.

---

## 6. Scientific Status Disclosure

This system explicitly displays **`NOT VALIDATED`** (`COMPLETE BUT NOT VALIDATED`) on all dashboards and API responses. Forcing data and historical replay execution are 100% complete. Independent validation requires future acquisition of authoritative sub-daily numerical flood-depth gauge records.
