import requests
import json
import os
from pathlib import Path

def acquire_drainage():
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "drainage" / "raw"
    processed_dir = base_dir / "data" / "drainage" / "processed"
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    inventory = {
        "status": "INITIALIZED",
        "datasets": []
    }
    
    # 1. Search OpenCity CKAN
    print("Searching OpenCity CKAN API...")
    url = "https://data.opencity.in/api/3/action/package_search?q=Chennai%20Stormwater%20Drains"
    
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        
        results = data.get("result", {}).get("results", [])
        print(f"Found {len(results)} packages.")
        
        for pkg in results:
            for res in pkg.get("resources", []):
                format_type = res.get("format", "").upper()
                if format_type in ["KML", "GEOJSON", "JSON", "SHP"]:
                    ds = {
                        "source": "OpenCity",
                        "title": res.get("name"),
                        "url": res.get("url"),
                        "format": format_type,
                        "retrieval_date": "2026-09-17",
                        "available_engineering_parameters": [],
                        "missing_engineering_parameters": [
                            "pipe diameter", "capacity", "slope", "invert elevation", 
                            "roughness", "flow direction", "condition", "manhole depth"
                        ],
                        "is_verified_engineering_infrastructure": False,
                        "raw_file": None,
                        "feature_count": 0
                    }
                    inventory["datasets"].append(ds)
                    
                    # Download it
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
                        
                        # Basic inspection (naive count for KML)
                        content_str = dl_r.text
                        if format_type == "KML":
                            count = content_str.count("<Placemark>")
                            ds["feature_count"] = count
                    except Exception as e:
                        print(f"Failed to download {ds['title']}: {e}")
                        
    except Exception as e:
        print(f"Failed to search OpenCity API: {e}")
        
    # Write inventory
    inventory_path = base_dir / "data" / "drainage" / "drainage_data_inventory.json"
    with open(inventory_path, "w") as f:
        json.dump(inventory, f, indent=4)
        
    print(f"\nInventory saved to {inventory_path}")
    print(json.dumps(inventory, indent=2))

if __name__ == "__main__":
    acquire_drainage()
