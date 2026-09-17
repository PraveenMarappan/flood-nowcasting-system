import os
import sys
import json
from datetime import datetime
from pathlib import Path
import numpy as np

BBOX = "13.00,80.18,13.10,80.30"

def generate_roads():
    base_dir = Path(__file__).parent.parent.parent / "data"
    roads_dir = base_dir / "roads"
    roads_dir.mkdir(parents=True, exist_ok=True)
    out_file = roads_dir / "chennai_roads.geojson"
    
    print(f"Generating synthetic structured OSM road graph over {BBOX} as Overpass API fallback...")
    
    lat_min, lng_min, lat_max, lng_max = 13.00, 80.18, 13.10, 80.30
    
    # Generate 50 vertical and 50 horizontal structured roads
    lat_steps = np.linspace(lat_min, lat_max, 50)
    lng_steps = np.linspace(lng_min, lng_max, 50)
    
    features = []
    
    road_id = 1
    
    # Horizontal Roads
    for i, lat in enumerate(lat_steps):
        coords = [[lng_min, lat], [lng_max, lat]]
        rc = "residential"
        if i % 10 == 0: rc = "primary"
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "road_id": f"syn_h_{road_id}",
                "name": f"Horizontal Street #{road_id}",
                "road_class": rc
            }
        }
        features.append(feature)
        road_id += 1
        
    # Vertical Roads
    for i, lng in enumerate(lng_steps):
        coords = [[lng, lat_min], [lng, lat_max]]
        rc = "residential"
        if i % 10 == 0: rc = "primary"
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "road_id": f"syn_v_{road_id}",
                "name": f"Vertical Avenue #{road_id}",
                "road_class": rc
            }
        }
        features.append(feature)
        road_id += 1
        
    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "OpenStreetMap Fallback (Synthetic Grid Generator)",
            "retrieval_date": datetime.utcnow().isoformat() + "Z",
            "bounding_box": BBOX,
            "feature_count": len(features),
            "limitations": "Generated systematically to simulate OSM topology because Overpass server returned 406 Not Acceptable globally mapping this IP block."
        },
        "features": features
    }
    
    with open(out_file, "w") as f:
        json.dump(geojson, f)
        
    print(f"Success! {len(features)} road segments saved to {out_file}.")

if __name__ == "__main__":
    generate_roads()
