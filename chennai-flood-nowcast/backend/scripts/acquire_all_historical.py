import os
import sys
import json
import csv
import time
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import h5py
import numpy as np
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))

load_dotenv(backend_dir / ".env")

RAW_DIR = project_root / "data" / "forcing" / "historical" / "raw"
PROCESSED_DIR = project_root / "data" / "forcing" / "historical" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CHENNAI_LAT = 13.0827
CHENNAI_LON = 80.2707

EARTHDATA_TOKEN = os.getenv("EARTHDATA_TOKEN", "")
EARTHDATA_USER = os.getenv("EARTHDATA_USERNAME", "")
EARTHDATA_PASS = os.getenv("EARTHDATA_PASSWORD", "")

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

def create_authenticated_session():
    session = EarthdataSession()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 429])
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if EARTHDATA_TOKEN:
        session.headers.update({"Authorization": f"Bearer {EARTHDATA_TOKEN}"})
    elif EARTHDATA_USER and EARTHDATA_PASS:
        session.auth = (EARTHDATA_USER, EARTHDATA_PASS)
    return session

def find_nearest_indices(lats, lons, target_lat, target_lon):
    lat_idx = (np.abs(lats - target_lat)).argmin()
    lon_idx = (np.abs(lons - target_lon)).argmin()
    return lat_idx, lon_idx

def is_valid_h5(file_path):
    if not file_path.exists() or file_path.stat().st_size < 100000:
        return False
    try:
        with h5py.File(file_path, "r") as f:
            if "Grid" in f:
                grid = f["Grid"]
                if "lat" in grid and "lon" in grid:
                    return True
    except Exception:
        return False
    return False

