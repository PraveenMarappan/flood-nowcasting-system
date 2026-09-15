from fastapi import APIRouter
from pydantic import BaseModel
import time
import csv
import os
from pathlib import Path
from datetime import datetime
from app.services.nasa_gpm import NasaGpmService

router = APIRouter()

class ForecastQuery(BaseModel):
    rainfall: int = 0

@router.get("/rainfall/current")
async def get_current_rainfall():
    service = NasaGpmService()
    result = await service.fetch_latest_precipitation()
    
    base_dir = Path(__file__).parent.parent.parent.parent / "data"
    raw_dir = base_dir / "raw"
    csv_file = raw_dir / "rainfall_history.csv"
    
    if result.get("status") == "LIVE":
        val = result.get("rainfall_rate", 0)
        source = result.get("source", "NASA GPM IMERG Early Run")
        status = result.get("status", "LIVE")
        
        raw_dir.mkdir(parents=True, exist_ok=True)
        file_exists = csv_file.exists()
        try:
            with open(csv_file, mode="a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["timestamp", "rainfall_rate_mm_hr", "source", "status", "data_timestamp"])
                writer.writerow([datetime.utcnow().isoformat() + "Z", val, source, status, result.get("data_timestamp", "")])
        except Exception as e:
            print("Error saving history", e)
    elif result.get("status") == "UNAVAILABLE":
        # Fallback to STALE if history exists
        if csv_file.exists():
            try:
                with open(csv_file, mode="r") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        last_row = rows[-1]
                        result = {
                            "status": "STALE",
                            "source": last_row["source"],
                            "rainfall_rate": float(last_row["rainfall_rate_mm_hr"]),
                            "data_timestamp": last_row.get("data_timestamp", last_row["timestamp"]),
                            "retrieved_at": last_row["timestamp"],
                            "error": result.get("error", "NASA DATA UNAVAILABLE")
                        }
            except Exception as e:
                print("Error reading history", e)
            
    return result

@router.get("/rainfall/history")
async def get_rainfall_history():
    base_dir = Path(__file__).parent.parent.parent.parent / "data"
    csv_file = base_dir / "raw" / "rainfall_history.csv"
    
    if not csv_file.exists():
        return {"history": []}
        
    history = []
    try:
        with open(csv_file, mode="r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append({
                    "timestamp": row["timestamp"],
                    "rainfall_rate": float(row["rainfall_rate_mm_hr"]),
                    "source": row["source"],
                    "status": row["status"]
                })
    except Exception as e:
        return {"error": str(e), "history": []}
        
    return {"history": history[-50:]}

@router.get("/flood/forecast")
def get_flood_forecast(rainfall: float = 0, is_simulated: bool = True):
    status = "NORMAL"
    water_depth = 0
    if rainfall > 100:
        status = "CRITICAL"
        water_depth = rainfall * 0.8
    elif rainfall > 50:
        status = "FLOOD"
        water_depth = rainfall * 0.5
    elif rainfall > 20:
        status = "WATCH"
        water_depth = rainfall * 0.1
    elif rainfall == 0:
        status = "RECOVERY"
        water_depth = 5 
        
    if rainfall == 0 and water_depth <= 5:
        status = "NORMAL"
        water_depth = 0

    return {
        "status": status,
        "water_depth_cm": water_depth,
        "is_simulated": is_simulated,
        "rainfall_input_mm": rainfall,
        "forecast": [
            {"time": "+30m", "status": status, "depth": water_depth * 0.9 if rainfall ==0 else water_depth + (rainfall*0.1)},
            {"time": "+60m", "status": status, "depth": water_depth * 0.7 if rainfall ==0 else water_depth + (rainfall*0.2)},
            {"time": "+90m", "status": "RECOVERY" if rainfall == 0 else status, "depth": water_depth * 0.5 if rainfall ==0 else max(water_depth, 10)},
            {"time": "+120m", "status": "RECOVERY" if rainfall == 0 else status, "depth": max(0, water_depth*0.2) if rainfall ==0 else max(water_depth, 10)},
            {"time": "+150m", "status": "NORMAL" if rainfall == 0 else status, "depth": 0 if rainfall == 0 else max(water_depth, 10)},
            {"time": "+180m", "status": "NORMAL" if rainfall == 0 else status, "depth": 0 if rainfall == 0 else max(water_depth, 10)},
        ]
    }

