import os
import requests
import json
import base64
from pathlib import Path
try:
    import h5py
    import numpy as np
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False
import warnings

warnings.filterwarnings("ignore")

dotenv_path = Path(".env")
earthdata_user = ""
earthdata_pass = ""
earthdata_token = ""

if dotenv_path.exists():
    with open(dotenv_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k == "EARTHDATA_USERNAME":
                    earthdata_user = v
                elif k == "EARTHDATA_PASSWORD":
                    earthdata_pass = v
                elif k == "EARTHDATA_TOKEN":
                    earthdata_token = v

print("========================================")
print("GES DISC ACCESS DIAGNOSTIC")
print("========================================")
print()
print(f"Earthdata token configured: {'YES' if earthdata_token else 'NO'}")
print()

# 1. CMR Search for metadata
cmr_pass = "FAIL"
download_link = None
try:
    search_url = "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGHHE&page_size=1&sort_key=-start_date"
    r_cmr = requests.get(search_url, timeout=15)
    if r_cmr.status_code == 200:
        cmr_pass = "PASS"
        data = r_cmr.json()
        entries = data.get("feed", {}).get("entry", [])
        if entries:
            for link in entries[0].get("links", []):
                if link.get("href", "").endswith(".HDF5") and "fedsearch/1.1/data#" in link.get("rel", ""):
                    download_link = link.get("href")
                    break
except Exception:
    pass

print(f"CMR metadata search:\n{cmr_pass}")
print()
print(f"GPM HDF5 metadata found:\n{'YES' if download_link else 'NO'}")
print()

# A robust method to follow the GES DISC OAuth flow
def test_download_flow(auth_type):
    if not download_link:
        return "FAIL", "N/A"
        
    session = requests.Session()
    # Initial request to GES DISC. This will redirect to URS if not authenticated.
    response = session.get(download_link, allow_redirects=False, timeout=20)
    
    redirects = 0
    final_status = str(response.status_code)
    
    while response.is_redirect and 'Location' in response.headers and redirects < 10:
        next_url = response.headers['Location']
        if next_url.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(response.url)
            next_url = f"{parsed.scheme}://{parsed.netloc}{next_url}"
        
        headers = {}
        
        # If redirecting to URS, inject credentials
        if "urs.earthdata.nasa.gov" in next_url:
            if auth_type == "bearer" and earthdata_token:
                headers["Authorization"] = f"Bearer {earthdata_token}"
            elif auth_type == "basic" and earthdata_user and earthdata_pass:
                auth_str = base64.b64encode(f"{earthdata_user}:{earthdata_pass}".encode()).decode()
                headers["Authorization"] = f"Basic {auth_str}"
                
        response = session.get(next_url, headers=headers, allow_redirects=False, timeout=20)
        final_status = str(response.status_code)
        redirects += 1
        
    return response, final_status

# 2. Bearer Token Test
bearer_pass = "NOT TESTED"
bearer_http = "N/A"
if earthdata_token:
    try:
        resp, status = test_download_flow("bearer")
        bearer_http = status
        if status == "200" and "html" not in resp.headers.get("Content-Type", "").lower():
            bearer_pass = "PASS"
        else:
            bearer_pass = "FAIL"
    except Exception as e:
        bearer_pass = "FAIL"
        bearer_http = f"Error: {e}"

print(f"Bearer token -> GPM HDF5:\n{bearer_pass}")
print(f"HTTP: {bearer_http}")
print()

# 3. Username/Password Test
up_pass = "NOT TESTED"
up_http = "N/A"
actual_retrieved = "NO"
temp_file = Path("temp_gesdisc.h5")

if earthdata_user and earthdata_pass:
    try:
        resp, status = test_download_flow("basic")
        up_http = status
        if status == "200" and "html" not in resp.headers.get("Content-Type", "").lower():
            up_pass = "PASS"
            with open(temp_file, "wb") as f:
                f.write(resp.content)
            actual_retrieved = "YES"
        else:
            up_pass = "FAIL"
    except Exception as e:
        up_pass = "FAIL"
        up_http = f"Error: {e}"

print(f"Username/password -> GPM HDF5:\n{up_pass}")
print(f"HTTP: {up_http}")
print()

# Check EULA / Authorization Requirement
ges_disc_auth = "UNKNOWN"
eula_auth = "UNKNOWN"
blocker = "Unknown blocker"
next_action = "Investigate further"
final_status = "UNKNOWN"

if bearer_http == "403" and up_http == "403":
    # 403 from GES DISC after authentication usually means EULA not accepted
    ges_disc_auth = "NO"
    eula_auth = "LIKELY NOT ACCEPTED"
    final_status = "ACCESS DENIED"
    blocker = "Both authentication methods trigger a 403 Forbidden at the data endpoint, likely indicating that the Earthdata profile lacks the mandatory GES DISC application authorization and End User License Agreement (EULA) acceptance."
    next_action = "Log in to your Earthdata profile at https://urs.earthdata.nasa.gov, navigate to Applications -> Authorized Apps, authorize 'GES DISC', accept its specific data access EULA, and verify that your stored credentials are correct."
elif up_http == "401":
    # Basic auth to URS failed entirely
    ges_disc_auth = "NO"
    eula_auth = "UNKNOWN"
    final_status = "AUTHENTICATION FAILED"
    blocker = "Earthdata username/password authentication returned 401 Unauthorized, suggesting incorrect credentials or missing 'GES DISC' app binding in Earthdata Login."
    next_action = "Verify the EARTHDATA_USERNAME and EARTHDATA_PASSWORD in .env match your current active Earthdata account."
elif bearer_http == "401":
    # Bearer auth to URS failed entirely
    ges_disc_auth = "NO"
    eula_auth = "UNKNOWN"
    final_status = "AUTHENTICATION FAILED"
    blocker = "Bearer token authentication returned 401 Unauthorized."
    next_action = "Generate a new valid Earthdata token."
elif actual_retrieved == "YES":
    ges_disc_auth = "YES"
    eula_auth = "YES"
    final_status = "WORKING"
    blocker = "None"
    next_action = "Proceed with using successful authentication method for real-time app integration."

# 4. Check contents if retrieved
var_retrieved = "NOT RETRIEVED"
rainfall_val = None
rainfall_unit = ""
granule_time = None

if actual_retrieved == "YES" and temp_file.exists():
    if HAS_H5PY:
        try:
            with h5py.File(temp_file, "r") as h5f:
                if "Grid" in h5f and "precipitationCal" in h5f["Grid"]:
                    var_retrieved = "precipitationCal"
                    grid = h5f["Grid"]
                    lats = grid["lat"][:]
                    lons = grid["lon"][:]
                    precip = grid["precipitationCal"][0, :, :]
                    
                    lat_used, lon_used = 13.0827, 80.2707
                    lat_idx = (np.abs(lats - lat_used)).argmin()
                    lon_idx = (np.abs(lons - lon_used)).argmin()
                    
                    val = precip[lon_idx, lat_idx]
                    if val < 0 or np.isnan(val):
                        val = 0.0
                    rainfall_val = float(val)
                    rainfall_unit = "mm/hr"
                    
                    granule_time = h5f.attrs.get('FileHeader', b'').decode('utf-8', errors='ignore')
                    granule_time = granule_time.split('StartGranuleDateTime=')[1].split(';')[0] if 'StartGranuleDateTime=' in granule_time else "Unknown"
        except Exception as e:
            var_retrieved = f"NOT RETRIEVED (Error parsing HDF5: {e})"
    else:
        var_retrieved = "NOT RETRIEVED (h5py/numpy missing)"

print(f"GES DISC authorization confirmed:\n{ges_disc_auth}")
print()
print(f"EULA requirement confirmed:\n{eula_auth}")
print()
print(f"Actual HDF5 retrieved:\n{actual_retrieved}")
print()
print(f"precipitationCal retrieved:\n{'YES' if var_retrieved == 'precipitationCal' else 'NO'}")
print()
if rainfall_val is not None:
    print(f"Actual rainfall:\n{rainfall_val} {rainfall_unit}")
    print()
    print(f"Observation timestamp:\n{granule_time}")
    print()

print(f"FINAL NASA STATUS:\n{final_status}")
print()
print(f"EXACT BLOCKER:\n{blocker}")
print()
print(f"NEXT ACTION:\n{next_action}")

if temp_file.exists():
    temp_file.unlink()
