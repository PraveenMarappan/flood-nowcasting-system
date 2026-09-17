import os
import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from math import isclose

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "validation" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "validation" / "processed"

def determine_event(filename_or_schema):
    identifier = filename_or_schema.lower()
    if '2015' in identifier:
        return "Chennai_2015", 2015
    return "UNKNOWN", None

def get_kml_namespace(element):
    if element.tag.startswith("{"):
        return element.tag.split("}")[0] + "}"
    return ""

def process_kml(filepath):
    features = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        ns = get_kml_namespace(root)
        
        # Try to find a schema name for event mapping
        schema_name = ""
        for schema in root.iter(f"{ns}Schema"):
            schema_name = schema.attrib.get('name', '')
            break
            
        event, event_year = determine_event(filepath.name + " " + schema_name)
        
        for placemark in root.iter(f"{ns}Placemark"):
            coords_text = None
            point = placemark.find(f".//{ns}Point")
            if point is not None:
                coords_elem = point.find(f"{ns}coordinates")
                if coords_elem is not None and coords_elem.text:
                    coords_text = coords_elem.text.strip()
                    
            if not coords_text:
                continue
                
            parts = coords_text.split(',')
            if len(parts) >= 2:
                try:
                    lon, lat = float(parts[0]), float(parts[1])
                except ValueError:
                    continue
            else:
                continue
                
            properties = {
                "source": filepath.name,
                "event": event,
                "event_year": event_year,
                "timestamp_available": False,
                "original_attributes": {}
            }
            
            # Extract attributes
            depth = None
            ext_data = placemark.find(f"{ns}ExtendedData")
            if ext_data is not None:
                for sd in ext_data.iter(f"{ns}SimpleData"):
                    name = sd.attrib.get('name', '')
                    val = sd.text if sd.text else ''
                    properties["original_attributes"][name] = val
                    if name.upper() == 'DEPTH':
                        try:
                            # assuming inches based on schema name, we convert to cm if needed, but let's just store safely
                            depth = float(val)
                            # Actually schema was chennai_flood_inundation_inches, if in inches, cm = depth * 2.54.
                            # We will store observed_depth_cm if it's likely inches, or just store the raw value if unknown.
                            # For safety, let's keep it as is, or attempt to convert if schema explicitly says inches.
                        except:
                            pass
                            
            if 'inches' in schema_name.lower() and depth is not None:
                properties["observed_depth_cm"] = depth * 2.54
            elif depth is not None:
                properties["observed_depth_cm"] = depth
                
            properties["observed_status"] = "FLOODED" if (depth is not None and depth > 0) or 'stagnant' in schema_name.lower() or 'flood' in schema_name.lower() else "UNKNOWN"
            
            # Source feature ID
            properties["source_feature_id"] = properties["original_attributes"].get("OBJECTID", properties["original_attributes"].get("F_ID", None))
            
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": properties
            })
    except Exception as e:
        print(f"Error parsing KML {filepath.name}: {e}")
        
    return features

def is_duplicate(feat, existing_features, tol=1e-5):
    lon1, lat1 = feat["geometry"]["coordinates"]
    for ex in existing_features:
        lon2, lat2 = ex["geometry"]["coordinates"]
        if isclose(lon1, lon2, abs_tol=tol) and isclose(lat1, lat2, abs_tol=tol):
            return True
    return False

def main():
    if not RAW_DIR.exists():
        print("Raw directory not found.")
        return
        
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    all_features = []
    
    total_records_read = 0
    valid_coords = 0
    invalid_coords = 0
    duplicate_records = 0
    
    records_with_depth = 0
    records_with_event = 0
    
    sources = set()
    
    for filepath in RAW_DIR.glob("*"):
        if filepath.suffix.lower() == '.kml':
            feats = process_kml(filepath)
            sources.add(filepath.name)
        else:
            feats = [] # we can extend to CSV if needed
            
        total_records_read += len(feats)
        for f in feats:
            lat = f["geometry"]["coordinates"][1]
            lon = f["geometry"]["coordinates"][0]
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                invalid_coords += 1
                continue
                
            if is_duplicate(f, all_features):
                duplicate_records += 1
                continue
                
            valid_coords += 1
            all_features.append(f)
            
            if f["properties"].get("observed_depth_cm") is not None:
                records_with_depth += 1
            if f["properties"].get("event") != "UNKNOWN":
                records_with_event += 1

    # bounds
    if len(all_features) > 0:
        lats = [f["geometry"]["coordinates"][1] for f in all_features]
        lons = [f["geometry"]["coordinates"][0] for f in all_features]
        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
    else:
        bounds = []
        
    out_file = PROCESSED_DIR / "chennai_validation_normalized.geojson"
    with open(out_file, 'w') as f:
        json.dump({
            "type": "FeatureCollection",
            "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
            "features": all_features
        }, f, indent=2)
        
    print("=== Validation Data Processing Report ===")
    print(f"Sources processed: {list(sources)}")
    print(f"Total entries reading: {total_records_read}")
    print(f"Valid coordinates: {valid_coords}")
    print(f"Invalid coordinates: {invalid_coords}")
    print(f"Duplicates excluded: {duplicate_records}")
    print(f"Total normalized features: {len(all_features)}")
    print(f"Features with depth data: {records_with_depth}")
    print(f"Features without depth data: {len(all_features) - records_with_depth}")
    print(f"Features with recognized event: {records_with_event}")
    print(f"Features mapped as UNKNOWN event: {len(all_features) - records_with_event}")
    print(f"Spatial Bounds [minLat, minLon, maxLat, maxLon]: {bounds}")
    print(f"Coordinate Reference System (CRS): urn:ogc:def:crs:OGC:1.3:CRS84")
    print(f"Output saved to -> {out_file.relative_to(BASE_DIR)}")

if __name__ == "__main__":
    main()
