import time
import json
from pathlib import Path
from typing import Dict, Any, List

from app.services.flood_model_service import FloodModelService
from app.services.route_service import RouteService

class ModelComparisonService:
    def __init__(self):
        self.flood_model = FloodModelService()
        self.route_service = RouteService()
        self.output_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "validation" / "results"
        self.output_file = self.output_dir / "model_comparison.json"

    def run_comparison(self, rainfall_scenarios: List[float] = None) -> Dict[str, Any]:
        if rainfall_scenarios is None:
            rainfall_scenarios = [0.0, 25.0, 50.0, 75.0, 105.0]

        # Test locations across Chennai pilot region
        sample_locations = [
            {"name": "Central Chennai (Egmore)", "lat": 13.0827, "lng": 80.2707},
            {"name": "Velachery Lowland", "lat": 12.9782, "lng": 80.2184},
            {"name": "Adyar Basin", "lat": 13.0067, "lng": 80.2570},
            {"name": "Mylapore Coastal", "lat": 13.0368, "lng": 80.2676},
            {"name": "Tambaram Outer", "lat": 12.9249, "lng": 80.1000}
        ]

        scenario_results = []

        for rain in rainfall_scenarios:
            legacy_depths = []
            grid_depths = []
            
            # 1. Point Comparison
            t0 = time.perf_counter()
            for loc in sample_locations:
                res_legacy = self.flood_model.calculate_spatial_flood(loc["lat"], loc["lng"], rain, 0, 1.0, model_version="LEGACY_HEURISTIC")
                legacy_depths.append(res_legacy["water_depth_cm"])
            t_legacy = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            for loc in sample_locations:
                res_grid = self.flood_model.calculate_spatial_flood(loc["lat"], loc["lng"], rain, 0, 1.0, model_version="GRID_HYDROLOGY_V1")
                grid_depths.append(res_grid["water_depth_cm"])
            t_grid = (time.perf_counter() - t0) * 1000.0

            # 2. Road Risk Network Comparison
            roads_legacy = self.route_service.get_roads_risk(forecast_offset_minutes=0, rainfall=rain, is_simulated=True)
            # Temporarily compute road risk with GRID_HYDROLOGY_V1
            features = self.route_service._cached_roads.get("features", []) if self.route_service._cached_roads else []
            
            grid_high_roads = 0
            grid_mod_roads = 0
            grid_low_roads = 0
            
            for f in features:
                coords = f.get("geometry", {}).get("coordinates", [])
                if not coords: continue
                lng = sum(pt[0] for pt in coords) / len(coords)
                lat = sum(pt[1] for pt in coords) / len(coords)
                grid_res = self.flood_model.calculate_spatial_flood(lat, lng, rain, 0, 1.0, model_version="GRID_HYDROLOGY_V1")
                d = grid_res["water_depth_cm"]
                if d >= 30.0: grid_high_roads += 1
                elif d >= 10.0: grid_mod_roads += 1
                elif d > 0.1: grid_low_roads += 1

            legacy_high_roads = sum(1 for f in roads_legacy.get("features", []) if f.get("properties", {}).get("risk_level") == "HIGH")
            legacy_mod_roads = sum(1 for f in roads_legacy.get("features", []) if f.get("properties", {}).get("risk_level") == "MODERATE")
            legacy_low_roads = sum(1 for f in roads_legacy.get("features", []) if f.get("properties", {}).get("risk_level") == "LOW")

            scenario_results.append({
                "rainfall_rate_mm_hr": rain,
                "legacy_heuristic": {
                    "max_depth_cm": round(max(legacy_depths), 2) if legacy_depths else 0.0,
                    "mean_depth_cm": round(sum(legacy_depths)/len(legacy_depths), 2) if legacy_depths else 0.0,
                    "high_risk_roads": legacy_high_roads,
                    "moderate_risk_roads": legacy_mod_roads,
                    "low_risk_roads": legacy_low_roads,
                    "execution_time_ms": round(t_legacy, 3)
                },
                "grid_hydrology_v1": {
                    "max_depth_cm": round(max(grid_depths), 2) if grid_depths else 0.0,
                    "mean_depth_cm": round(sum(grid_depths)/len(grid_depths), 2) if grid_depths else 0.0,
                    "high_risk_roads": grid_high_roads,
                    "moderate_risk_roads": grid_mod_roads,
                    "low_risk_roads": grid_low_roads,
                    "execution_time_ms": round(t_grid, 3)
                }
            })

        # 3. Cessation Recovery Comparison (Rain = 50 mm/hr -> 0 mm/hr forecast)
        recovery_comparison = []
        offsets = [0, 30, 60, 120, 180]
        for off in offsets:
            rec_legacy = self.flood_model.calculate_spatial_flood(13.0827, 80.2707, 50.0, off, 1.0, model_version="LEGACY_HEURISTIC")
            rec_grid = self.flood_model.calculate_spatial_flood(13.0827, 80.2707, 50.0, off, 1.0, model_version="GRID_HYDROLOGY_V1")
            recovery_comparison.append({
                "offset_minutes": off,
                "legacy_depth_cm": rec_legacy["water_depth_cm"],
                "grid_depth_cm": rec_grid["water_depth_cm"]
            })

        comparison_report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "models_compared": ["LEGACY_HEURISTIC", "GRID_HYDROLOGY_V1"],
            "validation_status": "NOT_VALIDATED",
            "scenario_results": scenario_results,
            "cessation_recovery_comparison": recovery_comparison
        }

        # Save to file
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w") as f:
            json.dump(comparison_report, f, indent=2)

        return comparison_report
