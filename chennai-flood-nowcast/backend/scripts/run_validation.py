#!/usr/bin/env python
"""
Validation Runner

Executes the full validation pipeline:
1. Loads replay output (or runs replay if not available)
2. Loads normalized validation observations
3. Runs depth validation (PATH A)
4. Runs occurrence validation (PATH B)
5. Writes all validation result files

Usage:
    cd backend
    .\\venv\\Scripts\\python scripts/run_validation.py

Output:
    data/validation/results/
        historical_replay_timeseries.csv
        depth_validation_results.csv
        occurrence_validation_results.json
        validation_metrics.json
        validation_report.md

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
    run_depth_validation,
    write_depth_validation_csv,
    run_occurrence_validation,
    write_occurrence_json,
    build_validation_metrics,
    write_validation_report,
)


def main():
    project_root = backend_dir.parent
    raw_dir = project_root / "data" / "forcing" / "historical" / "raw"
    validation_file = project_root / "data" / "validation" / "processed" / "chennai_validation_normalized.geojson"
    results_dir = project_root / "data" / "validation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("VALIDATION PIPELINE")
    print("=" * 60)
    print()

    # ─── Step 1: Run Historical Replay ─────────────────────────
    model_version = "GRID_HYDROLOGY_V1"
    print(f"Step 1: Running historical replay with model_version={model_version}...")
    replay = run_historical_replay(raw_dir, model_version=model_version)

    csv_path = results_dir / "historical_replay_timeseries.csv"
    write_replay_csv(replay["timeseries"], csv_path)
    print(f"  Replay status: {replay['historical_replay_status']}")
    print(f"  Event status:  {replay['event_replay_status']}")
    print(f"  Model version: {replay.get('historical_replay_model_version', model_version)}")
    print(f"  Timesteps:     {replay.get('forcing', {}).get('timesteps_processed', 0)}")
    print(f"  Peak rainfall: {replay.get('processed_window_peak_rainfall_mm_hr')} mm/hr")
    print()

    # ─── Step 2: Load Validation Observations ──────────────────
    print("Step 2: Loading validation observations...")
    if not validation_file.exists():
        print(f"  ERROR: Validation file not found: {validation_file}")
        print("  Cannot proceed with validation.")
        return

    with open(validation_file, "r", encoding="utf-8") as f:
        validation_data = json.load(f)

    observations = validation_data.get("features", [])
    print(f"  Total observations: {len(observations)}")

    depth_obs_count = sum(
        1 for obs in observations
        if obs.get("properties", {}).get("observed_depth_cm") is not None
    )
    chennai_obs_count = sum(
        1 for obs in observations
        if obs.get("properties", {}).get("event") == "Chennai_2015"
    )
    print(f"  With depth:         {depth_obs_count}")
    print(f"  Chennai_2015:       {chennai_obs_count}")
    print()

    # ─── Step 3: Depth Validation (PATH A) ─────────────────────
    print("Step 3: Running depth validation (PATH A)...")
    peak_rainfall = replay.get("processed_window_peak_rainfall_mm_hr")

    depth_result = run_depth_validation(
        observations=observations,
        peak_rainfall=peak_rainfall,
        model_version=model_version,
    )

    depth_csv_path = results_dir / "depth_validation_results.csv"
    write_depth_validation_csv(depth_result.get("results", []), depth_csv_path)

    print(f"  Status:             {depth_result['status']}")
    print(f"  Type:               {depth_result.get('validation_type')}")
    print(f"  Sample count:       {depth_result.get('sample_count')}")
    print(f"  Valid comparisons:  {depth_result.get('valid_comparison_count')}")
    print(f"  MAE (cm):           {depth_result.get('mae_cm')}")
    print(f"  RMSE (cm):          {depth_result.get('rmse_cm')}")
    print(f"  Median AE (cm):     {depth_result.get('median_ae_cm')}")
    print()

    # ─── Step 4: Occurrence Validation (PATH B) ────────────────
    print("Step 4: Running occurrence validation (PATH B)...")

    # Default: null threshold → NOT_COMPUTABLE
    occurrence_result = run_occurrence_validation(
        observations=observations,
        peak_rainfall=peak_rainfall,
        threshold_cm=None,  # Explicitly null — no arbitrary threshold
        threshold_source=None,
        model_version=model_version,
    )

    occ_path = results_dir / "occurrence_validation_results.json"
    write_occurrence_json(occurrence_result, occ_path)

    print(f"  Status:             {occurrence_result['status']}")
    print(f"  Reason:             {occurrence_result.get('reason', 'N/A')}")
    print(f"  Sample count:       {occurrence_result.get('sample_count')}")
    print(f"  Threshold (cm):     {occurrence_result.get('threshold_depth_cm')}")
    print(f"  Precision:          {occurrence_result.get('precision')}")
    print(f"  Recall:             {occurrence_result.get('recall')}")
    print(f"  F1:                 {occurrence_result.get('f1')}")
    print()

    # ─── Step 5: Write Metrics and Report ──────────────────────
    print("Step 5: Writing validation metrics and report...")

    metrics = build_validation_metrics(replay, depth_result, occurrence_result, model_version=model_version)

    metrics_path = results_dir / "historical_validation_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  Metrics: {metrics_path}")

    report_path = results_dir / "historical_validation_report.md"
    write_validation_report(metrics, depth_result, occurrence_result, report_path)
    print(f"  Report:  {report_path}")
    print()

    # ─── Final Summary ─────────────────────────────────────────
    print("=" * 60)
    print("VALIDATION PIPELINE COMPLETE")
    print("=" * 60)
    print()
    print(f"  Historical Replay:    {metrics['historical_replay_status']}")
    print(f"  Event Replay:         {metrics['event_replay_status']}")
    print(f"  Model Validation:     {metrics['model_validation_status']}")
    print()
    print("  Output files:")
    print(f"    {csv_path}")
    print(f"    {depth_csv_path}")
    print(f"    {occ_path}")
    print(f"    {metrics_path}")
    print(f"    {report_path}")
    print()

    if metrics.get("limitations"):
        print("  Limitations:")
        for lim in metrics["limitations"]:
            print(f"    - {lim}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
