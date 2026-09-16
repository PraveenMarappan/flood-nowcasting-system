# SIH26085 Final Technical Audit Report (Revised)

## 1. Current Architecture
The architecture cleanly isolates the mathematical calculations within specific services. The calculations enforce strict dimensional consistency without exposing misleadingly scaled data as 'observed'. The model enforces physical units over specific timesteps.

## 2. Actual Rainfall Calculation & Runoff
- `rainfall_rate_mm_hr` fetched live from NASA GPM IMERG.
- `runoff_rate_mm_hr` = `rainfall_rate_mm_hr * C` (where `C=0.8` is configured in `runoff_service.py` as a HEURISTIC — NOT CALIBRATED factor).

## 3. Topographical Influences
A dimensionless multiplier `terrain_factor` is assigned relative to elevation (HEURISTIC — NOT CALIBRATED):
- `< 5m` -> 1.8
- `< 15m` -> 1.2
- `>= 15m` -> 0.5

## 4. Flood-Depth Calculation
Dimensional consistency is enforced.
- **Timestep (Δt):** 1.0 hr (accumulation_interval_hours)
- **Runoff Depth:** `runoff_rate_mm_hr * Δt * 0.1 = runoff_depth_cm`
- **Output:** `modelled_surface_depth_cm = runoff_depth_cm * terrain_factor`

The codebase avoids arbitrary static bounds (`5cm` floors) outside physical inputs. Flow drops natively to 0 when zero rainfall/runoff inputs are received.

## 5. Actual Risk Thresholds
Classified conditionally upon the physical `modelled_surface_depth_cm`:
- `>20cm`: CRITICAL
- `>10cm`: HIGH
- `>3cm`: MODERATE
- `>0.1cm`: LOW

## 6. Actual Forecast Calculation
A baseline heuristic recession timeline tracks volumetric decay smoothly via multipliers (0.9, 0.7, 0.5...), without masquerading as an AI/ML forecast.

## 7. Configuration States
- **Drainage:** PARTIAL / NOT VERIFIED (Unused in mathematical computation implicitly).
- **Validation:** NOT_AVAILABLE
- **Calibration:** NOT_CALIBRATED
- **Data Confidence:** HIGH/MEDIUM/LOW representing infrastructural dataset existence (NOT statistical predictive certainty).

## 8. Summary of Revisions in v1.1
- Eliminated artificial disconnected 0.8 scalers.
- Tied the `runoff_service` linearly into the physical accumulation block in `flood_model_service.py`.
- Formally modeled a static continuous variable mapping step `Δt`.
- Relocated risk threshold bands purely around cm-depths.
