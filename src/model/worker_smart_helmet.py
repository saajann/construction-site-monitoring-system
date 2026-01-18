# Smart helmet associated with a single worker, equipped with:
# - GPS for worker position tracking
# - Battery level sensor
# - Multicolor LED

import json
import random
import time
from model.gps import GPS

class WorkerSmartHelmet:

    def __init__(self, id: str, position: GPS, boundaries: dict = None):
        self.id = id
        self.position = position
        self.battery = 100
        self.led = 0  # 0: Green (Work/Moving), 1: Yellow (Charging/Stationary), 2: Red (Danger)
        self.boundaries = boundaries # expectation: {"min_lat": ..., "max_lat": ..., "min_lon": ..., "max_lon": ...}
        # forse è meglio cambiare la logica del led, conviene fare:
        # 0, green, tutto ok
        # 1, giallo, batteria sotto il 10% 
        # 2, rosso, è entrato in una zona pericolosa
    
    def check_if_dangerous(self):
        ...

    def descrease_battery_level(self, qty: int):
        self.battery -= qty
        if self.battery < 0:
            self.battery = 0

    def set_led(self, state: int): # i dont need it here, it will be implemented in the data collector and manager 
        self.led = state
    
    def recharge_battery(self, qty: int):
        self.battery += qty
        if self.battery >= 100:
            self.battery = 100
            #self.led = 0

    def move(self):
        # Movement is allowed only if the LED is green (Work mode)
        if self.led != 0:
            return

        # Realistic random walk: small steps (~1-2 meters)
        # 1 deg lat ~ 111km -> 1m ~ 0.000009 deg
        step_size = 0.00002 # approx 2 meters
        
        # Random direction
        d_lat = random.uniform(-step_size, step_size)
        d_lon = random.uniform(-step_size, step_size)
        
        new_lat = self.position.latitude + d_lat
        new_lon = self.position.longitude + d_lon

        # Boundary control: keep the helmet inside the site area (polygon)
        if self.boundaries and 'polygon' in self.boundaries:
            # Check if new position is inside polygon
            if not self._point_in_polygon(new_lat, new_lon, self.boundaries['polygon']):
                # If outside, don't move
                return

        self.position.update_latitude(new_lat)
        self.position.update_longitude(new_lon)
    
    def _point_in_polygon(self, lat, lon, polygon):
        """
        Ray casting algorithm to check if point is inside polygon
        polygon: list of (lat, lon) tuples
        """
        n = len(polygon)
        inside = False
        
        p1_lat, p1_lon = polygon[0]
        for i in range(1, n + 1):
            p2_lat, p2_lon = polygon[i % n]
            if lon > min(p1_lon, p2_lon):
                if lon <= max(p1_lon, p2_lon):
                    if lat <= max(p1_lat, p2_lat):
                        if p1_lon != p2_lon:
                            x_intersection = (lon - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                        if p1_lat == p2_lat or lat <= x_intersection:
                            inside = not inside
            p1_lat, p1_lon = p2_lat, p2_lon
        
        return inside
    
    def senml_telemetry(self):
        """Returns telemetry in SenML+JSON format"""
        base_name = f"helmet:{self.id}"
        timestamp = time.time()
        
        data = [
            {"bn": base_name, "t": timestamp, "n": "battery", "u": "%", "v": self.battery},
            {"n": "latitude", "u": "lat", "v": self.position.latitude},
            {"n": "longitude", "u": "lon", "v": self.position.longitude},
            {"n": "led", "v": self.led}
        ]
        return json.dumps(data)

    def static_info(self):
        """Returns static device information in SenML+JSON format"""
        base_name = f"helmet:{self.id}"
        data = [
            {"bn": base_name, "n": "type", "vs": "smart_helmet"},
            {"n": "manufacturer", "vs": "UniMoRe IoT Lab"},
            {"n": "version", "vs": "1.0.0"}
        ]
        return json.dumps(data)