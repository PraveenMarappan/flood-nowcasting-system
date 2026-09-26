import os
import sys
import json
import time
import hashlib
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

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
RESULTS_DIR = project_root / "data" / "validation" / "results"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

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
            redirect_parsed = urllib.parse.urlparse(url)
            if not any(domain in redirect_parsed.hostname for domain in ["nasa.gov", "earthdata.nasa.gov", "eosdis.nasa.gov", "cloudfront.net"]):
                del headers['Authorization']
        return


def create_authenticated_session():
    session = EarthdataSession()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 429])
    adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if EARTHDATA_TOKEN:
        session.headers.update({"Authorization": f"Bearer {EARTHDATA_TOKEN}"})
    elif EARTHDATA_USER and EARTHDATA_PASS:
        session.auth = (EARTHDATA_USER, EARTHDATA_PASS)
    return session


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_nearest_indices(lats, lons, target_lat, target_lon):
    lat_idx = (np.abs(lats - target_lat)).argmin()
    lon_idx = (np.abs(lons - target_lon)).argmin()
    return lat_idx, lon_idx


def is_valid_imerg_h5(file_path: Path) -> bool:
    if not file_path.exists() or file_path.stat().st_size < 100000:
        return False
    try:
        with h5py.File(file_path, "r") as f:
            if "Grid" in f:
                grid = f["Grid"]
                if "lat" in grid and "lon" in grid and ("precipitation" in grid or "precipitationCal" in grid):
                    return True
    except Exception:
        return False
    return False


def generate_expected_timesteps():
    start = datetime(2015, 11, 30, 0, 0, tzinfo=timezone.utc)
    end = datetime(2015, 12, 5, 0, 0, tzinfo=timezone.utc)
    current = start
    timesteps = []
    while current <= end:
        timesteps.append(current)
        current += timedelta(minutes=30)
    return timesteps


def build_filename_for_dt(dt: datetime) -> str:
    mod = dt.hour * 60 + dt.minute
    end_dt = dt + timedelta(minutes=29, seconds=59)
    filename = (
        f"3B-HHR.MS.MRG.3IMERG.{dt.strftime('%Y%m%d')}-"
        f"S{dt.strftime('%H%M%S')}-E{end_dt.strftime('%H%M%S')}."
        f"{mod:04d}.V07B.HDF5"
    )
    return filename


def search_cmr_granules():
    url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {
        "short_name": "GPM_3IMERGHH",
        "temporal[]": "2015-11-30T00:00:00Z,2015-12-05T00:30:00Z",
        "page_size": 300
    }
    for attempt in range(3):
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
            print(f"CMR search warning (attempt {attempt+1}): {e}")
            time.sleep(1)
    return {}


def download_worker(item):
    dt, fname, url = item
    dest_path = RAW_DIR / fname
    if is_valid_imerg_h5(dest_path):
        return dt, fname, "EXISTS", True

    session = create_authenticated_session()
    err_reason = "Unknown"
    for attempt in range(3):
        try:
            resp = session.get(url, allow_redirects=True, timeout=35)
            if resp.status_code == 200 and len(resp.content) > 100000:
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                if is_valid_imerg_h5(dest_path):
                    return dt, fname, "DOWNLOADED", True
                else:
                    err_reason = "Invalid HDF5 content"
            else:
                err_reason = f"HTTP {resp.status_code} (bytes={len(resp.content)})"
        except Exception as e:
            err_reason = f"Exception: {e}"
            time.sleep(1)
    return dt, fname, f"FAILED ({err_reason})", False


