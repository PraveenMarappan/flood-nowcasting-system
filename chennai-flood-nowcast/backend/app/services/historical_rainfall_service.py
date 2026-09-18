"""
Historical Rainfall Service — IMERG Final V07B HDF5 Extractor

Reads NASA GPM IMERG Final Precipitation L3 Half Hourly HDF5 files
from the local filesystem. No network calls. No live API dependency.

Dataset: GPM_3IMERGHH  
Version: V07B  
Temporal resolution: 30 minutes  
Spatial resolution: 0.1° × 0.1°

HDF5 structure:
    Grid/precipitation  shape (1, 3600, 1800)  dtype float32
    Grid/lat            shape (1800,)
    Grid/lon            shape (3600,)
    Grid/time           Unix epoch seconds
    
Indexing: precipitation[time_idx, lon_idx, lat_idx]
"""

import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
import h5py

logger = logging.getLogger(__name__)

# IMERG filename pattern:
# 3B-HHR.MS.MRG.3IMERG.YYYYMMDD-SHHMMSS-EHHMMSS.MMMM.V07B.HDF5
IMERG_FILENAME_PATTERN = re.compile(
    r"3B-HHR\.MS\.MRG\.3IMERG\."
    r"(\d{4})(\d{2})(\d{2})-"
    r"S(\d{2})(\d{2})(\d{2})-"
    r"E(\d{2})(\d{2})(\d{2})\."
    r"(\d{4})\."
    r"(V\d+[A-Z]?)\."
    r"HDF5$"
)

DATASET_SHORT_NAME = "GPM_3IMERGHH"
PREFERRED_PRECIP_VAR = "precipitation"
FALLBACK_PRECIP_VAR = "precipitationCal"


def discover_hdf5_files(raw_dir: Path) -> List[Path]:
    """
    Discover all *.HDF5 files in the given directory.
    Returns files sorted by filename (which is chronological for IMERG).
    """
    if not raw_dir.exists():
        logger.warning(f"Historical forcing directory does not exist: {raw_dir}")
        return []

    files = sorted(raw_dir.glob("*.HDF5"))
    logger.info(f"Discovered {len(files)} HDF5 file(s) in {raw_dir}")
    return files


def parse_imerg_filename(filename: str) -> Optional[Dict[str, Any]]:
    """
    Parse an IMERG filename to extract timestamp and version metadata.
    
    Example: 3B-HHR.MS.MRG.3IMERG.20151130-S000000-E002959.0000.V07B.HDF5
    
    Returns:
        dict with start_time, end_time, version, minute_offset
        or None if filename does not match pattern.
    """
    match = IMERG_FILENAME_PATTERN.match(filename)
    if not match:
        logger.warning(f"Filename does not match IMERG pattern: {filename}")
        return None

    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    s_hr, s_min, s_sec = int(match.group(4)), int(match.group(5)), int(match.group(6))
    e_hr, e_min, e_sec = int(match.group(7)), int(match.group(8)), int(match.group(9))
    minute_offset = int(match.group(10))
    version = match.group(11)

    start_time = datetime(year, month, day, s_hr, s_min, s_sec, tzinfo=timezone.utc)
    end_time = datetime(year, month, day, e_hr, e_min, e_sec, tzinfo=timezone.utc)

    return {
        "start_time": start_time,
        "end_time": end_time,
        "version": version,
        "minute_offset": minute_offset,
        "filename": filename
    }


def _find_nearest_index(array: np.ndarray, target: float) -> int:
    """Find the index of the nearest value in a sorted array."""
    return int(np.abs(array - target).argmin())


