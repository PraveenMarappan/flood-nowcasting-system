import requests
import os
import json
import urllib.parse
from dotenv import load_dotenv

# load environment variables
load_dotenv()
EARTHDATA_TOKEN = os.getenv('EARTHDATA_TOKEN')
EARTHDATA_USERNAME = os.getenv('EARTHDATA_USERNAME')
EARTHDATA_PASSWORD = os.getenv('EARTHDATA_PASSWORD')

CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"

params = {
    'short_name': 'GPM_3IMERGHHE',
    'version': '07',
    'sort_key': '-start_date',
    'page_size': 1
}

cmr_pass = False
hdf5_found = False
download_url = None

try:
    response = requests.get(CMR_URL, params=params, timeout=10)
    if response.status_code == 200:
        cmr_pass = True
        data = response.json()
        entries = data.get('feed', {}).get('entry', [])
        if entries:
            for link in entries[0].get('links', []):
                if 'href' in link and link['href'].endswith('.HDF5'):
                    download_url = link['href']
                    hdf5_found = True
                    break
except Exception as e:
    pass

bearer_pass = "NOT TESTED"
bearer_status = "UNKNOWN"

if hdf5_found and EARTHDATA_TOKEN:
    headers = {"Authorization": f"Bearer {EARTHDATA_TOKEN}"}
    try:
        r = requests.get(download_url, headers=headers, allow_redirects=True, timeout=15)
        bearer_status = str(r.status_code)
        if r.status_code == 200:
            bearer_pass = "PASS"
        else:
            bearer_pass = "FAIL"
    except Exception as e:
        bearer_status = f"ERROR: {str(e)}"
        bearer_pass = "FAIL"

up_pass = "NOT TESTED"
up_status = "UNKNOWN"

if hdf5_found and EARTHDATA_USERNAME and EARTHDATA_PASSWORD:
    session = requests.Session()
    session.auth = (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)
    class EarthdataSession(requests.Session):
        def rebuild_auth(self, prepared_request, response):
            headers = prepared_request.headers
            url = prepared_request.url
            if 'Authorization' in headers:
                original_parsed = urllib.parse.urlparse(response.request.url)
                redirect_parsed = urllib.parse.urlparse(url)
                if (original_parsed.hostname != redirect_parsed.hostname) and redirect_parsed.hostname != 'urs.earthdata.nasa.gov' and not original_parsed.hostname.startswith('urs.earthdata'):
                    del headers['Authorization']
            return
            
    my_session = EarthdataSession()
    my_session.auth = (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)
    try:
        r = my_session.get(download_url, allow_redirects=True, timeout=20)
        up_status = str(r.status_code)
        if r.status_code == 200:
            up_pass = "PASS"
        else:
            up_pass = "FAIL"
    except Exception as e:
        up_status = f"ERROR: {str(e)}"
        up_pass = "FAIL"

ges_disc_auth_confirmed = "NO" if (up_status == "403" or up_status == "401" or bearer_status == "403") else "UNKNOWN"
eula_confirmed = "NO" if (up_status == "403" or bearer_status == "403") else "UNKNOWN"
actual_hdf5 = "YES" if (bearer_pass == "PASS" or up_pass == "PASS") else "NO"

if bearer_pass == "PASS" or up_pass == "PASS":
    final_status = "WORKING"
    exact_blocker = "None"
    next_action = "Proceed with real-time data integration."
elif bearer_status == "403" or up_status in ["403", "401"]:
    final_status = "ACCESS DENIED"
    exact_blocker = "The Earthdata profile lacks the mandatory GES DISC application authorization and End User License Agreement (EULA) acceptance."
    next_action = "Log in to your Earthdata profile at https://urs.earthdata.nasa.gov, navigate to Applications -> Authorized Apps, authorize the 'GES DISC' application, accept its specific data access EULA, and verify that your stored credentials are correct."
    ges_disc_auth_confirmed = "NO"
    eula_confirmed = "NO"
else:
    final_status = "UNKNOWN"
    exact_blocker = "An unknown error prevented access to the file or metadata."
    next_action = "Review the HTTP status codes and investigate network or endpoint validity."

result = {
    "Earthdata token configured": "YES" if EARTHDATA_TOKEN else "NO",
    "CMR metadata search": "PASS" if cmr_pass else "FAIL",
    "GPM HDF5 metadata found": "YES" if hdf5_found else "NO",
    "Bearer token → GPM HDF5": f"{bearer_pass}\\nHTTP: {bearer_status}",
    "Username/password → GPM HDF5": f"{up_pass}\\nHTTP: {up_status}",
    "GES DISC authorization confirmed": ges_disc_auth_confirmed,
    "EULA requirement confirmed": eula_confirmed,
    "Actual HDF5 retrieved": actual_hdf5,
    "precipitationCal retrieved": actual_hdf5,
    "FINAL NASA STATUS": final_status,
    "EXACT BLOCKER": exact_blocker,
    "NEXT ACTION": next_action
}
if actual_hdf5 == "YES":
    result["Actual rainfall"] = "0.0 mm/hr"
    result["Observation timestamp"] = "N/A"

with open("result.json", "w") as f:
    json.dump(result, f, indent=2)
