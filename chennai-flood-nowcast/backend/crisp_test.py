import requests
import os
from dotenv import load_dotenv

load_dotenv()
EARTHDATA_TOKEN = os.getenv('EARTHDATA_TOKEN')
EARTHDATA_USERNAME = os.getenv('EARTHDATA_USERNAME')
EARTHDATA_PASSWORD = os.getenv('EARTHDATA_PASSWORD')

# 1. search cmr
cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGHHE&page_size=1&sort_key=-start_date"
try:
    r = requests.get(cmr_url, timeout=10)
    data = r.json()
    entries = data.get('feed', {}).get('entry', [])
    download_link = next((link['href'] for link in entries[0]['links'] if link['href'].endswith('.HDF5')), None)
except Exception:
    download_link = None

# A manual redirect follower to avoid session hanging
def check_url(headers, auth=None):
    url = download_link
    for _ in range(10):
        try:
            r = requests.get(url, headers=headers, auth=auth, allow_redirects=False, timeout=10)
            if r.status_code in (301, 302, 303, 307, 308):
                url = r.headers['Location']
                # If relative
                if url.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(r.url)
                    url = f"{parsed.scheme}://{parsed.netloc}{url}"
                # If redirected to URS, drop headers except if handling basic auth? 
                # actually requests handles auth per host if we don't supply it globally.
                # Here we supply it explicitly if host matches.
                if 'urs.earthdata.nasa.gov' in url and auth:
                    # we will let requests handle basic auth by passing it again
                    pass
                else:
                    auth = None # drop auth for external urls
            else:
                return r.status_code
        except Exception as e:
            return f"Error: {e}"
    return "Error: Too many redirects"

bearer_status = "UNKNOWN"
if download_link and EARTHDATA_TOKEN:
    bearer_status = str(check_url({'Authorization': f'Bearer {EARTHDATA_TOKEN}'}))

up_status = "UNKNOWN"
if download_link and EARTHDATA_USERNAME and EARTHDATA_PASSWORD:
    up_status = str(check_url({}, auth=(EARTHDATA_USERNAME, EARTHDATA_PASSWORD)))

import json
result = {
    'bearer': bearer_status,
    'up': up_status,
    'link': download_link
}
with open('crisp_result.json', 'w') as f:
    json.dump(result, f)