def extract_rainfall(filepath: Path, target_lat: float, target_lon: float) -> Dict[str, Any]:
    """
    Extract rainfall value from a single IMERG HDF5 file at the nearest
    grid cell to (target_lat, target_lon).

    Returns a record dict with rainfall value, status, and metadata.
    Never silently converts missing/negative to zero.
    """
    result = {
        "timestamp_utc": None,
        "rainfall_mm_hr": None,
        "rainfall_status": "INVALID",
        "source_file": filepath.name,
        "latitude": None,
        "longitude": None,
        "dataset": DATASET_SHORT_NAME,
        "dataset_version": None,
        "units": "mm/hr"
    }

    # Parse filename for timestamp and version
    parsed = parse_imerg_filename(filepath.name)
    if parsed:
        result["timestamp_utc"] = parsed["start_time"].isoformat()
        result["dataset_version"] = parsed["version"]

    try:
        with h5py.File(filepath, "r") as f:
            if "Grid" not in f:
                result["rainfall_status"] = "INVALID"
                logger.error(f"No 'Grid' group in {filepath.name}")
                return result

            grid = f["Grid"]

            # Read coordinate arrays
            lats = grid["lat"][:]
            lons = grid["lon"][:]

            # Cross-validate timestamp if Grid/time is available
            if "time" in grid:
                hdf5_time = grid["time"][0]
                # IMERG time is seconds since 1980-01-06T00:00:00Z
                imerg_epoch = datetime(1980, 1, 6, tzinfo=timezone.utc)
                hdf5_timestamp = imerg_epoch + __import__("datetime").timedelta(seconds=int(hdf5_time))
                result["hdf5_timestamp_utc"] = hdf5_timestamp.isoformat()

            # Detect precipitation variable
            precip_ds = grid.get(PREFERRED_PRECIP_VAR)
            precip_var_used = PREFERRED_PRECIP_VAR
            if precip_ds is None:
                precip_ds = grid.get(FALLBACK_PRECIP_VAR)
                precip_var_used = FALLBACK_PRECIP_VAR
            if precip_ds is None:
                result["rainfall_status"] = "INVALID"
                logger.error(f"No precipitation variable found in {filepath.name}")
                return result

            result["precipitation_variable"] = precip_var_used

            # Find nearest indices
            lat_idx = _find_nearest_index(lats, target_lat)
            lon_idx = _find_nearest_index(lons, target_lon)

            # Record actual grid cell coordinates
            result["latitude"] = float(lats[lat_idx])
            result["longitude"] = float(lons[lon_idx])

            # Extract value: shape (1, 3600, 1800) -> precip[time, lon, lat]
            raw_value = float(precip_ds[0, lon_idx, lat_idx])

            # Classify the value
            if np.isnan(raw_value):
                result["rainfall_status"] = "MISSING"
                result["rainfall_mm_hr"] = None
            elif raw_value < 0:
                result["rainfall_status"] = "NEGATIVE"
                result["rainfall_mm_hr"] = None
                result["raw_value"] = raw_value
            else:
                result["rainfall_status"] = "VALID"
                result["rainfall_mm_hr"] = round(raw_value, 4)

    except Exception as e:
        result["rainfall_status"] = "INVALID"
        result["error"] = str(e)
        logger.error(f"Error reading {filepath.name}: {e}")

    return result


def extract_timeseries(
    raw_dir: Path,
    target_lat: float,
    target_lon: float
) -> List[Dict[str, Any]]:
    """
    Discover all IMERG HDF5 files in raw_dir, extract rainfall at the
    target location, and return records sorted chronologically.

    No network calls. No live API dependency.
    """
    files = discover_hdf5_files(raw_dir)
    if not files:
        logger.warning("No HDF5 files found for timeseries extraction")
        return []

    records = []
    for fp in files:
        record = extract_rainfall(fp, target_lat, target_lon)
        records.append(record)

    # Sort by timestamp
    records.sort(key=lambda r: r.get("timestamp_utc") or "")

    logger.info(
        f"Extracted {len(records)} timestep(s). "
        f"Valid: {sum(1 for r in records if r['rainfall_status'] == 'VALID')}, "
        f"Missing: {sum(1 for r in records if r['rainfall_status'] == 'MISSING')}, "
        f"Negative: {sum(1 for r in records if r['rainfall_status'] == 'NEGATIVE')}, "
        f"Invalid: {sum(1 for r in records if r['rainfall_status'] == 'INVALID')}"
    )

    return records
