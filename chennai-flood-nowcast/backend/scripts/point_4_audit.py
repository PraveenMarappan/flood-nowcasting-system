from app.services.flood_model_service import FloodModelService
from app.services.terrain_service import TerrainService
import sys

def run_audit():
    flood_service = FloodModelService()
    terrain_service = TerrainService()

    # Two distinct points in Chennai (one low elevation, one higher elevation)
    loc_1 = (13.0827, 80.2707) # Near Central (lower)
    loc_2 = (13.0102, 80.2158) # Guindy (higher)

    rainfall = 50.0  # 50 mm/hr
    forecast_offset = 0

    print("--- 4. FLOOD GRID AUDIT ---")
    
    for idx, loc in enumerate([loc_1, loc_2], start=1):
        try:
            # Query terrain directly for proof
            terrain = terrain_service.get_derivatives(loc[0], loc[1])
            elev = terrain.get('elevation_m', 'N/A')
            factor = terrain.get('flow_accumulation_modifier', 'N/A')
            
            # Query flood model
            flood = flood_service.calculate_spatial_flood(loc[0], loc[1], rainfall, forecast_offset)
            
            # Determine Risk
            depth = flood.get('water_depth_cm', -1)
            risk = "GRAY"
            if depth >= 0:
                if depth < 10: risk = "GREEN (LOW)"
                elif depth < 30: risk = "ORANGE (MODERATE)"
                else: risk = "RED (HIGH)"
                
            print(f"Location {idx}: {loc}")
            print(f"  Grid Elevation: {elev} m")
            print(f"  Terrain Accumulation Factor: {factor}")
            print(f"  Flood Depth (max_depth_cm): {depth} cm")
            print(f"  Risk Level: {risk}")
            print("-" * 30)
            
        except Exception as e:
            print(f"Location {idx} Error: {e}")

if __name__ == "__main__":
    run_audit()
