import requests
import os
import json
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("EARTHDATA_TOKEN", "")
user = os.getenv("EARTHDATA_USERNAME", "")
passwd = os.getenv("EARTHDATA_PASSWORD", "")

def run_diagnostics():
    re_dict = {}

    # CMR Metadata Request
    cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGHHE&page_size=1&sort_key=-start_date"
    hdf5_url = None
    try:
        r_cmr = requests.get(cmr_url, timeout=10)
        re_dict['cmr_pass'] = "PASS" if r_cmr.status_code == 200 else "FAIL"
        
        if r_cmr.status_code == 200:
            entries = r_cmr.json().get('feed', {}).get('entry', [])
            if entries:
                for link in entries[0].get('links', []):
                    if link.get('href', '').endswith('.HDF5'):
                        hdf5_url = link['href']
                        break
        re_dict['imerg_pass'] = "PASS" if hdf5_url else "FAIL"
        re_dict['url_valid'] = "VALID" if hdf5_url and "gesdisc" in hdf5_url.lower() or hdf5_url else "INVALID"
    except Exception as e:
        re_dict['cmr_pass'] = "FAIL"
        re_dict['imerg_pass'] = "FAIL"
        re_dict['url_valid'] = "INVALID"

    # HDF5 Test variables
    bearer_pass = "FAIL"
    resp_status = "UNKNOWN"
    content_type = "UNKNOWN"
    redirect_occurred = "NO"
    final_host = "UNKNOWN"
    server_error = "None"
    actual_hdf5 = "NO"

    if hdf5_url and token:
        try:
            # Bearer token test without following redirect first
            headers = {"Authorization": f"Bearer {token}", "Range": "bytes=0-1024"}
            initial_req = requests.get(hdf5_url, headers=headers, allow_redirects=False, timeout=10)
            redirect_occurred = "YES" if initial_req.is_redirect else "NO"
            
            # Follow redirects manually to track host and status
            current_url = hdf5_url
            response = initial_req
            redirects = 0
            
            while response.is_redirect and redirects < 5:
                next_url = response.headers.get("Location")
                if next_url.startswith("/"):
                    parsed = urlparse(current_url)
                    next_url = f"{parsed.scheme}://{parsed.netloc}{next_url}"
                
                # Check if we should forward the header
                # We forward Bearer if staying on GES DISC, or if NASA endpoints? Actually, usually you just send it.
                next_host = urlparse(next_url).netloc
                req_headers = {"Range": "bytes=0-1024"}
                
                # URS usually uses Basic, but for Bearer test we keep Bearer
                req_headers["Authorization"] = f"Bearer {token}"
                
                response = requests.get(next_url, headers=req_headers, allow_redirects=False, timeout=10)
                current_url = next_url
                redirects += 1

            resp_status = str(response.status_code)
            content_type = response.headers.get("Content-Type", "UNKNOWN")
            final_host = urlparse(current_url).netloc
            
            # Extract error if 403
            if response.status_code in [403, 401]:
                server_error = response.text[:500].replace("\n", " ") if response.text else "No error body"
                bearer_pass = "FAIL"
            elif response.status_code in [200, 206]:
                bearer_pass = "PASS"
                if "html" not in content_type:
                    actual_hdf5 = "YES"
            else:
                bearer_pass = "FAIL"
                
        except Exception as e:
            server_error = str(e)
            bearer_pass = "FAIL"
            resp_status = f"ERROR: {str(e)}"

    re_dict['bearer_pass'] = bearer_pass
    re_dict['hdf5_status'] = resp_status
    re_dict['content_type'] = content_type
    re_dict['redirect'] = redirect_occurred
    re_dict['final_host'] = final_host
    re_dict['server_error'] = server_error
    re_dict['actual_hdf5'] = actual_hdf5

    with open("final_auth_test.json", "w") as f:
        json.dump(re_dict, f, indent=2)

if __name__ == "__main__":
    run_diagnostics()
