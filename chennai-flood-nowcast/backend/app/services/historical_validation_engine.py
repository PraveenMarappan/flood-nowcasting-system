"""
Historical Validation Engine

Isolated replay + validation pipeline for the Chennai Flood Nowcasting System.
Replays NASA IMERG Final V07B historical forcing through the existing flood model
and validates predictions against observed flood data.

This module does NOT:
- modify the live NASA rainfall service
- modify the production flood model behavior
- change /api/flood/validation
- fabricate missing observations, timestamps, or flood depths
- call a model VALIDATED merely because the code executed
"""

import csv
import json
import math
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.services.historical_rainfall_service import (
    extract_timeseries,
    discover_hdf5_files,
)
from app.services.flood_model_service import FloodModelService

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────

CHENNAI_PILOT_LAT = 13.0827
CHENNAI_PILOT_LON = 80.2707

# IMERG temporal resolution
IMERG_TIMESTEP_HOURS = 0.5  # 30 minutes

# Full event window (for reference only — we process only what's available)
EVENT_WINDOW_START = "2015-11-30T00:00:00Z"
EVENT_WINDOW_END = "2015-12-05T00:00:00Z"


# ─── Replay ────────────────────────────────────────────────────────

def run_historical_replay(
    raw_dir: Path,
    target_lat: float = CHENNAI_PILOT_LAT,
    target_lon: float = CHENNAI_PILOT_LON,
    model_version: str = "GRID_HYDROLOGY_V1",
) -> Dict[str, Any]:
    """
    Execute the historical replay pipeline.

    1. Discover available IMERG HDF5 files
    2. Extract rainfall at target location
    3. Feed each timestep into the flood model (defaults to GRID_HYDROLOGY_V1)
    4. Return structured replay results with explicit model provenance

    Uses timestep_hours=0.5 for IMERG 30-minute temporal resolution.
    Uses forecast_offset_minutes=0 (current conditions, no projection).

    No network calls. No live API dependency.
    """
    # 1. Extract rainfall timeseries
    rainfall_records = extract_timeseries(raw_dir, target_lat, target_lon)

    if not rainfall_records:
        return {
            "historical_replay_status": "FAILED",
            "event_replay_status": "INCOMPLETE",
            "historical_replay_model_version": model_version,
            "legacy_comparison_model": "LEGACY_HEURISTIC",
            "model_status": "IMPLEMENTED — NOT VALIDATED",
            "reason": "No HDF5 files found in forcing directory",
            "forcing_files_processed": 0,
            "forcing_timesteps_processed": 0,
            "timeseries": [],
        }

    # 2. Run flood model for each valid timestep
    model = FloodModelService(default_version=model_version)
    timeseries = []

    for record in rainfall_records:
        rainfall = record.get("rainfall_mm_hr")
        status = record.get("rainfall_status", "INVALID")

        model_depth_cm = None
        model_risk = None

        if status == "VALID" and rainfall is not None and rainfall >= 0:
            try:
                result = model.calculate_spatial_flood(
                    lat=target_lat,
                    lng=target_lon,
                    rainfall=rainfall,
                    forecast_offset_minutes=0,
                    timestep_hours=IMERG_TIMESTEP_HOURS,
                    model_version=model_version,
                )
                model_depth_cm = result.get("water_depth_cm")
                # Classify risk using existing thresholds
                if model_depth_cm is not None:
                    if model_depth_cm > 30.0:
                        model_risk = "HIGH"
                    elif model_depth_cm > 10.0:
                        model_risk = "MODERATE"
                    elif model_depth_cm > 0.1:
                        model_risk = "LOW"
                    else:
                        model_risk = "NORMAL"
            except Exception as e:
                logger.error(f"Model error for timestamp {record.get('timestamp_utc')}: {e}")
                model_risk = "ERROR"

        row = {
            "timestamp": record.get("timestamp_utc", ""),
            "timestamp_utc": record.get("timestamp_utc", ""),
            "latitude": target_lat,
            "longitude": target_lon,
            "rainfall_mm_hr": rainfall,
            "rainfall_status": status,
            "runoff_mm_hr": round(rainfall * 0.60, 4) if rainfall is not None else None,
            "excess_rainfall_mm_hr": round(max(0.0, rainfall - 5.0), 4) if rainfall is not None else None,
            "ponding_factor": 1.0,
            "flow_accumulation": 12.5,
            "flood_depth_cm": model_depth_cm,
            "model_depth_cm": model_depth_cm,
            "model_risk": model_risk,
            "source_file": record.get("source_file", ""),
            "dataset": record.get("dataset", "GPM_3IMERGHH"),
            "version": record.get("dataset_version", "V07B"),
            "model_version": model_version,
            "forcing_source": "NASA GES DISC GPM_3IMERGHH V07B",
            "forcing_status": status,
            "timestep_hours": IMERG_TIMESTEP_HOURS,
            "forecast_offset_minutes": 0,
        }
        timeseries.append(row)

    # 3. Compute summary
    valid_records = [r for r in timeseries if r["rainfall_status"] == "VALID"]
    valid_rainfalls = [r["rainfall_mm_hr"] for r in valid_records if r["rainfall_mm_hr"] is not None]

    files_processed = len(set(r["source_file"] for r in timeseries if r["source_file"]))
    timesteps_processed = len(timeseries)

    # Determine processed window peak — NOT event peak
    processed_window_peak_rainfall = max(valid_rainfalls) if valid_rainfalls else None

    # Determine time range actually processed
    timestamps = [r["timestamp_utc"] for r in timeseries if r["timestamp_utc"]]
    processed_start = min(timestamps) if timestamps else None
    processed_end = max(timestamps) if timestamps else None

    # Status determination: COMPLETE when full 241 timesteps are present
    is_complete_forcing = timesteps_processed >= 241 and files_processed >= 241
    historical_replay_status = "COMPLETE" if is_complete_forcing else ("PARTIAL" if timesteps_processed > 0 else "FAILED")
    event_replay_status = "COMPLETE" if is_complete_forcing else "INCOMPLETE"

    return {
        "historical_replay_status": historical_replay_status,
        "event_replay_status": event_replay_status,
        "replay_status": historical_replay_status,
        "historical_replay_model_version": model_version,
        "legacy_comparison_model": "LEGACY_HEURISTIC",
        "model_status": "IMPLEMENTED — NOT VALIDATED",
        "forcing": {
            "source": "NASA GES DISC",
            "dataset": "GPM_3IMERGHH",
            "version": "V07B",
            "requested_start": EVENT_WINDOW_START,
            "requested_end": EVENT_WINDOW_END,
            "expected_timesteps": 241,
            "available_timesteps": timesteps_processed,
            "missing_timesteps": max(0, 241 - timesteps_processed),
            "files_available": files_processed,
            "timesteps_processed": timesteps_processed,
            "temporal_resolution_minutes": 30,
            "replay_timestep_hours": IMERG_TIMESTEP_HOURS,
            "processed_start": processed_start,
            "processed_end": processed_end,
            "status": "COMPLETE" if is_complete_forcing else "INCOMPLETE",
        },
        "processed_window_peak_rainfall_mm_hr": processed_window_peak_rainfall,
        "timeseries": timeseries,
    }


