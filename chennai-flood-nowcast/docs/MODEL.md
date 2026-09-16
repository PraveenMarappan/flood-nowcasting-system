# Baseline Urban Flood Nowcasting Model (baseline-v1)

This document describes the baseline heuristic model implemented for the SIH prototype.

## Limitations & Scope
This model is a **transparent baseline prototype**. It calculates a heuristic surface-water depth estimation.
It explicitly does NOT include:
- physical infiltration
- depression storage or soil moisture dynamics
- evaporation
- drainage discharge (pipe volumes, invert levels, strict hydraulic gradients)
- observed truthed physical water levels

## Mathematical Formulation

For a rainfall intensity R sustained for Δt hours, the baseline runoff accumulation is R × C × Δt.

This models a dimensionless 1.0 hour baseline assumption, NOT an observed one-hour rainfall accumulation exactly:

1. **Rainfall Intensity (R):** Live from NASA GPM in `mm/hr`.
2. **Runoff Coefficient (C):** A dimensionless parameter, `C = 0.8` (HEURISTIC — NOT CALIBRATED).
3. **Runoff Rate (Q_r):** 
   `Q_r = R × C`  `[mm/hr]`
4. **Accumulated Runoff Depth (D_r):**
   `D_r = Q_r × Δt` `[mm]`
5. **Depth Conversion (D_r_cm):**
   `D_r_cm = D_r × 0.1` `[cm]`
6. **Terrain Adjustment (F_terrain):**
   A scalable dimensionless mapping based on absolute DEM pixels (HEURISTIC — NOT CALIBRATED):
   - `elevation < 5 m` -> `1.8`
   - `elevation < 15 m` -> `1.2`
   - `elevation >= 15 m` -> `0.5`
7. **Modelled Surface Depth (D_model_cm):**
   `D_model_cm = D_r_cm × F_terrain`

**Combined Equation:**
`D_model_cm = R × C × Δt × 0.1 × F_terrain`

## Future Development (Mode B)
This architecture is structurally designed to couple with municipal stormwater pipe data. When validated GIS properties (pipe capacities, slopes, roughness) from local bodies are acquired, this static model will transition to a coupled hydraulic solver subtracting verifiable volume dynamically.
