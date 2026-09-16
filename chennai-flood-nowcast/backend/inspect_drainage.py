import json
import os
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "data" / "drainage" / "chennai_drainage.geojson"

if not path.exists():
    print("GeoJSON NOT FOUND")
else:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Type: {data.get('type')}")
    features = data.get("features", [])
    print(f"Feature Count: {len(features)}")
    if features:
        print(f"Example properties: {list(features[0].get('properties', {}).keys())}")
        print(f"Example geometry type: {features[0].get('geometry', {}).get('type')}")
        
    types = set()
    for f in features:
        props = f.get("properties", {})
        t = props.get("waterway") or props.get("type") or props.get("drain") or "unknown"
        types.add(t)
    print(f"Feature subtypes found: {types}")
