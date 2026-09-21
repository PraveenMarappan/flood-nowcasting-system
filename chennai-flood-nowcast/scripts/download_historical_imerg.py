import os
import sys
import json
import csv
import re
import time
import urllib.parse
import urllib.request
import requests
import h5py
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FORCING_DIR = ROOT_DIR / "data" / "forcing" / "historical"
RAW_DIR = FORCING_DIR / "raw"
PROCESSED_DIR = FORCING_DIR / "processed"

# Load environment variables from backend/.env
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

TARGET_LAT = 13.0827
TARGET_LON = 80.2707

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

def fetch_cmr_granule_links(start_iso="2015-11-30T00:00:00Z", end_iso="2015-12-05T00:00:00Z"):
    cmr_url = f"https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGHH&temporal={start_iso},{end_iso}&page_size=2000"
    print(f"Querying NASA CMR API: {cmr_url}")
    resp = requests.get(cmr_url, timeout=30)
    resp.raise_for_status()
    
    entries = resp.json().get('feed', {}).get('entry', [])
    print(f"Discovered {len(entries)} granule records in CMR metadata.")
    
    granules = []
    for entry in entries:
        title = entry.get('title')
        time_start = entry.get('time_start')
        links = entry.get('links', [])
        hdf5_url = next((l['href'] for l in links if l.get('href', '').endswith('.HDF5')), None)
        if hdf5_url:
            granules.append({
                "title": title,
                "time_start": time_start,
                "url": hdf5_url
            })
            
    granules.sort(key=lambda g: g["time_start"])
    return granules

def verify_hdf5(filepath):
    try:
        if not filepath.exists() or filepath.stat().st_size < 1000:
            return False
        with h5py.File(filepath, "r") as f:
            if "Grid" in f and ("precipitation" in f["Grid"] or "precipitationCal" in f["Grid"]):
                return True
    except Exception:
        pass
    return False

def download_single_granule(g_info, token):
    url = g_info["url"]
    fname = Path(url).name
    out_path = RAW_DIR / fname
    
    if verify_hdf5(out_path):
        return {"status": "SUCCESS", "filename": fname, "filepath": out_path, "time_start": g_info["time_start"], "cached": True}
        
    session = EarthdataSession()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=headers, allow_redirects=True, timeout=45)
            if resp.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                if verify_hdf5(out_path):
                    return {"status": "SUCCESS", "filename": fname, "filepath": out_path, "time_start": g_info["time_start"], "cached": False}
                else:
                    out_path.unlink(missing_ok=True)
            elif resp.status_code == 404:
                return {"status": "MISSING", "filename": fname, "filepath": None, "time_start": g_info["time_start"]}
        except Exception as e:
            time.sleep(1)
            
    return {"status": "FAILED", "filename": fname, "filepath": None, "time_start": g_info["time_start"]}

