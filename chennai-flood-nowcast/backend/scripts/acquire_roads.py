"""
Acquire Real OpenStreetMap Road Data for Chennai

Downloads machine-readable road vectors from OpenStreetMap Overpass API.
Preserves raw data in data/roads/raw/ and normalized GeoJSON in data/roads/processed/.
"""

import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# Expanded Bounding Box covering Greater Chennai Metropolitan Area
# South, West, North, East (min_lat, min_lon, max_lat, max_lon)
BBOX = "12.88,80.10,13.20,80.32"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
]

# Query for motorways, trunks, primaries, secondaries, tertiaries, residentials, and unclassified roads
QUERY = f"""
[out:json][timeout:120];
(
  way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified"]({BBOX});
);
out geom;
"""

def acquire_roads():
    project_root = Path(__file__).resolve().parent.parent.parent
    raw_dir = project_root / "data" / "roads" / "raw"
    processed_dir = project_root / "data" / "roads" / "processed"
    legacy_dir = project_root / "data" / "roads"
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    raw_file = raw_dir / "chennai_osm_roads_raw.json"
    processed_file = processed_dir / "chennai_roads.geojson"
    legacy_file = legacy_dir / "chennai_roads.geojson"
    
    print("=" * 60)
    print("ACQUIRING REAL OPENSTREETMAP ROADS FOR CHENNAI")
    print("=" * 60)
    print(f"Bounding box: {BBOX}")
    print()
    
    data = None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChennaiFloodNowcast/2.0',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    for endpoint in OVERPASS_ENDPOINTS:
        print(f"Trying Overpass endpoint: {endpoint}...")
        try:
            req = urllib.request.Request(endpoint, data=QUERY.encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=120) as response:
                raw_text = response.read().decode('utf-8')
                data = json.loads(raw_text)
                
                # Save raw JSON
                with open(raw_file, "w", encoding="utf-8") as f:
                    f.write(raw_text)
                print(f"  Successfully fetched raw data from {endpoint}")
                print(f"  Raw file written to: {raw_file}")
                break
        except Exception as e:
            print(f"  Failed from {endpoint}: {e}")
            time.sleep(2)
            
    if not data or "elements" not in data:
        print("ERROR: Could not fetch real road data from any Overpass endpoint.")
        sys.exit(1)
        
    elements = data.get("elements", [])
    print(f"Fetched {len(elements)} raw OSM elements.")
    
    # Process into clean GeoJSON
    features = []
    for el in elements:
        if el.get("type") != "way":
            continue
            
        geom = el.get("geometry", [])
        if len(geom) < 2:
            continue
            
        # Extract coordinates in [lon, lat] format (EPSG:4326)
        coords = [[pt["lon"], pt["lat"]] for pt in geom]
        
        tags = el.get("tags", {})
        highway = tags.get("highway", "unclassified")
        name = tags.get("name")
        if not name:
            name = "Unnamed road"
            
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "road_id": str(el["id"]),
                "road_name": name,
                "road_type": highway,
                "oneway": tags.get("oneway"),
                "lanes": tags.get("lanes"),
                "maxspeed": tags.get("maxspeed"),
                "surface": tags.get("surface"),
                "source": "OpenStreetMap",
                "data_status": "REAL"
            }
        }
        features.append(feature)
        
    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "OpenStreetMap",
            "retrieval_date": datetime.utcnow().isoformat() + "Z",
            "bounding_box": BBOX,
            "feature_count": len(features),
            "geometry_type": "LineString (EPSG:4326)",
            "data_status": "REAL"
        },
        "features": features
    }
    
    # Write processed GeoJSON to both processed and legacy root path for seamless backend loading
    with open(processed_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    print(f"  Processed GeoJSON saved to: {processed_file}")
    
    with open(legacy_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    print(f"  Legacy GeoJSON updated:  {legacy_file}")
    
    print()
    print("=" * 60)
    print(f"SUCCESS: {len(features)} REAL CHENNAI ROAD FEATURES ACQUIRED")
    print("=" * 60)

if __name__ == "__main__":
    acquire_roads()
