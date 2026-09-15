import requests, urllib.parse, h5py, os
from dotenv import load_dotenv

load_dotenv()
u = 'https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGHHE&page_size=1'
l = requests.get(u).json()['feed']['entry'][0]['links'][0]['href']

class EarthdataSession(requests.Session):
    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        url = prepared_request.url
        if 'Authorization' in headers:
            original_parsed = urllib.parse.urlparse(response.request.url)
            redirect_parsed = urllib.parse.urlparse(url)
            if original_parsed.hostname != redirect_parsed.hostname and \
               redirect_parsed.hostname != 'urs.earthdata.nasa.gov' and \
               not original_parsed.hostname.startswith('urs.earthdata') and \
               'nasa.gov' not in redirect_parsed.hostname and \
               'cloudfront.net' not in redirect_parsed.hostname:
                del headers['Authorization']
        return

ms = EarthdataSession()
ms.headers = {'Authorization': 'Bearer ' + os.environ['EARTHDATA_TOKEN']}
r = ms.get(l, stream=True, timeout=60)
with open('test_struct.h5', 'wb') as f:
    for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)

def f_p(n, o):
    print(n)
print("Keys inside HDF5:")
with h5py.File('test_struct.h5', 'r') as h5f:
    h5f.visititems(f_p)