@router.get("/data-status")
def get_data_status():
    rainfall_status = "UNAVAILABLE"
    
    base_dir = Path(__file__).parent.parent.parent.parent / "data"
    csv_file = base_dir / "raw" / "rainfall_history.csv"
    if csv_file.exists():
        try:
            with open(csv_file, mode="r") as f:
                reader = list(csv.DictReader(f))
                if reader:
                    last_status = reader[-1].get("status", "UNAVAILABLE")
                    if last_status == "LIVE":
                        rainfall_status = "REAL"
                    elif last_status == "STALE":
                        rainfall_status = "STALE"
        except Exception:
            pass

    return {
        "overall_health": "OK",
        "sources": {
            "rainfall": {"status": rainfall_status, "source": "NASA GPM IMERG"},
            "flood_depth": {"status": "MODELLED", "source": "Hydrological Model"},
            "dem_terrain": {"status": "ESTIMATED", "source": "Static Baseline"},
            "drainage": {"status": "SIMULATED", "source": "Rule-based mock"},
        }
    }

@router.get("/roads/risk")
def get_roads_risk():
    return {
        "is_simulated": True,
        "roads": [
            {"id": 1, "name": "Mount Road", "risk": "MODERATE", "depth_cm": 15, "coords": [[13.0658, 80.2642], [13.0450, 80.2450]]},
            {"id": 2, "name": "OMR IT Expressway", "risk": "LOW", "depth_cm": 5, "coords": [[12.9800, 80.2450], [12.9000, 80.2250]]},
            {"id": 3, "name": "Velachery Main Road", "risk": "HIGH", "depth_cm": 45, "coords": [[12.9850, 80.2200], [12.9700, 80.2150]]},
            {"id": 4, "name": "GST Road", "risk": "SAFE", "depth_cm": 0, "coords": [[13.0100, 80.2000], [12.9500, 80.1400]]},
            {"id": 5, "name": "ECR", "risk": "CRITICAL", "depth_cm": 70, "coords": [[12.9850, 80.2600], [12.9200, 80.2400]]},
        ]
    }


@router.get("/locations/critical")
def get_critical_locations():
    return {
        "is_simulated": True,
        "locations": [
            {"id": 1, "name": "Apollo Hospital", "type": "Hospital", "risk": "MODERATE", "status": "ACCESSIBLE", "depth_cm": 10, "lat": 13.0604, "lng": 80.2496},
            {"id": 2, "name": "Chennai Central", "type": "Transport Hub", "risk": "HIGH", "status": "WATCH", "depth_cm": 35, "lat": 13.0827, "lng": 80.2757},
            {"id": 3, "name": "Velachery Fire Station", "type": "Fire Station", "risk": "CRITICAL", "status": "IMPAIRED", "depth_cm": 60, "lat": 12.9774, "lng": 80.2223},
        ]
    }

@router.get("/drainage/status")
def get_drainage_status():
    return {
        "is_simulated": True,
        "drainage": {
            "load_percentage": 75,
            "capacity": "Stressed",
            "overflow_risk": "High",
            "choke_points": 3
        }
    }

@router.get("/route/safer")
def get_safer_route():
    return {
        "is_simulated": True,
        "message": "Routing via safe corridors (avoiding Velachery)",
        "waypoints": [
            [13.0827, 80.2757],
            [13.0604, 80.2496],
            [13.0400, 80.2200]
        ]
    }
