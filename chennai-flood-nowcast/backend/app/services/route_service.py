class RouteService:
    def __init__(self):
        self.model_version = "baseline-v1"

    def get_roads_risk(self):
        return {
            "model_version": self.model_version,
            "risk_type": "Modelled road risk",
            "roads": [
                {"id": 1, "name": "Mount Road", "risk": "MODERATE", "depth_cm": 15, "coords": [[13.0658, 80.2642], [13.0450, 80.2450]]},
                {"id": 2, "name": "OMR IT Expressway", "risk": "LOW", "depth_cm": 5, "coords": [[12.9800, 80.2450], [12.9000, 80.2250]]},
                {"id": 3, "name": "Velachery Main Road", "risk": "HIGH", "depth_cm": 45, "coords": [[12.9850, 80.2200], [12.9700, 80.2150]]},
                {"id": 4, "name": "GST Road", "risk": "NORMAL", "depth_cm": 0, "coords": [[13.0100, 80.2000], [12.9500, 80.1400]]},
                {"id": 5, "name": "ECR", "risk": "CRITICAL", "depth_cm": 70, "coords": [[12.9850, 80.2600], [12.9200, 80.2400]]},
            ]
        }

    def get_critical_locations(self):
        return {
            "model_version": self.model_version,
            "risk_type": "Modelled risk based on baseline model",
            "locations": [
                {"id": 1, "name": "Apollo Hospital", "type": "Hospital", "risk": "MODERATE", "status": "MODELLED", "depth_cm": 10, "lat": 13.0604, "lng": 80.2496},
                {"id": 2, "name": "Chennai Central", "type": "Transport Hub", "risk": "HIGH", "status": "MODELLED", "depth_cm": 35, "lat": 13.0827, "lng": 80.2757},
                {"id": 3, "name": "Velachery Fire Station", "type": "Fire Station", "risk": "CRITICAL", "status": "MODELLED", "depth_cm": 60, "lat": 12.9774, "lng": 80.2223},
            ]
        }
        
    def get_safer_route(self):
        return {
            "model_version": self.model_version,
            "route_type": "Model-based safer route",
            "message": "Routing via safe corridors (avoiding modelled high-risk sectors)",
            "waypoints": [
                [13.0827, 80.2757],
                [13.0604, 80.2496],
                [13.0400, 80.2200]
            ]
        }
