import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# Chennai Core Bounding Box (South, West, North, East)
BBOX = "13.00,80.18,13.10,80.30"

OVERPASS_URL = "http://overpass-api.de/api/interpreter"

QUERY = f"""
[out:json][timeout:50];
(
  way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified"]({BBOX});
);
out geom;
"""

def download_roads():
    base_dir = Path(__file__).parent.parent.parent / "data"
    roads_dir = base_dir / "roads"
    roads_dir.mkdir(parents=True, exist_ok=True)
    out_file = roads_dir / "chennai_roads.geojson"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    }
    import urllib.request
    import urllib.parse
    print(f"Downloading OSM geom roads for bounding box {BBOX}...")
    try:
        req = urllib.request.Request(OVERPASS_URL, data=QUERY.encode("utf-8"))
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OSMNowcastBot/1.0')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode('utf-8'))
                
        features = []
        for el in data.get("elements", []):
            if el["type"] == "way":
                coords = []
                for pt in el.get("geometry", []):
                    coords.append([pt["lon"], pt["lat"]])
                
                if len(coords) < 2:
                    continue
                    
                tags = el.get("tags", {})
                highway = tags.get("highway", "unknown")
                name = tags.get("name", f"Road {el['id']}")
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    },
                    "properties": {
                        "road_id": str(el["id"]),
                        "name": name,
                        "road_class": highway
                    }
                }
                features.append(feature)
                
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "source": "OpenStreetMap",
                "retrieval_date": datetime.utcnow().isoformat() + "Z",
                "bounding_box": BBOX,
                "feature_count": len(features)
            },
            "features": features
        }
        
        with open(out_file, "w") as f:
            json.dump(geojson, f)
            
        print(f"Success! {len(features)} road segments saved to {out_file}.")
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTPError: {e}")
        print(e.response.text)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching OSM data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_roads()
