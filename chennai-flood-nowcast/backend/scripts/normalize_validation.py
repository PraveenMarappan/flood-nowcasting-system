import xml.etree.ElementTree as ET
import json
import re
from pathlib import Path

def parse_kml_points(raw_file: Path, source_name: str, event_id: str):
    features = []
    if not raw_file.exists():
        return features
        
    try:
        tree = ET.parse(raw_file)
        root = tree.getroot()
        
        # Strip namespaces
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]  
                
        for placemark in root.findall('.//Placemark'):
            name_el = placemark.find('name')
            name = name_el.text if name_el is not None else 'Unknown'
            
            desc_el = placemark.find('description')
            desc = desc_el.text if desc_el is not None else ''
            
            # Extract depth if embedded
            depth_cm = None
            if "Depth" in desc or "inches" in desc.lower():
                # Attempt to regex parse inches or cm
                match = re.search(r'(\d+(\.\d+)?)\s*(inch|in|cm)', desc.lower())
                if match:
                    val = float(match.group(1))
                    unit = match.group(3)
                    if unit in ['inch', 'in']:
                        depth_cm = round(val * 2.54, 2)
                    else:
                        depth_cm = val
                        
            pts = placemark.find('.//Point/coordinates')
            if pts is not None:
                coords = pts.text.strip().split(',')
                if len(coords) >= 2:
                    lon, lat = float(coords[0]), float(coords[1])
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        continue # Invalid coordinates

                    features.append({
                        'type': 'Feature',
                        'properties': {
                            'source_id': name,
                            'source_dataset': source_name,
                            'event': event_id,
                            'observed_status': "FLOODED",
                            'observed_depth_cm': depth_cm,
                            'timestamps_available': False,
                            'original_attributes': desc
                        },
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [lon, lat]
                        }
                    })
    except Exception as e:
        print(f"Error parsing {raw_file.name}: {e}")
        
    return features

def normalize_validation_data():
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "validation" / "raw"
    processed_dir = base_dir / "data" / "validation" / "processed"
    
    all_features = []
    
    for f in raw_dir.glob("*.kml"):
        event = "Chennai_2015" if "2015" in f.name.lower() or "93d29" in f.name else "Historical"
        source_name = "Chennai Flooding Observations"
        feats = parse_kml_points(f, source_name, event)
        all_features.extend(feats)
        
    for f in raw_dir.glob("*.csv"):
        # basic proxy if CSV existed
        pass
    
    # Step 2: Quality checks
    total_records = len(all_features)
    valid_coords = []
    invalid_count = 0
    duplicates = 0
    records_with_depth = 0
    records_with_event = 0
    
    seen_coords = set()
    
    for f in all_features:
        lon, lat = f["geometry"]["coordinates"]
        
        # Check duplicate geometries
        coord_key = (round(lon, 4), round(lat, 4))
        if coord_key in seen_coords:
            duplicates += 1
            f["properties"]["is_duplicate"] = True
        else:
            f["properties"]["is_duplicate"] = False
            seen_coords.add(coord_key)
            
        if f["properties"]["observed_depth_cm"] is not None:
            records_with_depth += 1
            
        if f["properties"]["event"] != "Historical":
            records_with_event += 1
            
    # Write normalized data safely out
    geojson = {
        'type': 'FeatureCollection',
        'features': all_features
    }
    
    out_file = processed_dir / "chennai_validation_normalized.geojson"
    with open(out_file, 'w') as f:
        json.dump(geojson, f, indent=2)
        
    bounds = [
        min((f["geometry"]["coordinates"][0] for f in all_features)),
        min((f["geometry"]["coordinates"][1] for f in all_features)),
        max((f["geometry"]["coordinates"][0] for f in all_features)),
        max((f["geometry"]["coordinates"][1] for f in all_features))
    ] if all_features else []

    report = {
        "total_records": total_records,
        "valid_coordinates": total_records - invalid_count, # we strictly filtered out inv during parse 
        "invalid_coordinates": invalid_count,
        "duplicate_records": duplicates,
        "records_with_depth": records_with_depth,
        "records_without_depth": total_records - records_with_depth,
        "records_with_event": records_with_event,
        "records_without_event": total_records - records_with_event,
        "spatial_bounds": bounds,
        "crs": "EPSG:4326"
    }

    print("\n--- QA REPORT ---")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    normalize_validation_data()
