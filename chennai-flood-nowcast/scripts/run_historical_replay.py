import sys
import csv
import json
from pathlib import Path
from datetime import datetime

# Add backend directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.flood_model_service import FloodModelService

FORCING_CSV = ROOT_DIR / "data" / "forcing" / "historical" / "processed" / "chennai_2015_imerg_timeseries.csv"
RESULTS_DIR = ROOT_DIR / "data" / "validation" / "results"
RESULTS_CSV = RESULTS_DIR / "historical_replay_timeseries.csv"

# Chennai central coordinate
TARGET_LAT = 13.0827
TARGET_LON = 80.2707

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not FORCING_CSV.exists():
        print(f"ERROR: Forcing CSV not found at {FORCING_CSV}")
        sys.exit(1)
        
    records = []
    with open(FORCING_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            
    print(f"Loaded {len(records)} forcing timesteps from {FORCING_CSV.name}")
    
    model = FloodModelService()
    replay_results = []
    
    for idx, rec in enumerate(records):
        ts_utc = rec["timestamp_utc"]
        rain_mm_hr = float(rec["rainfall_mm_hr"])
        
        # Calculate spatial flood depth using existing FloodModelService with 0.5hr timestep
        calc = model.calculate_spatial_flood(
            latitude=TARGET_LAT,
            longitude=TARGET_LON,
            rainfall_mm_hr=rain_mm_hr,
            forecast_offset_minutes=0,
            timestep_hours=0.5
        )
        
        predicted_depth_cm = round(float(calc.get("water_depth_cm", 0.0)), 2)
        model_status = calc.get("status", "MODELLED")
        model_version = calc.get("model_version", "baseline-v1")
        
        replay_results.append({
            "timestamp_utc": ts_utc,
            "rainfall_mm_hr": rain_mm_hr,
            "predicted_depth_cm": predicted_depth_cm,
            "model_status": model_status,
            "model_version": model_version,
            "timestep_hours": 0.5
        })
        
    # Save replay timeseries CSV
    fieldnames = [
        "timestamp_utc", "rainfall_mm_hr", "predicted_depth_cm",
        "model_status", "model_version", "timestep_hours"
    ]
    
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(replay_results)
        
    print(f"Saved replay timeseries to {RESULTS_CSV} ({len(replay_results)} records).")
    
    depths = [r["predicted_depth_cm"] for r in replay_results]
    max_depth = max(depths) if depths else 0.0
    mean_depth = sum(depths) / len(depths) if depths else 0.0
    
    print("\nREPLAY SUMMARY:")
    print(f"  - Total Timesteps: {len(replay_results)}")
    print(f"  - Max Predicted Depth: {max_depth} cm")
    print(f"  - Mean Predicted Depth: {mean_depth:.2f} cm")

if __name__ == "__main__":
    main()
