#!/usr/bin/env python
"""
Historical Replay Runner

Discovers verified NASA IMERG Final V07B HDF5 files and replays them
through the existing flood model at the Chennai pilot location.

Usage:
    cd backend
    .\\venv\\Scripts\\python scripts/run_historical_replay.py

Output:
    data/validation/results/historical_replay_timeseries.csv

No network calls. No live API dependency. No NASA credentials required.
"""

import sys
import json
from pathlib import Path

# Ensure backend package is importable
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.historical_validation_engine import (
    run_historical_replay,
    write_replay_csv,
)


def main():
    project_root = backend_dir.parent
    raw_dir = project_root / "data" / "forcing" / "historical" / "raw"
    results_dir = project_root / "data" / "validation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("HISTORICAL RAINFALL REPLAY")
    print("=" * 60)
    print(f"Forcing directory: {raw_dir}")
    print(f"Output directory:  {results_dir}")
    print()

    # Run replay
    replay = run_historical_replay(raw_dir)

    # Write timeseries CSV
    csv_path = results_dir / "historical_replay_timeseries.csv"
    write_replay_csv(replay["timeseries"], csv_path)

    # Print summary
    forcing = replay.get("forcing", {})
    print("─── REPLAY SUMMARY ────────────────────────────────")
    print(f"Historical Replay Status:     {replay['historical_replay_status']}")
    print(f"Event Replay Status:          {replay['event_replay_status']}")
    print(f"Forcing Files Processed:      {forcing.get('files_available', 0)}")
    print(f"Forcing Timesteps Processed:  {forcing.get('timesteps_processed', 0)}")
    print(f"Temporal Resolution:          {forcing.get('temporal_resolution_minutes', 'N/A')} min")
    print(f"Replay Timestep:              {forcing.get('replay_timestep_hours', 'N/A')} hr")
    print(f"Processed Window Start:       {forcing.get('processed_start', 'N/A')}")
    print(f"Processed Window End:         {forcing.get('processed_end', 'N/A')}")
    print(f"Processed Window Peak Rain:   {replay.get('processed_window_peak_rainfall_mm_hr', 'N/A')} mm/hr")
    print()

    # Print timeseries
    ts = replay.get("timeseries", [])
    if ts:
        print("─── TIMESERIES ────────────────────────────────────")
        for row in ts:
            print(
                f"  {row['timestamp_utc']}  "
                f"rain={row['rainfall_mm_hr']} mm/hr  "
                f"status={row['rainfall_status']}  "
                f"depth={row['model_depth_cm']} cm  "
                f"risk={row['model_risk']}"
            )
        print()

    print(f"Output written to: {csv_path}")
    print()

    # Save replay metadata as JSON for the validation script
    meta_path = results_dir / "replay_metadata.json"
    meta = {k: v for k, v in replay.items() if k != "timeseries"}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)
    print(f"Replay metadata:   {meta_path}")

    print("=" * 60)
    print("REPLAY COMPLETE")
    print("=" * 60)

    return replay


if __name__ == "__main__":
    main()
