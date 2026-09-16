# Chennai Drainage Data

### Source Evaluation & Selection
- **Greater Chennai Corporation / OpenCity ("Chennai - Stormwater Drain (SWD) Maps"):** Checked API, found mostly Ward-level PDFs and a huge KML file. Contains geometry but absolutely zero machine-readable engineering properties like diameter or depth.
- **Greater Chennai Corporation ("Chennai Basin Drainage Maps"):** Mostly non-downloadable or PDF based macros/micros.
- **GCC official GIS (Storm_Water_Drain layer):** Closed interactive portal, no direct WFS/REST download available for the raw attributes.
- **Tamil Nadu GIS / TNGIS (Drainage layer):** Requires state login, closed to public bulk attribute download.
- **OpenStreetMap (OSM):** Supplementary source providing waterways, canals, and drains. 

### Original Source
OpenStreetMap / OpenCity metadata approximation.

### Download Date
2026-09-16

### Dataset Name
Chennai Basin Drainage Extract (OSM)

### CRS
EPSG:4326 (WGS84)

### Conversion Process
Requested Overpass API for `waterway=drain|canal|ditch|river` in Chennai area. Transformed the raw OSM JSON elements into standard EPSG:4326 GeoJSON. 

### Available Attributes
- `name` (e.g. Buckingham Canal)
- `waterway` (type of waterway geometry)

### Missing Attributes (UNAVAILABLE)
- `diameter` (UNAVAILABLE)
- `depth` (UNAVAILABLE)
- `capacity` (UNAVAILABLE)
- `slope` (UNAVAILABLE)
- `flow_direction` (UNAVAILABLE)
- `condition` (UNAVAILABLE)
- `nodes/manholes` (UNAVAILABLE)

### Limitations
This is a PARTIAL/ESTIMATED geometry layer. Features are visually accurate to OSM community mapping but lack sufficient hydrodynamic parameters (width, depth, slope, friction) to run a true fully-physical routing algorithm like SWMM. Therefore, the system utilizes them for spatial overlay and heuristic flow rules (Status: PARTIAL/ESTIMATED).
