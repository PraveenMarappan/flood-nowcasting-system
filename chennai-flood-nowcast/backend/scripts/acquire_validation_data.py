import requests
import json
import os
import urllib.parse
from pathlib import Path

def acquire_validation():
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "validation" / "raw"
    processed_dir = base_dir / "data" / "validation" / "processed"
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    inventory = {
        "status": "ACQUIRED",
        "datasets": []
    }
    
    # 1. Search OpenCity CKAN for validation datasets
    print("Searching OpenCity CKAN API for Chennai Floods/Inundation Data...")
    
    # Common queries
    queries = [
        "Chennai Inundation Points",
        "Chennai Floods 2015",
        "Chennai Flood Hazard Zones Map",
        "Return Period Flow Maps",
        "Chennai Flooding Data"
    ]
    
    seen_urls = set()
    
    for q in queries:
        url = f"https://data.opencity.in/api/3/action/package_search?q={urllib.parse.quote(q)}"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            results = data.get("result", {}).get("results", [])
            print(f"Query '{q}' found {len(results)} packages.")
            
            for pkg in results:
                for res in pkg.get("resources", []):
                    # Dedup
                    if res.get("url") in seen_urls:
                        continue
                    seen_urls.add(res.get("url"))
                    
                    format_type = res.get("format", "").upper()
                    if format_type in ["KML", "GEOJSON", "JSON", "SHP", "CSV"]:
                        
                        title = res.get("name", pkg.get("title", "Unknown"))
                        
                        # Data classification heuristics based on titles
                        data_type = "SIMULATED"
                        if "inundation point" in title.lower() or "flood 2015" in title.lower() or "waterlogging" in title.lower():
                            data_type = "OBSERVED DATA"
                        elif "hazard" in title.lower() or "return period" in title.lower():
                            data_type = "MODELLED DATA"
                        
                        ds = {
                            "source": "OpenCity",
                            "title": title,
                            "url": res.get("url"),
                            "format": format_type,
                            "data_type": data_type,
                            "event_date": "2015" if "2015" in title else "Historical",
                            "retrieval_date": "2026-09-17",
                            "observed_variables": {
                                "depth_available": "inches" in title.lower() or "depth" in title.lower(),
                                "flood_extent_available": "zone" in title.lower() or "map" in title.lower(),
                                "timestamps_available": False
                            },
                            "raw_file": None,
                            "feature_count": 0
                        }
                        inventory["datasets"].append(ds)
                        
                        # Only strictly download and cache OBSERVED DATA (Points/Polygons)
                        if data_type == "OBSERVED DATA":
                            try:
                                print(f"Downloading {ds['title']}...")
                                dl_r = requests.get(ds["url"], timeout=15)
                                filename = ds["url"].split("/")[-1]
                                if not filename or "." not in filename:
                                    filename = ds["title"].replace(" ", "_") + f".{format_type.lower()}"
                                    
                                filepath = raw_dir / filename
                                with open(filepath, "wb") as f:
                                    f.write(dl_r.content)
                                ds["raw_file"] = str(filepath.name)
                                
                                content_str = dl_r.text
                                if format_type == "KML":
                                    ds["feature_count"] = content_str.count("<Placemark>")
                                    ds["geometry_type"] = "Polygon" if "<Polygon>" in content_str else ("Point" if "<Point>" in content_str else "Unknown")
                                elif format_type == "CSV":
                                    ds["feature_count"] = max(0, len(content_str.split('\n')) - 1)
                                    ds["geometry_type"] = "Point"
                            except Exception as e:
                                print(f"Failed to download OBSERVED {ds['title']}: {e}")
                        else:
                            ds["raw_file"] = "SKIPPED_LARGE_MODELLED_DATASET"
                            ds["feature_count"] = -1
                            ds["geometry_type"] = "Unknown"
                            
        except Exception as e:
            print(f"Failed to execute query {q}: {e}")
        
    # Write inventory
    inventory_path = base_dir / "data" / "validation" / "validation_data_inventory.json"
    with open(inventory_path, "w") as f:
        json.dump(inventory, f, indent=4)
        
    print(f"\nInventory saved to {inventory_path}")
    print(json.dumps(inventory, indent=2))

if __name__ == "__main__":
    acquire_validation()
