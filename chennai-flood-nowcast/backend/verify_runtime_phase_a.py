import json
import urllib.request

BASE_URL = "http://127.0.0.1:8000"

def get_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def run_tests():
    print("=== STARTING RUNTIME VERIFICATION ===")
    
    # 1. Primary Endpoint Check
    diag_url = f"{BASE_URL}/api/drainage/diagnostics?latitude=13.0827&longitude=80.2707"
    diag = get_json(diag_url)
    print("\n1. Primary API Response Schema Verification:")
    print(f"Status: {diag.get('status')}")
    print(f"Mode: {diag.get('mode')}")
    print(f"Coverage Status: {diag.get('coverage', {}).get('status')} ({diag.get('coverage', {}).get('nearest_swd_distance_m')} m)")
    print(f"Density (km/km2): {diag.get('density', {}).get('density_km_per_km2')}")
    print(f"DBI Value: {diag.get('dbi', {}).get('value')} (Status: {diag.get('dbi', {}).get('status')})")
    print(f"DBI d_ref provenance: {diag.get('dbi', {}).get('d_ref_provenance')}")
    print(f"Alignment alpha_align: {diag.get('alignment', {}).get('alpha_align')}")
    
    h_status = diag.get('hydraulic_data_status', {})
    print("Hydraulic Status Fields:")
    for k, v in h_status.items():
        print(f"  - {k}: {v}")
        assert v == "UNKNOWN", f"Expected UNKNOWN for {k}, got {v}"
        
    s_guarantees = diag.get('safety_guarantees', {})
    print(f"Drainage Effect on Flood Depth: {s_guarantees.get('drainage_effect_on_flood_depth')}")
    print(f"Hydraulic Coupling: {s_guarantees.get('hydraulic_coupling')}")
    
    assert diag.get('status') == "AVAILABLE"
    assert diag.get('mode') == "GEOMETRIC_ONLY"
    assert isinstance(diag.get('coverage', {}).get('nearest_swd_distance_m'), (int, float))
    assert isinstance(diag.get('density', {}).get('density_km_per_km2'), (int, float))
    assert diag.get('dbi', {}).get('d_ref_provenance') == "ASSUMED_NORMALIZATION_CONSTANT"
    assert s_guarantees.get('drainage_effect_on_flood_depth') == 0.0
    assert s_guarantees.get('hydraulic_coupling') == "UNAVAILABLE"
    print("-> PRIMARY SCHEMA CHECK: PASSED")
    
    # 2. Spatial Variability Check (3 coordinates)
    coords = [
        ("Central Chennai", 13.0827, 80.2707),
        ("T. Nagar", 13.0400, 80.2400),
        ("Outer West", 13.0000, 80.1200)
    ]
    print("\n2. Testing Spatial Variability across 3 Coordinates:")
    results = []
    for name, lat, lng in coords:
        res = get_json(f"{BASE_URL}/api/drainage/diagnostics?latitude={lat}&longitude={lng}")
        dist = res['coverage']['nearest_swd_distance_m']
        dens = res['density']['density_km_per_km2']
        dbi_val = res['dbi']['value']
        status = res['coverage']['status']
        print(f"  [{name}] Lat: {lat}, Lng: {lng} -> Dist: {dist}m, Coverage: {status}, Density: {dens} km/km2, DBI: {dbi_val}")
        results.append((dist, dens))
        
    # Verify spatial variation
    assert results[0][0] != results[2][0] or results[0][1] != results[2][1], "Spatial diagnostics did not vary between coordinates!"
    print("-> SPATIAL VARIABILITY CHECK: PASSED")
    
    # 3. Flood Depth Invariance Check
    print("\n3. Testing Flood Depth Invariance (Before vs After Diagnostics):")
    flood_before = get_json(f"{BASE_URL}/api/flood/current")
    _ = get_json(f"{BASE_URL}/api/drainage/diagnostics?latitude=13.0827&longitude=80.2707")
    flood_after = get_json(f"{BASE_URL}/api/flood/current")
    
    depth_before = flood_before.get('water_depth_cm')
    depth_after = flood_after.get('water_depth_cm')
    print(f"  Flood Depth Before Diagnostics: {depth_before} cm")
    print(f"  Flood Depth After Diagnostics:  {depth_after} cm")
    assert depth_before == depth_after, f"Flood depth changed! Before: {depth_before}, After: {depth_after}"
    print("-> FLOOD DEPTH INVARIANCE CHECK: PASSED")
    
    # 4. Road Risk Behavior Check
    print("\n4. Testing Road Risk Behavior (0 mm/hr vs 75 mm/hr):")
    roads_0 = get_json(f"{BASE_URL}/api/roads/risk?rainfall_mm_hr=0")
    roads_75 = get_json(f"{BASE_URL}/api/roads/risk?rainfall_mm_hr=75")
    
    features_0 = roads_0.get('features', [])
    features_75 = roads_75.get('features', [])
    print(f"  Road Feature Count (0 mm/hr): {len(features_0)}")
    print(f"  Road Feature Count (75 mm/hr): {len(features_75)}")
    assert len(features_0) > 0 and len(features_75) > 0, "Road features missing!"
    
    risks_0 = set(f['properties'].get('risk_level') for f in features_0)
    risks_75 = set(f['properties'].get('risk_level') for f in features_75)
    print(f"  Risk levels at 0 mm/hr:  {risks_0}")
    print(f"  Risk levels at 75 mm/hr: {risks_75}")
    assert 'NORMAL' in risks_0 or 'LOW' in risks_0
    assert 'HIGH' in risks_75 or 'CRITICAL' in risks_75
    print("-> ROAD RISK BEHAVIOR CHECK: PASSED")
    
    print("\n=== ALL BACKEND RUNTIME TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_tests()
