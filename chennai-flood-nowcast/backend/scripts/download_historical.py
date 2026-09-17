import os
import json
import requests
import datetime
import h5py
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FORCING_DIR = BASE_DIR / "data" / "forcing" / "historical"
RAW_DIR = FORCING_DIR / "raw"

# Chennai Coordinates
TARGET_LAT = 13.0827
TARGET_LON = 80.2707

def find_nearest_indices(lats, lons, target_lat, target_lon):
    lat_idx = (np.abs(lats - target_lat)).argmin()
    lon_idx = (np.abs(lons - target_lon)).argmin()
    return lat_idx, lon_idx

def download_and_verify():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    # NASA Granule Link
    download_link = "https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGHH.07/2015/334/3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
    file_name = "3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5"
    out_path = RAW_DIR / file_name
    
    token = os.getenv("EARTHDATA_TOKEN", "")
    
    if not out_path.exists():
        import urllib.parse
        
        class EarthdataSession(requests.Session):
            def rebuild_auth(self, prepared_request, response):
                headers = prepared_request.headers
                url = prepared_request.url
                if 'Authorization' in headers:
                    original_parsed = urllib.parse.urlparse(response.request.url)
                    redirect_parsed = urllib.parse.urlparse(url)
                    if original_parsed.hostname != redirect_parsed.hostname and \
                    redirect_parsed.hostname != 'urs.earthdata.nasa.gov' and \
                    not original_parsed.hostname.startswith('urs.earthdata') and \
                    "nasa.gov" not in redirect_parsed.hostname and \
                    "cloudfront.net" not in redirect_parsed.hostname:
                        del headers['Authorization']
                return

        my_session = EarthdataSession()
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Downloading {file_name}...")
        resp = my_session.get(download_link, headers=headers, allow_redirects=True, timeout=60)
        
        if resp.status_code == 200:
            with open(out_path, "wb") as f:
                f.write(resp.content)
            print("Download successful.")
        else:
            print(f"Failed to download: {resp.status_code}")
            return False
            
    print("Verifying data...")
    val = None
    try:
        with h5py.File(out_path, 'r') as f:
            grid = f['Grid']
            lats = grid['lat'][:]
            lons = grid['lon'][:]
            precip_ds = grid.get('precipitation')
            if precip_ds is None:
                precip_ds = grid.get('precipitationCal')
                
            precip = precip_ds[0, :, :]
            lat_idx, lon_idx = find_nearest_indices(lats, lons, TARGET_LAT, TARGET_LON)
            val = precip[lon_idx, lat_idx]
            
            # Print timestamp availability if present
            # We know it's representing 2015-11-30T00:00:00 to 00:29:59
            print(f"Extracted rainfall at {TARGET_LAT}, {TARGET_LON} = {val} mm/hr")
    except Exception as e:
        print(f"Verification Failed: {e}")
        return False
        
    # Generate Inventory
    inventory = {
        "source": "NASA/GES DISC",
        "dataset": "GPM IMERG Final Precipitation L3 Half Hourly (GPM_3IMERGHH)",
        "version": "V07B",
        "temporal_resolution": "Half-Hourly (30 minutes)",
        "spatial_resolution": "0.1 degree x 0.1 degree",
        "units": "mm/hr",
        "coverage": "Global (-90 -180 to 90 180)",
        "event_period": "2015-11-30T00:00:00Z to 2015-12-05T00:00:00Z (and beyond)",
        "file_format": "HDF5 (.HDF5)",
        "download_access_status": "Accessible / Verified",
        "provenance": {
            "origin_link": "https://data.gesdisc.earthdata.nasa.gov/",
            "verified_sample": file_name,
            "data_key": "precipitation"
        }
    }
    
    with open(FORCING_DIR / "historical_rainfall_inventory.json", "w") as f:
        json.dump(inventory, f, indent=4)
        
    print("Inventory created.")
    return True
    
if __name__ == "__main__":
    download_and_verify()