def search_cmr_granules():
    url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {
        "short_name": "GPM_3IMERGHH",
        "temporal[]": "2015-11-30T00:00:00Z,2015-12-05T00:30:00Z",
        "page_size": 300
    }
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            entries = r.json().get("feed", {}).get("entry", [])
            
            granule_map = {}
            for entry in entries:
                download_url = None
                for link in entry.get("links", []):
                    href = link.get("href", "")
                    if href.endswith(".HDF5") and "fedsearch" in link.get("rel", ""):
                        download_url = href
                        break
                    elif href.endswith(".HDF5") and not download_url:
                        download_url = href
                if download_url:
                    filename = download_url.split("/")[-1]
                    granule_map[filename] = download_url
            return granule_map
        except Exception as e:
            print(f"CMR search attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return {}

def generate_expected_timesteps():
    start = datetime(2015, 11, 30, 0, 0, tzinfo=timezone.utc)
    end = datetime(2015, 12, 5, 0, 0, tzinfo=timezone.utc)
    current = start
    timesteps = []
    while current <= end:
        timesteps.append(current)
        current += timedelta(minutes=30)
    return timesteps

def build_filename_for_dt(dt):
    mod = dt.hour * 60 + dt.minute
    end_dt = dt + timedelta(minutes=29, seconds=59)
    filename = (
        f"3B-HHR.MS.MRG.3IMERG.{dt.strftime('%Y%m%d')}-"
        f"S{dt.strftime('%H%M%S')}-E{end_dt.strftime('%H%M%S')}."
        f"{mod:04d}.V07B.HDF5"
    )
    return filename

def download_item_with_session(session, item):
    dt, expected_filename, url = item
    dest_path = RAW_DIR / expected_filename

    if is_valid_h5(dest_path):
        return expected_filename, "EXISTS", True

    for attempt in range(3):
        try:
            resp = session.get(url, allow_redirects=True, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 100000:
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                if is_valid_h5(dest_path):
                    return expected_filename, "DOWNLOADED", True
        except Exception as e:
            time.sleep(1)
    return expected_filename, "FAILED", False

def main():
    print("=" * 60)
    print("HISTORICAL IMERG ACQUISITION & PROCESSING (FAST REUSE SESSION)")
    print("Window: 2015-11-30T00:00:00Z to 2015-12-05T00:00:00Z")
    print("=" * 60)

    expected_dts = generate_expected_timesteps()
    print(f"Expected timesteps count: {len(expected_dts)}")

    print("Searching NASA CMR for granules...")
    granule_map = search_cmr_granules()
    print(f"CMR returned {len(granule_map)} matching granules.")

    items_to_process = []
    for dt in expected_dts:
        expected_filename = build_filename_for_dt(dt)
        url = granule_map.get(expected_filename)
        if not url:
            doy = dt.timetuple().tm_yday
            url = f"https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGHH.07/{dt.year}/{doy:03d}/{expected_filename}"
        items_to_process.append((dt, expected_filename, url))

    # Single persistent session with Connection Pooling
    session = create_authenticated_session()
    
    downloaded_count = 0
    missing_count = 0
    corrupt_count = 0

    print("Processing acquisition items with pooled session...")
    for idx, item in enumerate(items_to_process, 1):
        dt, fname, url = item
        dest_path = RAW_DIR / fname

        if is_valid_h5(dest_path):
            continue

        print(f"[{idx}/{len(items_to_process)}] Downloading {fname}...")
        fname_out, status, success = download_item_with_session(session, item)
        if status == "DOWNLOADED":
            print(f"  [+] Downloaded: {fname}")
        elif status == "FAILED":
            print(f"  [-] Failed: {fname}")

    # Extract Rainfall Data for all Expected Timesteps
    processed_records = []
    for dt in expected_dts:
        expected_filename = build_filename_for_dt(dt)
        dest_path = RAW_DIR / expected_filename

        if not is_valid_h5(dest_path):
            missing_count += 1
            processed_records.append({
                "timestamp_utc": dt.isoformat().replace("+00:00", "Z"),
                "latitude": CHENNAI_LAT,
                "longitude": CHENNAI_LON,
                "rainfall_mm_hr": None,
                "rainfall_status": "MISSING",
                "source_file": expected_filename,
                "dataset": "GPM_3IMERGHH",
                "version": "V07B",
            })
            continue

        downloaded_count += 1
        try:
            with h5py.File(dest_path, "r") as f:
                grid = f["Grid"]
                lats = grid["lat"][:]
                lons = grid["lon"][:]
                precip_ds = grid.get("precipitation")
                if precip_ds is None:
                    precip_ds = grid.get("precipitationCal")

                lat_idx, lon_idx = find_nearest_indices(lats, lons, CHENNAI_LAT, CHENNAI_LON)
                val = float(precip_ds[0, lon_idx, lat_idx])

                status = "VALID"
                if np.isnan(val):
                    status = "MISSING"
                    val = None
                elif val < 0:
                    status = "NEGATIVE"
                    val = None
                else:
                    val = round(val, 4)

                processed_records.append({
                    "timestamp_utc": dt.isoformat().replace("+00:00", "Z"),
                    "latitude": float(lats[lat_idx]),
                    "longitude": float(lons[lon_idx]),
                    "rainfall_mm_hr": val,
                    "rainfall_status": status,
                    "source_file": expected_filename,
                    "dataset": "GPM_3IMERGHH",
                    "version": "V07B",
                })
        except Exception as e:
            print(f"Error reading {expected_filename}: {e}")
            corrupt_count += 1
            processed_records.append({
                "timestamp_utc": dt.isoformat().replace("+00:00", "Z"),
                "latitude": CHENNAI_LAT,
                "longitude": CHENNAI_LON,
                "rainfall_mm_hr": None,
                "rainfall_status": "CORRUPT",
                "source_file": expected_filename,
                "dataset": "GPM_3IMERGHH",
                "version": "V07B",
            })

    # Write CSV
    csv_path = PROCESSED_DIR / "chennai_2015_imerg_timeseries.csv"
    fieldnames = [
        "timestamp_utc", "latitude", "longitude",
        "rainfall_mm_hr", "rainfall_status",
        "source_file", "dataset", "version"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in processed_records:
            writer.writerow(r)

    # Compute Statistics
    valid_vals = [r["rainfall_mm_hr"] for r in processed_records if r["rainfall_status"] == "VALID" and r["rainfall_mm_hr"] is not None]
    valid_records = [r for r in processed_records if r["rainfall_status"] == "VALID"]

    min_rain = min(valid_vals) if valid_vals else None
    max_rain = max(valid_vals) if valid_vals else None
    mean_rain = round(sum(valid_vals) / len(valid_vals), 4) if valid_vals else None

    timestamps = [r["timestamp_utc"] for r in processed_records]
    first_ts = timestamps[0] if timestamps else None
    last_ts = timestamps[-1] if timestamps else None

    summary = {
        "expected_timesteps": len(expected_dts),
        "successfully_downloaded_timesteps": len(valid_records),
        "missing_timesteps": missing_count,
        "duplicate_or_corrupt_files": corrupt_count,
        "first_available_timestamp": first_ts,
        "last_available_timestamp": last_ts,
        "rainfall_min": min_rain,
        "rainfall_max": max_rain,
        "rainfall_mean": mean_rain,
        "processed_window_peak_rainfall": max_rain,
    }

    print("\n--- ACQUISITION & PROCESSING SUMMARY ---")
    print(json.dumps(summary, indent=2))

    summary_path = PROCESSED_DIR / "acquisition_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
