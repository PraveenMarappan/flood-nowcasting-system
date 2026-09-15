import os
import asyncio
import logging
import datetime
from pathlib import Path
import requests

import numpy as np
import h5py

logger = logging.getLogger(__name__)

class NasaGpmService:
    def __init__(self):
        self.username = os.getenv("EARTHDATA_USERNAME", "")
        self.password = os.getenv("EARTHDATA_PASSWORD", "")
        self.short_name = "GPM_3IMERGHHE" # Early Run
        
        self.target_lat = 13.0827
        self.target_lon = 80.2707
        
        # Determine the data dir
        base_dir = Path(__file__).parent.parent.parent.parent / "data"
        self.raw_dir = base_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    async def check_credentials(self) -> bool:
        """Verify if credentials are provided in the environment."""
        if not self.username or not self.password:
            logger.warning("NASA Earthdata credentials missing. Ensure EARTHDATA_USERNAME and EARTHDATA_PASSWORD are set.")
            return False
        return True

    def find_nearest_indices(self, lats, lons, target_lat, target_lon):
        lat_idx = (np.abs(lats - target_lat)).argmin()
        lon_idx = (np.abs(lons - target_lon)).argmin()
        return lat_idx, lon_idx

    async def fetch_latest_precipitation(self):
        """
        Fetch latest NASA GPM IMERG Early Run data using direct HTTP requests.
        Follows secure redirect handling and parses the HDF5 to retrieve precipitationCal.
        """
        has_creds = await self.check_credentials()
        if not has_creds:
            return {"status": "UNAVAILABLE", "source": "NASA GPM IMERG Early Run", "error": "Credentials missing."}
            
        def fetch_data_sync():
            try:
                # 1. Search CMR
                cmr_url = f"https://cmr.earthdata.nasa.gov/search/granules.json?short_name={self.short_name}&page_size=1&sort_key=-start_date"
                r = requests.get(cmr_url, timeout=10)
                if r.status_code != 200:
                    return {"status": "UNAVAILABLE", "source": "NASA GPM IMERG Early Run", "error": f"CMR search failed: {r.status_code}"}
                
                data = r.json()
                entries = data.get('feed', {}).get('entry', [])
                if not entries:
                    return {"status": "UNAVAILABLE", "source": "NASA GPM IMERG Early Run", "error": "No granules found"}
                    
                entry = entries[0]
                data_timestamp = entry.get('time_start', 'Unknown Time')
                links = entry.get('links', [])
                download_link = next((link['href'] for link in links if link.get('href', '').endswith('.HDF5')), None)
                
                if not download_link:
                    return {"status": "UNAVAILABLE", "source": "NASA GPM IMERG Early Run", "error": "No HDF5 link found"}
                
                # 2. Download safely handling redirects
                token = os.getenv("EARTHDATA_TOKEN", "")
                if not token:
                    return {"status": "UNAVAILABLE", "source": "NASA GPM IMERG Early Run", "error": "EARTHDATA_TOKEN missing"}
                    
                import urllib.parse
                headers = {"Authorization": f"Bearer {token}"}
                session = requests.Session()
                
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
                            "nasa.gov" not in redirect_parsed.hostname and \
                            "cloudfront.net" not in redirect_parsed.hostname:
                                del headers['Authorization']
                        return
                        
                my_session = EarthdataSession()
                resp = my_session.get(download_link, headers=headers, allow_redirects=True, timeout=30)
                        
                if resp.status_code != 200:
                    return {"status": "UNAVAILABLE", "source": "NASA GPM IMERG Early Run", "error": f"Download failed: {resp.status_code}"}
                
                content_type = resp.headers.get("Content-Type", "")
                if "html" in content_type:
                    return {"status": "UNAVAILABLE", "source": "NASA GPM IMERG Early Run", "error": f"Received HTML instead of data. Content-type: {content_type}"}
                    
                # 3. Save temporarily and Parse HDF5
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".HDF5") as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                    
                val = 0.0
                try:
                    with h5py.File(tmp_path, 'r') as f:
                        grid = f['Grid']
                        lats = grid['lat'][:]
                        lons = grid['lon'][:]
                        # IMERG V07 uses 'precipitation', V06 uses 'precipitationCal'
                        precip_ds = grid.get('precipitation')
                        if precip_ds is None:
                            precip_ds = grid.get('precipitationCal')
                        
                        precip = precip_ds[0, :, :]
                        
                        lat_idx, lon_idx = self.find_nearest_indices(lats, lons, self.target_lat, self.target_lon)
                        val = precip[lon_idx, lat_idx]
                        
                        if val < 0 or np.isnan(val):
                            val = 0.0
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                        
                return {
                    "status": "LIVE",
                    "source": "NASA GPM IMERG Early Run",
                    "dataset": self.short_name,
                    "rainfall_rate": float(val),
                    "unit": "mm/hr",
                    "latitude": self.target_lat,
                    "longitude": self.target_lon,
                    "data_timestamp": data_timestamp,
                    "retrieved_at": datetime.datetime.utcnow().isoformat() + "Z"
                }

            except Exception as e:
                logger.error(f"NASA data error: {e}")
                return {"status": "UNAVAILABLE", "error": str(e)}

        return await asyncio.to_thread(fetch_data_sync)