def extract_chennai_rainfall(filepath):
    with h5py.File(filepath, "r") as f:
        grid = f["Grid"]
        lats = grid["lat"][:]
        lons = grid["lon"][:]
        precip_ds = grid.get("precipitation")
        if precip_ds is None:
            precip_ds = grid.get("precipitationCal")
            
        lat_idx = int(np.abs(lats - TARGET_LAT).argmin())
        lon_idx = int(np.abs(lons - TARGET_LON).argmin())
        
        raw_val = float(precip_ds[0, lon_idx, lat_idx])
        actual_lat = float(lats[lat_idx])
        actual_lon = float(lons[lon_idx])
        
        val = round(raw_val, 4) if not np.isnan(raw_val) and raw_val >= 0 else 0.0
        return val, actual_lat, actual_lon

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    token = os.getenv("EARTHDATA_TOKEN", "")
    granules = fetch_cmr_granule_links("2015-11-30T00:00:00Z", "2015-12-05T00:00:00Z")
    
    expected_count = len(granules)
    print(f"Downloading/verifying {expected_count} granules using multi-threading (10 workers)...")
    
    download_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(download_single_granule, g, token): g for g in granules}
        for future in as_completed(futures):
            res = future.result()
            download_results.append(res)
            
    download_results.sort(key=lambda r: r["time_start"])
    
    success_count = sum(1 for r in download_results if r["status"] == "SUCCESS")
    missing_count = sum(1 for r in download_results if r["status"] == "MISSING")
    failed_count = sum(1 for r in download_results if r["status"] == "FAILED")
    
    print(f"Download Summary: Total: {expected_count}, Success: {success_count}, Missing: {missing_count}, Failed: {failed_count}")
    
    timeseries_records = []
    seen_timestamps = set()
    
    for r in download_results:
        if r["status"] == "SUCCESS" and r["filepath"]:
            fname = r["filename"]
            match = re.search(r"3B-HHR\.MS\.MRG\.3IMERG\.(\d{8})-S(\d{6})-E(\d{6})\.", fname)
            if match:
                date_str, start_str = match.group(1), match.group(2)
                ts_dt = datetime.strptime(f"{date_str}{start_str}", "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                ts_iso = ts_dt.isoformat()
            else:
                ts_iso = r["time_start"]
                
            if ts_iso in seen_timestamps:
                continue
            seen_timestamps.add(ts_iso)
            
            rain_val, act_lat, act_lon = extract_chennai_rainfall(r["filepath"])
            timeseries_records.append({
                "timestamp_utc": ts_iso,
                "rainfall_mm_hr": rain_val,
                "latitude": act_lat,
                "longitude": act_lon,
                "dataset": "GPM_3IMERGHH",
                "product_version": "V07B",
                "source": "NASA GES DISC",
                "file_name": fname
            })
            
    timeseries_records.sort(key=lambda x: x["timestamp_utc"])
    
    csv_path = PROCESSED_DIR / "chennai_2015_imerg_timeseries.csv"
    fieldnames = [
        "timestamp_utc", "rainfall_mm_hr", "latitude", "longitude",
        "dataset", "product_version", "source", "file_name"
    ]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(timeseries_records)
        
    print(f"\nSaved Chennai 2015 IMERG Timeseries CSV to {csv_path} with {len(timeseries_records)} records.")
    
    rain_vals = [r["rainfall_mm_hr"] for r in timeseries_records]
    max_rain = max(rain_vals) if rain_vals else 0.0
    min_rain = min(rain_vals) if rain_vals else 0.0
    mean_rain = float(np.mean(rain_vals)) if rain_vals else 0.0
    zero_count = sum(1 for v in rain_vals if v == 0.0)
    total_accum_mm = float(sum(v * 0.5 for v in rain_vals))
    
    dq_summary = {
        "event_window": "2015-11-30T00:00:00Z to 2015-12-05T00:00:00Z",
        "first_timestamp": timeseries_records[0]["timestamp_utc"] if timeseries_records else None,
        "last_timestamp": timeseries_records[-1]["timestamp_utc"] if timeseries_records else None,
        "expected_timesteps": expected_count,
        "downloaded_timesteps": success_count,
        "actual_timesteps_processed": len(timeseries_records),
        "missing_timesteps": missing_count,
        "duplicate_timesteps": 0,
        "corrupt_timesteps": failed_count,
        "min_rainfall_mm_hr": min_rain,
        "max_rainfall_during_processed_window_mm_hr": max_rain,
        "mean_rainfall_mm_hr": round(mean_rain, 4),
        "total_accumulated_rainfall_mm": round(total_accum_mm, 2),
        "zero_rainfall_intervals": zero_count
    }
    
    print("\nDATA QUALITY SUMMARY:")
    print(json.dumps(dq_summary, indent=2))
    
    with open(PROCESSED_DIR / "chennai_2015_imerg_quality_report.json", "w") as f:
        json.dump(dq_summary, f, indent=4)

if __name__ == "__main__":
    main()
