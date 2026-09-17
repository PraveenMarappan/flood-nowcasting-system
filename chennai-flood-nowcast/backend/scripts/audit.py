import json
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
geojson_path = BASE_DIR / "data" / "validation" / "processed" / "chennai_validation_normalized.geojson"

def main():
    with open(geojson_path, "r") as f:
        data = json.load(f)
        
    sources = defaultdict(lambda: {
        'count': 0,
        'event': set(),
        'event_year': set(),
        'with_depth': 0,
        'without_depth': 0,
        'flood_status': 0,
        'unknown_status': 0,
        'timestamp': set(),
        'bounds': {'min_lat': 90, 'max_lat': -90, 'min_lon': 180, 'max_lon': -180}
    })
    
    for feat in data['features']:
        props = feat['properties']
        geom = feat['geometry']
        source = props['source']
        
        sources[source]['count'] += 1
        
        if props.get('observed_depth_cm') is not None:
            sources[source]['with_depth'] += 1
        else:
            sources[source]['without_depth'] += 1
            
        if props.get('observed_status') == 'FLOODED':
            sources[source]['flood_status'] += 1
        elif props.get('observed_status') == 'UNKNOWN':
            sources[source]['unknown_status'] += 1
            
        sources[source]['event'].add(props.get('event'))
        sources[source]['event_year'].add(props.get('event_year'))
        sources[source]['timestamp'].add(props.get('timestamp_available'))
        
        lat = geom['coordinates'][1]
        lon = geom['coordinates'][0]
        
        sources[source]['bounds']['min_lat'] = min(sources[source]['bounds']['min_lat'], lat)
        sources[source]['bounds']['max_lat'] = max(sources[source]['bounds']['max_lat'], lat)
        sources[source]['bounds']['min_lon'] = min(sources[source]['bounds']['min_lon'], lon)
        sources[source]['bounds']['max_lon'] = max(sources[source]['bounds']['max_lon'], lon)
        
    for k, v in sources.items():
        v['event'] = list(v['event'])
        v['event_year'] = list(v['event_year'])
        v['timestamp'] = list(v['timestamp'])
        
    print(json.dumps(sources, indent=2))

if __name__ == "__main__":
    main()
