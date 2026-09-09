from fastapi import APIRouter
from pydantic import BaseModel
import time

router = APIRouter()

# Base model examples for mock responses
class ForecastQuery(BaseModel):
    rainfall: int = 0

@router.get("/flood/forecast")
def get_flood_forecast(rainfall: int = 0):
    # Rule based simple logical mapping
    # Assuming baseline data if rainfall is provided via simulation
    # 0 = NORMAL, >20 WATCH, >50 FLOOD, >100 CRITICAL
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
        water_depth = 5 # simulated gradual recession
        
    if rainfall == 0 and water_depth == 0:
        status = "NORMAL"

    return {
        "status": status,
        "water_depth_cm": water_depth,
        "is_simulated": True,
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