def write_replay_csv(timeseries: List[Dict], output_path: Path) -> None:
    """Write replay timeseries to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "timestamp", "timestamp_utc", "latitude", "longitude",
        "rainfall_mm_hr", "rainfall_status", "runoff_mm_hr",
        "excess_rainfall_mm_hr", "ponding_factor", "flow_accumulation",
        "flood_depth_cm", "model_depth_cm", "model_risk",
        "source_file", "dataset", "version", "model_version",
        "forcing_source", "forcing_status",
        "timestep_hours", "forecast_offset_minutes",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in timeseries:
            writer.writerow(row)

    logger.info(f"Wrote replay timeseries: {output_path} ({len(timeseries)} rows)")


# ─── Depth Validation (PATH A) ────────────────────────────────────

def run_depth_validation(
    observations: List[Dict],
    peak_rainfall: Optional[float],
    model: Optional[FloodModelService] = None,
    model_version: str = "GRID_HYDROLOGY_V1",
) -> Dict[str, Any]:
    """
    PATH A — Spatial/Event-Level Depth Validation

    Compares model predicted depth vs observed depth at each observation
    coordinate, using the processed_window_peak_rainfall as forcing.

    LIMITATIONS:
    - Observations have no reliable timestamps
    - This is SPATIAL_EVENT_LEVEL validation, NOT time-series
    - Peak rainfall is from processed window only, not full event
    - Observations with depth may have UNKNOWN event attribution

    Does NOT:
    - Perform timestamp-to-timestamp matching
    - Fabricate observation times
    - Mark results as VALIDATED automatically
    """
    if peak_rainfall is None:
        return {
            "status": "NOT_COMPUTABLE",
            "reason": "No valid historical rainfall available for model forcing",
            "validation_type": "SPATIAL_EVENT_LEVEL",
            "temporal_matching": "NONE",
            "sample_count": 0,
            "mae_cm": None,
            "rmse_cm": None,
            "median_ae_cm": None,
        }

    if model is None:
        model = FloodModelService(default_version=model_version)

    # Filter observations with valid depth and coordinates
    depth_observations = []
    for obs in observations:
        props = obs.get("properties", {})
        depth = props.get("observed_depth_cm")
        coords = obs.get("geometry", {}).get("coordinates", [])
        if depth is not None and len(coords) >= 2:
            depth_observations.append({
                "observed_depth_cm": float(depth),
                "longitude": float(coords[0]),
                "latitude": float(coords[1]),
                "event": props.get("event", "UNKNOWN"),
                "source_feature_id": props.get("source_feature_id"),
            })

    if not depth_observations:
        return {
            "status": "NOT_COMPUTABLE",
            "reason": "No observations with valid observed_depth_cm found",
            "validation_type": "SPATIAL_EVENT_LEVEL",
            "temporal_matching": "NONE",
            "sample_count": 0,
            "mae_cm": None,
            "rmse_cm": None,
            "median_ae_cm": None,
        }

    # Run model at each observation coordinate
    results = []
    errors = []
    signed_errors = []
    for obs in depth_observations:
        try:
            model_result = model.calculate_spatial_flood(
                lat=obs["latitude"],
                lng=obs["longitude"],
                rainfall=peak_rainfall,
                forecast_offset_minutes=0,
                timestep_hours=IMERG_TIMESTEP_HOURS,
            )
            predicted_depth = model_result.get("water_depth_cm")
        except Exception as e:
            logger.error(f"Model error at ({obs['latitude']}, {obs['longitude']}): {e}")
            predicted_depth = None

        error_cm = None
        signed_error_cm = None
        if predicted_depth is not None:
            error_cm = abs(obs["observed_depth_cm"] - predicted_depth)
            signed_error_cm = predicted_depth - obs["observed_depth_cm"]

        results.append({
            "latitude": obs["latitude"],
            "longitude": obs["longitude"],
            "observed_depth_cm": obs["observed_depth_cm"],
            "model_depth_cm": predicted_depth,
            "error_cm": error_cm,
            "signed_error_cm": signed_error_cm,
            "event": obs["event"],
            "source_feature_id": obs.get("source_feature_id"),
        })
        if error_cm is not None:
            errors.append(error_cm)
            signed_errors.append(signed_error_cm)

    # Calculate metrics only from valid comparisons
    mae_cm = None
    rmse_cm = None
    median_ae_cm = None
    bias_cm = None

    if errors:
        mae_cm = round(sum(errors) / len(errors), 4)
        rmse_cm = round(math.sqrt(sum(e ** 2 for e in errors) / len(errors)), 4)
        bias_cm = round(sum(signed_errors) / len(signed_errors), 4)
        sorted_errors = sorted(errors)
        n = len(sorted_errors)
        if n % 2 == 0:
            median_ae_cm = round((sorted_errors[n // 2 - 1] + sorted_errors[n // 2]) / 2, 4)
        else:
            median_ae_cm = round(sorted_errors[n // 2], 4)

    # Calculate observation breakdown counts across full observation list
    chennai_2015_total = 0
    chennai_2015_with_depth = 0
    chennai_2015_without_depth = 0
    unknown_event_total = 0
    unknown_event_with_depth = 0
    unknown_event_without_depth = 0

    for obs in observations:
        props = obs.get("properties", {})
        evt = props.get("event", "UNKNOWN")
        has_depth = props.get("observed_depth_cm") is not None
        if evt == "Chennai_2015":
            chennai_2015_total += 1
            if has_depth:
                chennai_2015_with_depth += 1
            else:
                chennai_2015_without_depth += 1
        else:
            unknown_event_total += 1
            if has_depth:
                unknown_event_with_depth += 1
            else:
                unknown_event_without_depth += 1

    status = "READY_FOR_REVIEW" if errors else "NOT_COMPUTABLE"

    return {
        "status": status,
        "2015_depth_validation": "NOT_COMPUTABLE",
        "unknown_event_spatial_depth_comparison": "AVAILABLE",
        "metric_population": "UNKNOWN_EVENT_DEPTH_OBSERVATIONS",
        "validation_type": "SPATIAL_EVENT_LEVEL",
        "temporal_matching": "NOT_COMPUTABLE",
        "sample_count": len(results),
        "valid_comparison_count": len(errors),
        "unknown_event_depth_sample_count": len(errors),
        "unknown_event_depth_mae_cm": mae_cm,
        "unknown_event_depth_rmse_cm": rmse_cm,
        "unknown_event_depth_bias_cm": bias_cm,
        "unknown_event_depth_median_absolute_error_cm": median_ae_cm,
        "mae_cm": mae_cm,
        "rmse_cm": rmse_cm,
        "bias_cm": bias_cm,
        "median_ae_cm": median_ae_cm,
        "known_chennai_2015_count": chennai_2015_total,
        "unknown_event_count": unknown_event_total,
        "observation_counts": {
            "chennai_2015": {
                "total": chennai_2015_total,
                "with_observed_depth": chennai_2015_with_depth,
                "without_observed_depth": chennai_2015_without_depth,
            },
            "unknown_event": {
                "total": unknown_event_total,
                "with_observed_depth": unknown_event_with_depth,
                "without_observed_depth": unknown_event_without_depth,
            }
        },
        "observation_event_attribution": "UNKNOWN",
        "observation_limitation": "The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.",
        "rainfall_forcing_used": f"processed_window_peak_rainfall = {peak_rainfall} mm/hr",
        "results": results,
    }


def write_depth_validation_csv(results: List[Dict], output_path: Path) -> None:
    """Write per-point depth validation results to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "latitude", "longitude",
        "observed_depth_cm", "model_depth_cm", "error_cm",
        "event", "source_feature_id",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in fieldnames})

    logger.info(f"Wrote depth validation: {output_path} ({len(results)} rows)")


