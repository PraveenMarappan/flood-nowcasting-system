import os
import sys
import json
import csv
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import h5py

backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent
raw_dir = project_root / "data" / "forcing" / "historical" / "raw"
results_dir = project_root / "data" / "validation" / "results"

def compute_sha256(fpath: Path) -> str:
    hasher = hashlib.sha256()
    with open(fpath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def check_integrity():
    print("=" * 70)
    print("FINAL INTEGRITY VERIFICATION AUDIT")
    print("=" * 70)

    errors = []

    # 1. raw_manifest.json
    manifest_path = project_root / "data" / "forcing" / "historical" / "raw_manifest.json"
    if not manifest_path.exists():
        errors.append("raw_manifest.json missing!")
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        print(f"[CHECK 1] raw_manifest.json records count: {len(manifest)}")
        if len(manifest) != 241:
            errors.append(f"raw_manifest.json record count is {len(manifest)}, expected 241")

        timestamps = [item["timestamp_utc"] for item in manifest]
        if len(set(timestamps)) != 241:
            errors.append(f"Duplicate timestamps in raw_manifest.json! Unique: {len(set(timestamps))}")

        filenames = [item["filename"] for item in manifest]
        if len(set(filenames)) != 241:
            errors.append(f"Duplicate filenames in raw_manifest.json! Unique: {len(set(filenames))}")

        start_dt = datetime(2015, 11, 30, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(2015, 12, 5, 0, 0, tzinfo=timezone.utc)

        for item in manifest:
            ts = datetime.fromisoformat(item["timestamp_utc"].replace("Z", "+00:00"))
            if not (start_dt <= ts <= end_dt):
                errors.append(f"Timestamp out of bounds: {item['timestamp_utc']}")
            
            fname = item["filename"]
            fpath = raw_dir / fname
            if not fpath.exists():
                errors.append(f"File listed in manifest does not exist: {fname}")
            elif not item.get("sha256") or len(item.get("sha256")) != 64:
                errors.append(f"Invalid SHA256 in manifest for {fname}")

    # 2. missing_timestamps.json
    missing_path = project_root / "data" / "forcing" / "historical" / "missing_timestamps.json"
    if not missing_path.exists():
        errors.append("missing_timestamps.json does not exist!")
    else:
        with open(missing_path, "r", encoding="utf-8") as f:
            missing = json.load(f)
        print(f"[CHECK 2] missing_timestamps.json items count: {len(missing)}")
        if len(missing) != 0:
            errors.append(f"missing_timestamps.json is not empty! Length = {len(missing)}")

    # 3. historical_replay_timeseries.csv
    csv_path = results_dir / "historical_replay_timeseries.csv"
    if not csv_path.exists():
        errors.append("historical_replay_timeseries.csv does not exist!")
    else:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        print(f"[CHECK 3] historical_replay_timeseries.csv rows count: {len(reader)}")
        if len(reader) != 241:
            errors.append(f"historical_replay_timeseries.csv row count is {len(reader)}, expected 241")

        csv_ts = [row["timestamp_utc"] for row in reader]
        if len(set(csv_ts)) != 241:
            errors.append(f"Duplicate timestamps in CSV! Unique: {len(set(csv_ts))}")

        for idx, row in enumerate(reader, 1):
            if row.get("model_version") != "GRID_HYDROLOGY_V1":
                errors.append(f"CSV row {idx} model_version is {row.get('model_version')}, expected GRID_HYDROLOGY_V1")
            if row.get("rainfall_status") != "VALID":
                errors.append(f"CSV row {idx} rainfall_status is {row.get('rainfall_status')}, expected VALID")

    # 4. independent_validation_metrics.json
    indep_path = results_dir / "independent_validation_metrics.json"
    if not indep_path.exists():
        errors.append("independent_validation_metrics.json does not exist!")
    else:
        with open(indep_path, "r", encoding="utf-8") as f:
            indep = json.load(f)
        print(f"[CHECK 4] Validation Status: {indep.get('validation_status')}")
        print(f"[CHECK 4] Scientific Classification: {indep.get('scientific_classification')}")
        
        unk = indep.get("unknown_event_depth_comparison", {})
        if unk.get("population_name") != "UNKNOWN_EVENT_DEPTH_OBSERVATIONS":
            errors.append(f"Population name is '{unk.get('population_name')}', expected UNKNOWN_EVENT_DEPTH_OBSERVATIONS")
        if "2015 validation" in json.dumps(unk).lower():
            errors.append("192 UNKNOWN observations mislabelled as 2015 validation!")

    # 5. event_validation_metrics.csv
    evt_path = results_dir / "event_validation_metrics.csv"
    if not evt_path.exists():
        errors.append("event_validation_metrics.csv missing!")
    else:
        with open(evt_path, "r", encoding="utf-8") as f:
            evt_rows = list(csv.DictReader(f))
        print(f"[CHECK 5] Event validation metrics rows: {len(evt_rows)}")
        for r in evt_rows:
            if r.get("MAE_cm") != "N/A" or r.get("RMSE_cm") != "N/A":
                errors.append("Event validation metrics contain fabricated numerical metrics for 2015 event!")

    # 6. observation_sources.json
    obs_path = project_root / "data" / "validation" / "observation_sources.json"
    if not obs_path.exists():
        errors.append("observation_sources.json missing!")
    else:
        with open(obs_path, "r", encoding="utf-8") as f:
            obs_data = json.load(f)
        ds_map = {d["population_name"]: d for d in obs_data.get("datasets", [])}
        print(f"[CHECK 6] Chennai_2015 records: {ds_map.get('Chennai_2015', {}).get('total_records')}, depth: {ds_map.get('Chennai_2015', {}).get('records_with_depth')}")
        print(f"[CHECK 6] UNKNOWN records: {ds_map.get('UNKNOWN', {}).get('total_records')}, depth: {ds_map.get('UNKNOWN', {}).get('records_with_depth')}")
        
        if ds_map.get("Chennai_2015", {}).get("records_with_depth") != 0:
            errors.append("Chennai_2015 records reported with non-zero depth count!")
        if ds_map.get("UNKNOWN", {}).get("records_with_depth") != 192:
            errors.append("UNKNOWN records depth count is not 192!")

    print("\n" + "=" * 70)
    if errors:
        print(f"VERIFICATION FAILED WITH {len(errors)} ERRORS:")
        for err in errors:
            print(f"  [-] {err}")
    else:
        print("SUCCESS: ALL INTEGRITY CHECKS 1-6 PASSED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    check_integrity()
