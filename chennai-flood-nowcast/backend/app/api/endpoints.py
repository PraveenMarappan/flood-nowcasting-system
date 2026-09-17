from fastapi import APIRouter
from pydantic import BaseModel
import csv
from pathlib import Path
from datetime import datetime

from app.services.nasa_gpm import NasaGpmService
from app.services.terrain_service import TerrainService
from app.services.drainage_coupling_service import DrainageCouplingService
from app.services.flood_model_service import FloodModelService
from app.services.forecast_service import ForecastService
from app.services.route_service import RouteService
from app.services.data_status_service import DataStatusService
from app.services.validation_service import ValidationService

router = APIRouter()
terrain_service = TerrainService()
drainage_service = DrainageCouplingService()
flood_model_service = FloodModelService()
forecast_service = ForecastService()
route_service = RouteService()
data_status_service = DataStatusService()
validation_service = ValidationService()

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
    
    return flood_model_service.calculate_current_flood(actual_rainfall, elevation_val, has_real_terrain, latitude, longitude)

@router.get("/flood/forecast")
def get_flood_forecast(rainfall: float = 0, is_simulated: bool = True, latitude: float = 13.0827, longitude: float = 80.2707):
    elev_data = terrain_service.get_elevation(latitude, longitude)
    elevation_val = elev_data.get("elevation_m")
    has_real_terrain = (elevation_val is not None and elev_data.get("status") == "REAL")
    
    current_flood = flood_model_service.calculate_current_flood(rainfall, elevation_val, has_real_terrain, latitude, longitude)
    
    forecast_data = forecast_service.generate_forecast(
        current_water_depth=current_flood["water_depth_cm"],
        current_rainfall=rainfall,
        current_status=current_flood["risk_level"],
        drainage_eval=current_flood["drainage"]
    )
    
    # Merge for endpoint compatibility
    forecast_data["water_depth_cm"] = current_flood["water_depth_cm"]
    forecast_data["is_simulated"] = is_simulated
    forecast_data["rainfall_input_mm"] = rainfall
    forecast_data["drainage"] = current_flood["drainage"]
    
    return forecast_data

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
    drainage_info = drainage_service.get_status()
    
    return data_status_service.get_status(rainfall_status, dem_status, drainage_info)

@router.get("/terrain/status")
def get_terrain_status():
    return terrain_service.get_status()

@router.get("/terrain/summary")
def get_terrain_summary():
    return terrain_service.get_summary()
    
@router.get("/terrain/elevation")
def get_terrain_elevation(latitude: float, longitude: float):
    return terrain_service.get_elevation(latitude, longitude)

@router.get("/roads/risk")
def get_roads_risk(forecast_offset: int = 0, rainfall: float = 0.0, is_simulated: bool = True):
    return route_service.get_roads_risk(forecast_offset_minutes=forecast_offset, rainfall=rainfall, is_simulated=is_simulated)

@router.get("/locations/critical")
def get_critical_locations():
    return route_service.get_critical_locations()

@router.get("/drainage/status")
def get_drainage_status():
    return drainage_service.get_status()

@router.get("/route/safer")
def get_safer_route():
    return route_service.get_safer_route()

@router.get("/flood/zones")
def get_flood_zones():
    return {
        "status": "MODELLED",
        "model_version": "baseline-v1",
        "zones": []
    }

@router.get("/flood/validation")
def get_validation_status():
    return validation_service.get_validation_metrics()
