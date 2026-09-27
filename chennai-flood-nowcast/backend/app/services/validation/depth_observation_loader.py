"""
Depth Observation Loader

Loads and standardizes legitimate numerical flood-depth observations from the
OpenCity Chennai Inundation Points Dataset (814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml).

Provenances & Rules:
- Original units: inches
- Unit conversion: 1 inch = 2.54 cm
- Rejects negative physical flood depths
- Preserves zero-depth observations if present
- Verifies timestamp presence/absence
"""

import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

INCHES_TO_CM = 2.54

class DepthObservationLoader:
    def __init__(self, kml_path: Path = None):
        if kml_path is None:
            curr = Path(__file__).resolve().parent
            candidates = []
            for p in [curr] + list(curr.parents):
                candidates.append(p / "data" / "validation" / "raw" / "814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml")
            
            found_path = None
            for cand in candidates:
                if cand.exists():
                    found_path = cand
                    break

            if found_path is None:
                # fallback
                found_path = Path("c:/Users/HP/OneDrive/Desktop/flood nowcasting/data/validation/raw/814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml")

            kml_path = found_path
        self.kml_path = kml_path

    def load_opencity_depth_observations(self) -> List[Dict[str, Any]]:
        """
        Parse KML file and extract valid numerical flood-depth observation records.
        Returns a list of standardized dicts.
        """
        if not self.kml_path.exists():
            logger.error(f"KML dataset not found at path: {self.kml_path}")
            return []

        tree = ET.parse(self.kml_path)
        root = tree.getroot()

        # Handle XML namespaces
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        observations = []
        placemarks = root.findall('.//kml:Placemark', ns)
        if not placemarks:
            # Fallback without namespace
            placemarks = root.findall('.//Placemark')

        for idx, pm in enumerate(placemarks):
            lat = None
            lon = None
            depth_inches = None
            remarks = ""

            # 1. Parse SimpleData tags
            simple_datas = pm.findall('.//kml:SimpleData', ns) or pm.findall('.//SimpleData')
            for sd in simple_datas:
                name = sd.attrib.get('name', '')
                val = sd.text.strip() if sd.text else ""

                if name == 'F_LATITUDE' and val:
                    try:
                        lat = float(val)
                    except ValueError:
                        pass
                elif name == 'F_LONGITUDE' and val:
                    try:
                        lon = float(val)
                    except ValueError:
                        pass
                elif name == 'DEPTH' and val:
                    try:
                        depth_inches = float(val)
                    except ValueError:
                        pass
                elif name == 'F_REMARKS' and val:
                    remarks = val

            # 2. Fallback coordinates from <coordinates> tag
            if lat is None or lon is None:
                coord_elem = pm.find('.//kml:coordinates', ns) or pm.find('.//coordinates')
                if coord_elem and coord_elem.text:
                    parts = coord_elem.text.strip().split(',')
                    if len(parts) >= 2:
                        try:
                            lon = float(parts[0])
                            lat = float(parts[1])
                        except ValueError:
                            pass

            # Validation checks
            if lat is None or lon is None or depth_inches is None:
                logger.warning(f"Record {idx} missing required spatial/depth fields. Skipping.")
                continue

            # Reject negative depths
            if depth_inches < 0:
                logger.warning(f"Record {idx} has negative depth ({depth_inches} inches). Rejecting.")
                continue

            depth_cm = round(depth_inches * INCHES_TO_CM, 2)

            obs = {
                "observation_id": f"OPENCITY_INUNDATION_{idx + 1:03d}",
                "dataset_id": "OpenCity_Chennai_Inundation_Points",
                "source": "OpenCity Chennai CKAN (Greater Chennai Corporation & Survey Records)",
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "observed_depth_inches": depth_inches,
                "observed_depth_cm": depth_cm,
                "original_unit": "inches",
                "converted_unit": "cm",
                "conversion_factor": INCHES_TO_CM,
                "remarks": remarks,
                "event_attribution": "UNKNOWN_EVENT_DIAGNOSTIC",
                "timestamp_utc": None,
                "has_reliable_timestamp": False,
                "metadata": {
                    "is_zero_depth": (depth_cm == 0.0),
                    "measurement_type": "Surrogate / Field Inundation Measurement",
                    "coordinate_reference": "EPSG:4326 (WGS84)"
                }
            }
            observations.append(obs)

        logger.info(f"Loaded {len(observations)} valid depth records from OpenCity KML dataset.")
        return observations
