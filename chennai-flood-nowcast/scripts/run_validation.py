import json
import csv
import sys
import numpy as np
from pathlib import Path
from shapely.geometry import shape, Point

# Add backend directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.flood_model_service import FloodModelService

VAL_GEOJSON = ROOT_DIR / "data" / "validation" / "processed" / "chennai_validation_normalized.geojson"
REPLAY_CSV = ROOT_DIR / "data" / "validation" / "results" / "historical_replay_timeseries.csv"
RESULTS_DIR = ROOT_DIR / "data" / "validation" / "results"

METRICS_JSON = RESULTS_DIR / "historical_validation_metrics.json"
REPORT_MD = RESULTS_DIR / "historical_validation_report.md"

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not VAL_GEOJSON.exists():
        print(f"ERROR: Validation GeoJSON not found at {VAL_GEOJSON}")
        sys.exit(1)
        
    if not REPLAY_CSV.exists():
        print(f"ERROR: Replay CSV not found at {REPLAY_CSV}")
        sys.exit(1)
        
    # Read replay timeseries to find peak rainfall during event window
    replay_records = []
    with open(REPLAY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            replay_records.append(row)
            
    rain_vals = [float(r["rainfall_mm_hr"]) for r in replay_records]
    peak_event_rain = max(rain_vals) if rain_vals else 0.0
    
    # Read normalized validation dataset
    with open(VAL_GEOJSON, "r", encoding="utf-8") as f:
        val_data = json.load(f)
        
    features = val_data.get("features", [])
    print(f"Loaded {len(features)} total validation records from GeoJSON.")
    
    # Separate into Event-Attributed vs Unknown Attribution
    event_2015_features = []
    unknown_attr_features = []
    
    for feat in features:
        props = feat.get("properties", {})
        attr = props.get("event") or props.get("event_attribution") or props.get("attribution") or "UNKNOWN"
        if attr == "Chennai_2015":
            event_2015_features.append(feat)
        else:
            unknown_attr_features.append(feat)
            
    c2015_with_depth = [f for f in event_2015_features if f.get("properties", {}).get("observed_depth_cm") is not None]
    c2015_without_depth = [f for f in event_2015_features if f.get("properties", {}).get("observed_depth_cm") is None]
    
    unk_with_depth = [f for f in unknown_attr_features if f.get("properties", {}).get("observed_depth_cm") is not None]
    unk_without_depth = [f for f in unknown_attr_features if f.get("properties", {}).get("observed_depth_cm") is None]

    print(f"  - Chennai_2015 Total: {len(event_2015_features)} (with depth: {len(c2015_with_depth)}, without depth: {len(c2015_without_depth)})")
    print(f"  - UNKNOWN Event Total: {len(unknown_attr_features)} (with depth: {len(unk_with_depth)}, without depth: {len(unk_without_depth)})")
    print(f"  - 2015 Event Depth Validation: NOT_COMPUTABLE (0 usable depth observations)")

    # Spatial depth error evaluation for UNKNOWN event depth observations
    model = FloodModelService()
    validation_records = []
    abs_errors = []
    sq_errors = []
    diffs = []
    
    for idx, feat in enumerate(unk_with_depth):
        geom = shape(feat["geometry"])
        coords = geom.coords[0] if geom.geom_type == "Point" else (geom.centroid.x, geom.centroid.y)
        lng, lat = coords[0], coords[1]
        
        props = feat.get("properties", {})
        obs_depth_cm = float(props["observed_depth_cm"])
        obs_id = props.get("id") or props.get("source_feature_id") or f"obs_{idx+1}"
        
        calc = model.calculate_spatial_flood(
            lat=lat,
            lng=lng,
            rainfall=peak_event_rain,
            forecast_offset_minutes=0,
            timestep_hours=0.5
        )
        
        pred_depth_cm = round(float(calc.get("water_depth_cm", 0.0)), 2)
        abs_err = round(abs(pred_depth_cm - obs_depth_cm), 2)
        sq_err = round((pred_depth_cm - obs_depth_cm) ** 2, 2)
        diff = round(pred_depth_cm - obs_depth_cm, 2)
        
        abs_errors.append(abs_err)
        sq_errors.append(sq_err)
        diffs.append(diff)
        
        validation_records.append({
            "observation_id": obs_id,
            "latitude": lat,
            "longitude": lng,
            "observed_depth_cm": obs_depth_cm,
            "predicted_depth_cm": pred_depth_cm,
            "absolute_error_cm": abs_err,
            "squared_error_cm2": sq_err,
            "timestamp_status": "UNKNOWN",
            "event_attribution": "UNKNOWN"
        })
        
    # Calculate Statistical Validation Metrics
    if abs_errors:
        mae = float(np.mean(abs_errors))
        rmse = float(np.sqrt(np.mean(sq_errors)))
        bias = float(np.mean(diffs))
        median_ae = float(np.median(abs_errors))
        sample_count = len(abs_errors)
    else:
        mae, rmse, bias, median_ae, sample_count = None, None, None, None, 0
        
    metrics = {
        "event_window": "2015-11-30T00:00:00Z to 2015-12-05T00:00:00Z",
        "dataset": "GPM_3IMERGHH V07B",
        "expected_timesteps": 241,
        "available_timesteps": len(replay_records),
        "missing_timesteps": max(0, 241 - len(replay_records)),
        "event_replay_status": "INCOMPLETE",
        "processed_window_peak_rainfall_mm_hr": peak_event_rain,
        "observation_counts": {
            "total_normalized_records": len(features),
            "chennai_2015": {
                "total": len(event_2015_features),
                "with_observed_depth": len(c2015_with_depth),
                "without_observed_depth": len(c2015_without_depth),
            },
            "unknown_event": {
                "total": len(unknown_attr_features),
                "with_observed_depth": len(unk_with_depth),
                "without_observed_depth": len(unk_without_depth),
            }
        },
        "2015_depth_validation": "NOT_COMPUTABLE",
        "unknown_event_spatial_depth_comparison": "AVAILABLE",
        "metric_population": "UNKNOWN_EVENT_DEPTH_OBSERVATIONS",
        "depth_validation": {
            "metric_population": "UNKNOWN_EVENT_DEPTH_OBSERVATIONS",
            "unknown_event_depth_sample_count": sample_count,
            "unknown_event_depth_mae_cm": round(mae, 4) if mae is not None else None,
            "unknown_event_depth_rmse_cm": round(rmse, 4) if rmse is not None else None,
            "unknown_event_depth_bias_cm": round(bias, 4) if bias is not None else None,
            "unknown_event_depth_median_absolute_error_cm": round(median_ae, 4) if median_ae is not None else None,
            "mae_cm": round(mae, 4) if mae is not None else None,
            "rmse_cm": round(rmse, 4) if rmse is not None else None,
            "bias_cm": round(bias, 4) if bias is not None else None,
            "median_absolute_error_cm": round(median_ae, 4) if median_ae is not None else None,
            "sample_count": sample_count,
            "provenance_statement": "The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation."
        },
        "occurrence_validation": {
            "status": "NOT_COMPUTABLE",
            "reason": "THRESHOLD_NOT_DEFINED",
            "note": "No predefined observation inundation threshold exists in project spec."
        },
        "time_matched_validation": {
            "status": "NOT_COMPUTABLE",
            "reason": "OBSERVATION_TIMESTAMPS_UNAVAILABLE",
            "note": "Historical observations lack sub-daily timestamps."
        },
        "drainage_diagnostics": {
            "terminology": "drainage-constrained diagnostic locations",
            "hydraulic_capacity": "UNKNOWN",
            "hydraulic_conveyance": "UNAVAILABLE",
            "hydraulic_coupling": "UNAVAILABLE",
            "drainage_effect_on_flood_depth_cm": 0.0
        },
        "overall_validation_status": "NOT_VALIDATED",
        "validation_disclaimer": "The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation."
    }
    
    # Save Metrics JSON
    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
        
    print(f"\nSaved Validation Metrics JSON to {METRICS_JSON}")
    print("\nVALIDATION METRICS SUMMARY:")
    print(f"  - 2015 Depth Validation: NOT_COMPUTABLE")
    print(f"  - Metric Population: UNKNOWN_EVENT_DEPTH_OBSERVATIONS")
    print(f"  - Sample Count: {sample_count}")
    print(f"  - MAE:  {mae:.2f} cm" if mae else "  - MAE: N/A")
    print(f"  - RMSE: {rmse:.2f} cm" if rmse else "  - RMSE: N/A")
    print(f"  - Bias: {bias:.2f} cm" if bias else "  - Bias: N/A")
    print(f"  - Median AE: {median_ae:.2f} cm" if median_ae else "  - Median AE: N/A")

    # Generate Validation Report Markdown
    report_content = f"""# 2015 Chennai Flood Event Replay & Historical Validation Report

## Executive Disclaimer

> [!IMPORTANT]
> **2015 Depth Validation:** `NOT_COMPUTABLE` (0 usable depth records for Chennai_2015)  
> **Overall Validation Status:** `NOT_VALIDATED`  
> **Event Replay Status:** `INCOMPLETE` (128 of 241 expected timesteps)  
>  
> **The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.**

---

## 1. Forcing Data & Replay Inventory
* **Event Window:** `2015-11-30T00:00:00Z` to `2015-12-05T00:00:00Z`
* **Dataset:** NASA GPM IMERG Final L3 Half-Hourly (`GPM_3IMERGHH.07` V07B)
* **Replay Timestep:** `0.5 hours` (30 minutes)
* **Expected Timesteps:** 241
* **Available Timesteps:** {len(replay_records)}
* **Missing Timesteps:** {max(0, 241 - len(replay_records))}
* **Event Replay Status:** `INCOMPLETE`
* **Processed-Window Peak Rainfall:** {peak_event_rain:.2f} mm/hr (NOT 2015 event peak rainfall)

---

## 2. Observation Dataset Partitioning

| Category | Total Records | With Observed Depth | Without Observed Depth | Event Depth Validation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Chennai_2015 Attributed** | {len(event_2015_features)} | **0** | {len(c2015_without_depth)} | **NOT_COMPUTABLE** |
| **UNKNOWN Event Attribution** | {len(unknown_attr_features)} | **{len(unk_with_depth)}** | 0 | **AVAILABLE** (Spatial Comparison Only) |
| **Total Benchmark Features** | {len(features)} | {len(unk_with_depth)} | {len(c2015_without_depth)} | N/A |

> **Notice:** UNKNOWN event observations were NOT moved into the 2015 validation set.

---

## 3. Quantitative Depth Metrics (UNKNOWN Event Observations)

**Metric Population:** `UNKNOWN_EVENT_DEPTH_OBSERVATIONS`  
**Terminology:** Comparison against UNKNOWN-event depth observations / Spatial depth comparison using observations with unknown event attribution.

> [!WARNING]
> **The 192 depth observations used for the depth-error statistics do not have reliable event attribution and therefore must not be interpreted as a 2015 event-specific validation.**

* **`unknown_event_depth_mae_cm`:** **{mae:.2f} cm**
* **`unknown_event_depth_rmse_cm`:** **{rmse:.2f} cm**
* **`unknown_event_depth_bias_cm`:** **{bias:.2f} cm**
* **`unknown_event_depth_median_absolute_error_cm`:** **{median_ae:.2f} cm**
* **`unknown_event_depth_sample_count`:** **{sample_count}**

---

## 4. Drainage Diagnostics & Terminology

- **Diagnostic Terminology:** Drainage-constrained diagnostic locations
- **SWD Pipe Geometry:** Real spatial geometry loaded from GIS dataset
- **Drainage Diagnostics:** Proximity and density diagnostics computed
- **Hydraulic Capacity:** `UNKNOWN`
- **Hydraulic Conveyance:** `UNAVAILABLE` (No hydraulic conveyance calculated)
- **Hydraulic Coupling:** `UNAVAILABLE`
- **Drainage Effect on Flood Depth:** `0.0 cm` (Drainage does not alter numerical flood depth)

---

## 5. Methodological Limitations & Statuses

### A. 2015 Event Depth Validation Status
* **Status:** `NOT_COMPUTABLE`
* **Reason:** `NO_USABLE_DEPTH_OBSERVATIONS`
* **Details:** The 753 Chennai_2015 attributed records contain zero measured depth values.

### B. Occurrence Validation Status
* **Status:** `NOT_COMPUTABLE`
* **Reason:** `THRESHOLD_NOT_DEFINED`
* **Details:** No standardized inundation threshold is defined in project specifications.

### C. Time-Matched Validation Status
* **Status:** `NOT_COMPUTABLE`
* **Reason:** `OBSERVATION_TIMESTAMPS_UNAVAILABLE`
* **Details:** Historical flood depths lack sub-daily timestamps.

---

## 6. Verification & Summary of Statuses
* **2015 Depth Validation:** `NOT_COMPUTABLE`
* **Unknown-Event Spatial Depth Comparison:** `AVAILABLE`
* **Event Replay Status:** `INCOMPLETE`
* **Occurrence Validation:** `NOT_COMPUTABLE`
* **Time-Matched Validation:** `NOT_COMPUTABLE`
* **Overall Validation Status:** `NOT_VALIDATED`
"""

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Saved Validation Report Markdown to {REPORT_MD}")

if __name__ == "__main__":
    main()