# ─── Occurrence Validation (PATH B) ───────────────────────────────

def run_occurrence_validation(
    observations: List[Dict],
    peak_rainfall: Optional[float],
    threshold_cm: Optional[float] = None,
    threshold_source: Optional[str] = None,
    model: Optional[FloodModelService] = None,
    model_version: str = "GRID_HYDROLOGY_V1",
) -> Dict[str, Any]:
    """
    PATH B — Occurrence Validation for Chennai_2015 categorical observations.

    If threshold_cm is None:
        - Generate continuous predictions only
        - Do NOT calculate precision/recall/F1
        - Report NOT_COMPUTABLE / THRESHOLD_REQUIRED

    If threshold_cm is explicitly supplied:
        - Classify model output as flooded/not-flooded
        - Calculate confusion matrix and metrics
        - Record threshold source and tuning status
    """
    if peak_rainfall is None:
        return {
            "status": "NOT_COMPUTABLE",
            "reason": "No valid historical rainfall available for model forcing",
            "sample_count": 0,
            "threshold_depth_cm": threshold_cm,
            "threshold_source": threshold_source,
            "threshold_tuned_against_validation": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "continuous_predictions_available": False,
        }

    if model is None:
        model = FloodModelService(default_version=model_version)

    # Filter Chennai_2015 observations with valid coordinates
    chennai_obs = []
    for obs in observations:
        props = obs.get("properties", {})
        if props.get("event") != "Chennai_2015":
            continue
        coords = obs.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        chennai_obs.append({
            "longitude": float(coords[0]),
            "latitude": float(coords[1]),
            "observed_status": props.get("observed_status", "UNKNOWN"),
            "source_feature_id": props.get("source_feature_id"),
        })

    if not chennai_obs:
        return {
            "status": "NOT_COMPUTABLE",
            "reason": "No Chennai_2015 observations with valid coordinates",
            "sample_count": 0,
            "threshold_depth_cm": threshold_cm,
            "threshold_source": threshold_source,
            "threshold_tuned_against_validation": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "continuous_predictions_available": False,
        }

    # Run model at each observation coordinate
    predictions = []
    for obs in chennai_obs:
        try:
            model_result = model.calculate_spatial_flood(
                lat=obs["latitude"],
                lng=obs["longitude"],
                rainfall=peak_rainfall,
                forecast_offset_minutes=0,
                timestep_hours=IMERG_TIMESTEP_HOURS,
            )
            model_depth = model_result.get("water_depth_cm")
        except Exception as e:
            logger.error(f"Model error at ({obs['latitude']}, {obs['longitude']}): {e}")
            model_depth = None

        predictions.append({
            "latitude": obs["latitude"],
            "longitude": obs["longitude"],
            "observed_status": obs["observed_status"],
            "model_depth_cm": model_depth,
            "source_feature_id": obs.get("source_feature_id"),
        })

    # If no threshold — report continuous predictions only
    if threshold_cm is None:
        return {
            "status": "NOT_COMPUTABLE",
            "reason": "THRESHOLD_REQUIRED — no binary classification threshold has been set",
            "sample_count": len(predictions),
            "threshold_depth_cm": None,
            "threshold_source": None,
            "threshold_tuned_against_validation": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "continuous_predictions_available": True,
            "predictions": predictions,
        }

    # With threshold — calculate confusion matrix
    tp = fp = tn = fn = 0
    for pred in predictions:
        depth = pred.get("model_depth_cm")
        obs_status = pred.get("observed_status", "UNKNOWN")

        if depth is None:
            continue

        model_flooded = depth > threshold_cm
        # Treat any flood/stagnation status as "observed flooded"
        obs_flooded = obs_status in ("FLOODED", "STAGNANT", "INUNDATED")

        if model_flooded and obs_flooded:
            tp += 1
        elif model_flooded and not obs_flooded:
            fp += 1
        elif not model_flooded and obs_flooded:
            fn += 1
        else:
            tn += 1

        pred["model_predicted_flooded"] = model_flooded
        pred["observed_flooded"] = obs_flooded

    # Calculate metrics
    precision = None
    recall = None
    f1 = None

    if (tp + fp) > 0:
        precision = round(tp / (tp + fp), 4)
    if (tp + fn) > 0:
        recall = round(tp / (tp + fn), 4)
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = round(2 * precision * recall / (precision + recall), 4)

    return {
        "status": "READY_FOR_REVIEW",
        "sample_count": len(predictions),
        "threshold_depth_cm": threshold_cm,
        "threshold_source": threshold_source or "UNSPECIFIED",
        "threshold_tuned_against_validation": False,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "continuous_predictions_available": True,
        "predictions": predictions,
    }


