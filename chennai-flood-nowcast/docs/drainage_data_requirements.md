# STORMWATER DRAINAGE DATA AUDIT & HYDRAULIC REQUIREMENTS

**Dataset Name:** Chennai Storm Water Drains (SWD) Map 2023  
**Data Source:** OpenCity / Greater Chennai Corporation  
**Feature Count:** 10,255 SWD LineStrings  
**Current Operating Mode:** `DRAINAGE_GEOMETRIC_ONLY`  
**Hydraulic Coupling Status:** `UNAVAILABLE`  

---

## 1. Available Feature Attributes Audit

The 10,255 SWD features were ingested, validated, and indexed in a spatial `STRtree` (`pyproj` geodesic WGS84 distance calculator). The attribute fields in the raw dataset were audited:

| Attribute Field | Present in Dataset? | Engineering Parameter Utility |
| :--- | :--- | :--- |
| `geometry` (LineString) | **YES** | Real spatial geometry for proximity diagnostics |
| `name` / `layer` | **YES** | Local identifier |
| `pipe_diameter` | **NO** | Required for pipe cross-sectional flow area |
| `culvert_width_height` | **NO** | Required for box culvert capacity ($Q_{\text{cap}}$) |
| `invert_elevation` | **NO** | Required for gravity slope ($S_0$) and hydraulic head |
| `manning_n` | **NO** | Required for friction roughness loss ($n = 0.013\text{--}0.015$) |
| `flow_direction` | **NO** | Required for directed pipe network routing |
| `outfall_condition` | **NO** | Required for tailwater backwater constraints |

---

## 2. Model Safeguards & Hydraulic Architecture

Because zero hydraulic pipe attributes are available:
1. **Hydraulic Coupling**: Enforced as `UNAVAILABLE`.
2. **Depth Reduction**: Set strictly to **`0.0 cm`**. Proximity to drains does NOT reduce flood depth estimates in `GRID_HYDROLOGY_V1`.
3. **Future Extensibility**: The software architecture (`DrainageCouplingService`) provides explicit placeholders to accept Manning flow capacity ($Q = \frac{1}{n} A R^{2/3} S^{1/2}$) as soon as authoritative municipal engineering surveys become available.
