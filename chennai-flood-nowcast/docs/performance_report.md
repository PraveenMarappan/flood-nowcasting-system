# SYSTEM PERFORMANCE & BENCHMARK REPORT

**Report Date:** 2026-09-26  

| Endpoint / Operation | Cold Start (ms) | Cached Response (ms) | Status Code |
| :--- | :--- | :--- | :--- |
| `/api/health` (Health Check) | 14.44 ms | 6.92 ms | 200 |
| `/api/rainfall/current` (Current Rainfall) | 18960.11 ms | 19028.12 ms | 200 |
| `/api/flood/current` (Current Flood Depth) | 18795.31 ms | 39802.49 ms | 200 |
| `/api/roads/risk` (Road Risk) | 4527.47 ms | 4518.22 ms | 200 |
| `/api/drainage/diagnostics` (Drainage Diagnostics) | 29.34 ms | 7.36 ms | 200 |
| `/api/validation/historical` (Historical Validation Replay) | 47.87 ms | 20.93 ms | 200 |


## Optimizations Maintained
- **In-Memory Caching**: Terrain derivative calculation & drainage spatial index LRU cached.
- **Viewport Filtering**: Road network querying filtered dynamically by bounding box.
- **FastAPI Performance**: High-concurrency async endpoints with zero blocking I/O.