def main():
    print("=" * 70)
    print("PHASE 1 AUDIT & PHASE 2 NASA GPM IMERG ACQUISITION")
    print("=" * 70)

    expected_dts = generate_expected_timesteps()
    print(f"Expected half-hourly timesteps in 5-day window: {len(expected_dts)}")

    # 1. Existing Audit Before Download
    existing_valid_files = set()
    corrupted_files = []
    duplicates_set = set()

    for fname in os.listdir(RAW_DIR):
        if fname.endswith(".HDF5"):
            fpath = RAW_DIR / fname
            if is_valid_imerg_h5(fpath):
                if fname in existing_valid_files:
                    duplicates_set.add(fname)
                else:
                    existing_valid_files.add(fname)
            else:
                corrupted_files.append(fname)

    available_before = len(existing_valid_files)
    print(f"Available timesteps BEFORE download attempt: {available_before}")
    print(f"Missing timesteps BEFORE download attempt:   {len(expected_dts) - available_before}")

    # 2. Search CMR and Build Target Download List
    print("\nSearching NASA CMR for granule URLs...")
    cmr_map = search_cmr_granules()
    print(f"CMR returned {len(cmr_map)} granule links.")

    download_tasks = []
    for dt in expected_dts:
        fname = build_filename_for_dt(dt)
        dest_path = RAW_DIR / fname
        if not is_valid_imerg_h5(dest_path):
            url = cmr_map.get(fname)
            if not url:
                doy = dt.timetuple().tm_yday
                url = f"https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGHH.07/{dt.year}/{doy:03d}/{fname}"
            download_tasks.append((dt, fname, url))

    newly_downloaded = 0
    download_failed = 0

    if download_tasks:
        print(f"\nInitiating 5-thread parallel download for {len(download_tasks)} missing granules...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_map = {
                executor.submit(download_worker, item): item[1]
                for item in download_tasks
            }
            for idx, future in enumerate(as_completed(future_map), 1):
                dt, fname, status, success = future.result()
                if status == "DOWNLOADED":
                    newly_downloaded += 1
                    print(f"  [{idx}/{len(download_tasks)}] [+] Downloaded & Verified: {fname}")
                elif status == "EXISTS":
                    pass
                else:
                    download_failed += 1
                    print(f"  [{idx}/{len(download_tasks)}] [-] Download Result: {fname} -> {status}")
    else:
        print("\nAll 241 granules are already downloaded and verified on disk!")

    # 3. Post-Acquisition Audit & Manifest Generation
    manifest = []
    missing_timestamps = []
    valid_count_after = 0
    corrupt_after = 0

    first_available_ts = None
    last_available_ts = None

    for dt in expected_dts:
        ts_iso = dt.isoformat().replace("+00:00", "Z")
        fname = build_filename_for_dt(dt)
        fpath = RAW_DIR / fname

        if is_valid_imerg_h5(fpath):
            valid_count_after += 1
            if first_available_ts is None:
                first_available_ts = ts_iso
            last_available_ts = ts_iso

            fsize = fpath.stat().st_size
            sha256_hash = compute_sha256(fpath)

            # Extract Chennai sample rainfall value
            val = None
            try:
                with h5py.File(fpath, "r") as hf:
                    grid = hf["Grid"]
                    lats = grid["lat"][:]
                    lons = grid["lon"][:]
                    precip_ds = grid.get("precipitation")
                    if precip_ds is None:
                        precip_ds = grid.get("precipitationCal")
                    lat_idx, lon_idx = find_nearest_indices(lats, lons, CHENNAI_LAT, CHENNAI_LON)
                    raw_val = float(precip_ds[0, lon_idx, lat_idx])
                    if not np.isnan(raw_val) and raw_val >= 0:
                        val = round(raw_val, 4)
            except Exception as e:
                pass

            manifest.append({
                "timestamp_utc": ts_iso,
                "filename": fname,
                "dataset": "GPM_3IMERGHH",
                "version": "V07B",
                "file_size_bytes": fsize,
                "sha256": sha256_hash,
                "hdf5_valid": True,
                "chennai_rainfall_mm_hr": val,
                "chennai_extraction_status": "SUCCESS" if val is not None else "ERROR"
            })
        else:
            if fpath.exists():
                corrupt_after += 1
            missing_timestamps.append(ts_iso)

    missing_count_after = len(missing_timestamps)

    # 4. Save Audit Artifacts
    completeness_audit = {
        "expected_timesteps": len(expected_dts),
        "available_timesteps_before": available_before,
        "newly_downloaded_timesteps": newly_downloaded,
        "available_timesteps": valid_count_after,
        "missing_timesteps": missing_count_after,
        "duplicates": len(duplicates_set),
        "corrupted_files": corrupt_after,
        "first_available": first_available_ts,
        "last_available": last_available_ts,
        "dataset": "GPM_3IMERGHH",
        "version": "V07B",
        "spatial_resolution": "0.1 deg (~10 km)",
        "units": "mm/hr",
        "status": "COMPLETE" if valid_count_after == len(expected_dts) else "INCOMPLETE",
        "timestamp_audit_performed_at": datetime.now(timezone.utc).isoformat()
    }

    with open(RESULTS_DIR / "completeness_audit.json", "w", encoding="utf-8") as f:
        json.dump(completeness_audit, f, indent=2)

    with open(project_root / "data" / "forcing" / "historical" / "raw_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    with open(project_root / "data" / "forcing" / "historical" / "missing_timestamps.json", "w", encoding="utf-8") as f:
        json.dump(missing_timestamps, f, indent=2)

    print("\n" + "=" * 70)
    print("PHASE 1 & 2 ACQUISITION SUMMARY RESULTS")
    print("=" * 70)
    print(f"EXPECTED TIMESTEPS: {len(expected_dts)}")
    print(f"AVAILABLE BEFORE:   {available_before}")
    print(f"NEWLY DOWNLOADED:   {newly_downloaded}")
    print(f"AVAILABLE AFTER:    {valid_count_after}")
    print(f"MISSING AFTER:      {missing_count_after}")
    print(f"CORRUPTED:          {corrupt_after}")
    print(f"DUPLICATES:         {len(duplicates_set)}")
    print("=" * 70)

    if missing_timestamps:
        print(f"\nRemaining Missing Timestamps ({len(missing_timestamps)} total):")
        for ts in missing_timestamps[:10]:
            print(f"  - {ts}")
        if len(missing_timestamps) > 10:
            print(f"  ... and {len(missing_timestamps) - 10} more.")
    else:
        print("\nSUCCESS: 241/241 TIMESTEPS ARE 100% COMPLETE & VERIFIED!")

if __name__ == "__main__":
    main()
