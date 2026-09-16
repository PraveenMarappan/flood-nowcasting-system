from fastapi import APIRouter
from pydantic import BaseModel
import time
import csv
import os
from pathlib import Path
from datetime import datetime
from app.services.nasa_gpm import NasaGpmService
from app.services.terrain_service import TerrainService
from app.services.drainage_coupling_service import DrainageCouplingService

router = APIRouter()
terrain_service = TerrainService()
drainage_service = DrainageCouplingService()

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

@router.get("/flood/current")
async def get_current_flood(latitude: float = 13.0827, longitude: float = 80.2707):
    # Fetch real rainfall
    rainfall_data = await get_current_rainfall()
    
    if rainfall_data.get("status") not in ["LIVE", "STALE"]:
        return {
            "status": "UNAVAILABLE",
            "source": "Hydrological Model",
            "error": "Rainfall data unavailable",
            "location": {"latitude": latitude, "longitude": longitude}
        }
        
    actual_rainfall = rainfall_data.get("rainfall_rate", 0.0)
    
    # Fetch real elevation
    elev_data = terrain_service.get_elevation(latitude, longitude)
    
    elevation_val = elev_data.get("elevation_m")
    has_real_terrain = (elevation_val is not None and elev_data.get("status") == "REAL")
    
    risk_level = "NORMAL"
    water_depth = 0
    
    # Very basic prototype hydrological/rule-based model integration 
    # using REAL DEM if available.
    terrain_factor = 1.0 # Default multiplier
    if has_real_terrain:
        if elevation_val < 5:
            terrain_factor = 1.8 # Low-lying area
        elif elevation_val < 15:
            terrain_factor = 1.2
        else:
            terrain_factor = 0.5 # Higher ground, less depth gathering
            
    if actual_rainfall > 100:
        risk_level = "CRITICAL"
        water_depth = actual_rainfall * 0.8 * terrain_factor
    elif actual_rainfall > 50:
        risk_level = "FLOOD"
        water_depth = actual_rainfall * 0.5 * terrain_factor
    elif actual_rainfall > 20:
        risk_level = "WATCH"
        water_depth = actual_rainfall * 0.1 * terrain_factor
    elif actual_rainfall == 0:
        risk_level = "RECOVERY"
        water_depth = 5 * terrain_factor
        
    if actual_rainfall == 0 and water_depth <= 5:
        risk_level = "NORMAL"
        water_depth = 0

    drainage_evaluation = drainage_service.evaluate_drainage_influence(latitude, longitude, water_depth)

    return {
        "status": "MODELLED",
        "source": "Hydrological Model",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "water_depth_cm": round(water_depth, 2),
        "risk_level": risk_level,
        "rainfall_rate_mm_hr": actual_rainfall,
        "terrain_elevation_m": elevation_val if has_real_terrain else None,
        "drainage": drainage_evaluation
    }

@router.get("/flood/forecast")
def get_flood_forecast(rainfall: float = 0, is_simulated: bool = True, latitude: float = 13.0827, longitude: float = 80.2707):
    # Fetch real elevation if available
    elev_data = terrain_service.get_elevation(latitude, longitude)
    
    elevation_val = elev_data.get("elevation_m")
    has_real_terrain = (elevation_val is not None and elev_data.get("status") == "REAL")
    
    status = "NORMAL"
    water_depth = 0
    
    # Very basic prototype hydrological/rule-based model integration 
    # using REAL DEM if available.
    # Lower elevation -> higher baseline susceptibility to water depth
    terrain_factor = 1.0 # Default multiplier
    if has_real_terrain:
        if elevation_val < 5:
            terrain_factor = 1.8 # Low-lying area
        elif elevation_val < 15:
            terrain_factor = 1.2
        else:
            terrain_factor = 0.5 # Higher ground, less depth gathering
            
    if rainfall > 100:
        status = "CRITICAL"
        water_depth = rainfall * 0.8 * terrain_factor
    elif rainfall > 50:
        status = "FLOOD"
        water_depth = rainfall * 0.5 * terrain_factor
    elif rainfall > 20:
        status = "WATCH"
        water_depth = rainfall * 0.1 * terrain_factor
    elif rainfall == 0:
        status = "RECOVERY"
        water_depth = 5 * terrain_factor
        
    if rainfall == 0 and water_depth <= 5:
        status = "NORMAL"
        water_depth = 0

    drainage_evaluation = drainage_service.evaluate_drainage_influence(latitude, longitude, water_depth)

    return {
        "status": status,
        "water_depth_cm": water_depth,
        "is_simulated": is_simulated,
        "rainfall_input_mm": rainfall,
        "drainage": drainage_evaluation,
        "forecast": [
            {
                "time": "+30m", 
                "status": status, 
                "depth": water_depth * 0.9 if rainfall ==0 else water_depth + (rainfall*0.1),
                "drainage_influence": drainage_evaluation["numerical_influence"]
            },
            {
                "time": "+60m", 
                "status": status, 
                "depth": water_depth * 0.7 if rainfall ==0 else water_depth + (rainfall*0.2),
                "drainage_influence": drainage_evaluation["numerical_influence"]
            },
            {
                "time": "+90m", 
                "status": "RECOVERY" if rainfall == 0 else status, 
                "depth": water_depth * 0.5 if rainfall ==0 else max(water_depth, 10),
                "drainage_influence": drainage_evaluation["numerical_influence"]
            },
            {
                "time": "+120m", 
                "status": "RECOVERY" if rainfall == 0 else status, 
                "depth": max(0, water_depth*0.2) if rainfall ==0 else max(water_depth, 10),
                "drainage_influence": drainage_evaluation["numerical_influence"]
            },
            {
                "time": "+150m", 
                "status": "NORMAL" if rainfall == 0 else status, 
                "depth": 0 if rainfall == 0 else max(water_depth, 10),
                "drainage_influence": drainage_evaluation["numerical_influence"]
            },
            {
                "time": "+180m", 
                "status": "NORMAL" if rainfall == 0 else status, 
                "depth": 0 if rainfall == 0 else max(water_depth, 10),
                "drainage_influence": drainage_evaluation["numerical_influence"]
            },
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

    terrain_info = terrain_service.get_status()
    dem_status = terrain_info.get("status", "UNAVAILABLE")
    if dem_status == "UNAVAILABLE":
        dem_status_label = "UNAVAILABLE"
    else:
        dem_status_label = "REAL"

    drainage_info = drainage_service.get_status()
    drainage_status = "PARTIAL / ESTIMATED" if drainage_info.get("status") == "PARTIAL" else "UNAVAILABLE"
    drainage_source = drainage_info.get("source", "Chennai Drainage GeoJSON")

    return {
        "overall_health": "OK",
        "sources": {
            "rainfall": {"status": rainfall_status, "source": "NASA GPM IMERG"},
            "flood_depth": {"status": "MODELLED", "source": "Hydrological Model"},
            "dem_terrain": {"status": dem_status_label, "source": terrain_info.get("source", "SRTM DEM")},
            "drainage": {"status": drainage_status, "source": drainage_source},
        }
    }

@router.get("/terrain/status")
def get_terrain_status():
    return terrain_service.get_status()

@router.get("/terrain/summary")
def get_terrain_summary():
    return terrain_service.get_status()
    
@router.get("/terrain/elevation")
def get_terrain_elevation(latitude: float, longitude: float):
    return terrain_service.get_elevation(latitude, longitude)

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
    return drainage_service.get_status()

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