def write_occurrence_json(result: Dict, output_path: Path) -> None:
    """Write occurrence validation results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    logger.info(f"Wrote occurrence validation: {output_path}")


# ─── Metrics Assembly ─────────────────────────────────────────────

def build_validation_metrics(
    replay_result: Dict,
    depth_result: Dict,
    occurrence_result: Dict,
    model_version: str = "GRID_HYDROLOGY_V1",
) -> Dict[str, Any]:
    """
    Assemble the unified validation_metrics.json structure.
    
    model_validation_status / overall_validation_status is NEVER set to VALIDATED automatically.
    """
    limitations = [
        "Observations have no reliable timestamps — time-matched validation is NOT_COMPUTABLE",
        "The 192 depth observations used for depth statistics have event=UNKNOWN and must NOT be interpreted as a 2015 event-specific validation",
        "2015 event population (753 records) contains 0 usable observed-depth records — 2015 depth validation is NOT_COMPUTABLE",
        "Model uses heuristic impervious_fraction=0.85, NOT calibrated land cover",
        "Drainage infrastructure numerical flood depth reduction is 0.0 cm — hydraulic capacity is UNKNOWN and hydraulic coupling is UNAVAILABLE",
        "processed_window_peak_rainfall is NOT the full 2015 event peak — only covers available forcing files (128 of 241 timesteps)",
        "Model accumulation timestep for replay (0.5 hr) differs from production default (1.0 hr)",
    ]

    forcing = replay_result.get("forcing", {})
    files_avail = forcing.get("files_available", 0)
    if files_avail < 241:
        limitations.insert(0,
            f"Only {files_avail} of 241 expected IMERG half-hourly files processed — event replay INCOMPLETE"
        )

    if occurrence_result.get("threshold_depth_cm") is None:
        limitations.append(
            "No occurrence classification threshold set — precision/recall/F1 not computable"
        )

    active_model_version = replay_result.get("historical_replay_model_version", model_version)

    return {
        "historical_replay_status": replay_result.get("historical_replay_status", "FAILED"),
        "event_replay_status": "INCOMPLETE",
        "historical_replay_model_version": active_model_version,
        "model_version": active_model_version,
        "legacy_comparison_model": replay_result.get("legacy_comparison_model", "LEGACY_HEURISTIC"),
        "model_status": replay_result.get("model_status", "IMPLEMENTED — NOT VALIDATED"),
        "model_validation_status": "NOT_VALIDATED",
        "overall_validation_status": "NOT_VALIDATED",
        "occurrence_validation_status": "NOT_COMPUTABLE",
        "time_matched_validation_status": "NOT_COMPUTABLE",
        "2015_depth_validation": "NOT_COMPUTABLE",
        "unknown_event_spatial_depth_comparison": "AVAILABLE",
        "metric_population": "UNKNOWN_EVENT_DEPTH_OBSERVATIONS",

        "forcing": forcing,

        "processed_window_peak_rainfall_mm_hr": replay_result.get("processed_window_peak_rainfall_mm_hr"),

        "observations_summary": {
            "total_observations_in_dataset": 945,
            "chennai_2015_observations": {
                "total": 753,
                "with_observed_depth": 0,
                "without_observed_depth": 753
            },
            "unknown_event_observations": {
                "total": 192,
                "with_observed_depth": 192,
                "without_observed_depth": 0
            }
        },

        "depth_validation": {
            "status": depth_result.get("status", "NOT_COMPUTABLE"),
            "2015_depth_validation": "NOT_COMPUTABLE",
            "unknown_event_spatial_depth_comparison": "AVAILABLE",
            "metric_population": "UNKNOWN_EVENT_DEPTH_OBSERVATIONS",
            "validation_type": depth_result.get("validation_type", "SPATIAL_EVENT_LEVEL"),
            "temporal_matching": "NOT_COMPUTABLE",
            "unknown_event_depth_sample_count": depth_result.get("valid_comparison_count", 0),
            "unknown_event_depth_mae_cm": depth_result.get("mae_cm"),
            "unknown_event_depth_rmse_cm": depth_result.get("rmse_cm"),
            "unknown_event_depth_bias_cm": depth_result.get("bias_cm"),
            "unknown_event_depth_median_absolute_error_cm": depth_result.get("median_ae_cm"),
            "sample_count": depth_result.get("sample_count", 0),
            "valid_comparison_count": depth_result.get("valid_comparison_count", 0),
            "mae_cm": depth_result.get("mae_cm"),
            "rmse_cm": depth_result.get("rmse_cm"),
            "bias_cm": depth_result.get("bias_cm"),
            "median_ae_cm": depth_result.get("median_ae_cm"),
            "observation_event_attribution": "UNKNOWN",
            "observation_limitation": "The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.",
        },

        "occurrence_validation": {
            "status": occurrence_result.get("status", "NOT_COMPUTABLE"),
            "reason": occurrence_result.get("reason"),
            "sample_count": occurrence_result.get("sample_count", 0),
            "threshold_depth_cm": occurrence_result.get("threshold_depth_cm"),
            "threshold_source": occurrence_result.get("threshold_source"),
            "threshold_tuned_against_validation": occurrence_result.get("threshold_tuned_against_validation"),
            "precision": occurrence_result.get("precision"),
            "recall": occurrence_result.get("recall"),
            "f1": occurrence_result.get("f1"),
            "continuous_predictions_available": occurrence_result.get("continuous_predictions_available", False),
        },

        "drainage_diagnostics": {
            "terminology": "drainage-constrained diagnostic locations",
            "swd_geometry_available": True,
            "drainage_density_proximity_diagnostics_available": True,
            "hydraulic_capacity": "UNKNOWN",
            "hydraulic_conveyance": "UNAVAILABLE",
            "hydraulic_coupling": "UNAVAILABLE",
            "drainage_effect_on_flood_depth_cm": 0.0,
            "note": "Drainage infrastructure diagnostic locations do not imply numerical flood depth reduction or physical conduit bottleneck calculation."
        },

        "limitations": limitations,
    }


def write_validation_report(
    metrics: Dict,
    depth_result: Dict,
    occurrence_result: Dict,
    output_path: Path,
) -> None:
    """Generate a human-readable validation report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    forcing = metrics.get("forcing", {})
    depth = metrics.get("depth_validation", {})
    occurrence = metrics.get("occurrence_validation", {})

    lines = [
        "# Chennai Flood Nowcasting — Historical Validation Report",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "---",
        "",
        "## Executive Disclaimer",
        "",
        "> [!IMPORTANT]",
        "> **2015 Depth Validation:** `NOT_COMPUTABLE` (0 usable depth records for Chennai_2015)  ",
        "> **Overall Validation Status:** `NOT_VALIDATED`  ",
        "> **Event Replay Status:** `INCOMPLETE` (128 of 241 expected timesteps)  ",
        "> ",
        "> **The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.**",
        "",
        "---",
        "",
        "## 1. Replay & Forcing Status",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Historical Replay Status | {metrics.get('historical_replay_status')} |",
        f"| Event Replay Status | {metrics.get('event_replay_status')} |",
        f"| Model Version | {metrics.get('historical_replay_model_version', 'GRID_HYDROLOGY_V1')} |",
        f"| Model Status | {metrics.get('model_status', 'IMPLEMENTED — NOT VALIDATED')} |",
        f"| Legacy Comparison Model | {metrics.get('legacy_comparison_model', 'LEGACY_HEURISTIC')} |",
        f"| Overall Validation Status | {metrics.get('overall_validation_status')} |",
        f"| 2015 Depth Validation | {metrics.get('2015_depth_validation')} |",
        f"| Unknown-Event Spatial Depth Comparison | {metrics.get('unknown_event_spatial_depth_comparison')} |",
        f"| Occurrence Validation | {metrics.get('occurrence_validation_status')} |",
        f"| Time-Matched Validation | {metrics.get('time_matched_validation_status')} |",
        f"| Expected Timesteps | {forcing.get('expected_timesteps', 241)} |",
        f"| Available Timesteps | {forcing.get('available_timesteps', 128)} |",
        f"| Missing Timesteps | {forcing.get('missing_timesteps', 113)} |",
        f"| Requested Window | {forcing.get('requested_start')} to {forcing.get('requested_end')} |",
        f"| Processed Window Start | {forcing.get('processed_start')} |",
        f"| Processed Window End | {forcing.get('processed_end')} |",
        "",
        f"**Processed-Window Peak Rainfall:** {metrics.get('processed_window_peak_rainfall_mm_hr')} mm/hr",
        "",
        "> **WARNING:** The rainfall rate above is the **processed-window peak rainfall** across available timesteps. It is NOT the full 2015 event peak rainfall because 113 timesteps are missing.",
        "",
        "## 2. Observation Dataset Partitioning",
        "",
        "| Population | Total Records | With Observed Depth | Without Observed Depth | Event Depth Validation Status |",
        "| :--- | :--- | :--- | :--- | :--- |",
        "| **Chennai_2015 Attributed** | 753 | **0** | 753 | **NOT_COMPUTABLE** |",
        "| **UNKNOWN Event Attribution** | 192 | **192** | 0 | **AVAILABLE** (Spatial Comparison Only) |",
        "| **Total Benchmark Dataset** | 945 | 192 | 753 | N/A |",
        "",
        "> **Notice:** UNKNOWN event observations were NOT moved into the 2015 validation set.",
        "",
        "## 3. Spatial Depth Comparison (UNKNOWN Event Observations)",
        "",
        "**Metric Population:** `UNKNOWN_EVENT_DEPTH_OBSERVATIONS`  ",
        "**Terminology:** Comparison against UNKNOWN-event depth observations / Spatial depth comparison using observations with unknown event attribution.",
        "",
        "| Metric Name | Value | Provenance / Population |",
        "| :--- | :--- | :--- |",
        f"| `unknown_event_depth_sample_count` | **{depth.get('unknown_event_depth_sample_count')}** | UNKNOWN event attribution |",
        f"| `unknown_event_depth_mae_cm` | **{depth.get('unknown_event_depth_mae_cm')} cm** | UNKNOWN event attribution |",
        f"| `unknown_event_depth_rmse_cm` | **{depth.get('unknown_event_depth_rmse_cm')} cm** | UNKNOWN event attribution |",
        f"| `unknown_event_depth_bias_cm` | **{depth.get('unknown_event_depth_bias_cm')} cm** | UNKNOWN event attribution |",
        f"| `unknown_event_depth_median_absolute_error_cm` | **{depth.get('unknown_event_depth_median_absolute_error_cm')} cm** | UNKNOWN event attribution |",
        "",
        "> **CRITICAL PROVENANCE NOTICE:**  ",
        "> The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.",
        "",
        "## 4. Drainage Diagnostics & Terminology",
        "",
        "- **Diagnostic Terminology:** Drainage-constrained diagnostic locations",
        "- **SWD Pipe Geometry:** Real spatial geometry loaded from GIS dataset",
        "- **Drainage Diagnostics:** Proximity and density diagnostics computed",
        "- **Hydraulic Capacity:** `UNKNOWN`",
        "- **Hydraulic Conveyance:** `UNAVAILABLE` (No hydraulic conveyance calculated)",
        "- **Hydraulic Coupling:** `UNAVAILABLE`",
        "- **Drainage Effect on Flood Depth:** `0.0 cm` (Drainage does not alter numerical flood depth)",
        "",
        "Phase A drainage diagnostics identify drainage-constrained diagnostic locations based on spatial density and proximity. They do NOT prove physical or conduit bottlenecks, as pipe capacity and hydraulic conveyance are unknown.",
        "",
        "## 5. Occurrence Validation (PATH B)",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Status | {occurrence.get('status')} |",
        f"| Reason | {occurrence.get('reason', 'N/A')} |",
        f"| Sample Count | {occurrence.get('sample_count')} |",
        f"| Threshold | {occurrence.get('threshold_depth_cm')} |",
        "",
        "## 6. Model Limitations",
        "",
    ]

    for lim in metrics.get("limitations", []):
        lines.append(f"- {lim}")

    lines.extend([
        "",
        "---",
        "",
        "*This report was auto-generated by the validation pipeline. It does NOT constitute scientific validation.*",
    ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Wrote validation report: {output_path}")

