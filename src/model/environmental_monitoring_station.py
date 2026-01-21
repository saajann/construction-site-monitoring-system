# Multiple environmental monitoring stations equipped with:
# - Fine dust sensor
# - Noise level sensor
# - Dangerous gas sensor
# - GPS for positioning

import json
import random
from model.gps import GPS

from dotenv import load_dotenv
import os
load_dotenv()

# FIXED VARIABLES
#DUST_LIMIT = int(os.getenv("DUST_LIMIT"))
#NOISE_LIMIT = int(os.getenv("NOISE_LIMIT"))
#GAS_LIMIT = int(os.getenv("GAS_LIMIT"))
MONITORING_STATION_RANGE = int(os.getenv("MONITORING_STATION_RANGE"))


class EnvironmentalMonitoringStation:

    def __init__(self, id: str, position: GPS):
        self.id = id
        self.position = position # GPS
        self.range = MONITORING_STATION_RANGE # meters
        self.dust = random.uniform(20, 40)
        self.noise = random.uniform(40, 60)
        self.gas = random.uniform(0, 0.5)

    def update_dust_level(self):
        # Fluctuate: +/- random value, keep roughly within range [0, 100]
        change = random.uniform(-5, 5)
        # Allow it to go higher to test alarm occasionally
        self.dust = max(0, min(120, self.dust + change))

    def update_noise_level(self):
        change = random.uniform(-5, 5)
        self.noise = max(0, min(120, self.noise + change))

    def update_gas_level(self):
        change = random.uniform(-0.1, 0.1)
        self.gas = max(0, min(10, self.gas + change))

    def change_position(self):
        # Stations move rarely and slowly if at all (e.g. mounted on machinery)
        step_size = 0.00001 # approx 1 meter
        d_lat = random.uniform(-step_size, step_size)
        d_lon = random.uniform(-step_size, step_size)
        
        self.position.update_latitude(self.position.latitude + d_lat)
        self.position.update_longitude(self.position.longitude + d_lon)
    
    def info(self):
        # return json of info
        data = {
            "id": self.id,
            "latitude": self.position.latitude,
            "longitude": self.position.longitude,
            "altitude": self.position.altitude,
            "range": self.range,
            "dust": self.dust,
            "noise": self.noise,
            "gas": self.gas
        }

        return json.dumps(data)

    def device_info(self):
        """Metadata for retained info topic (aligned with template)"""
        return json.dumps({
            "id": self.id,
            "user_id": "admin-unimore-333695",
            "software_version": "2.0.0",
            "type": "station",
            "capabilities": ["gps", "dust", "noise", "gas"]
        })

    def to_senml(self):
        """Convert telemetry to SenML+JSON format with hierarchical names"""
        import time
        timestamp = time.time()
        return json.dumps([
            {"n": "station.gps.lat", "u": "lat", "v": self.position.latitude, "t": timestamp},
            {"n": "station.gps.lon", "u": "lon", "v": self.position.longitude, "t": timestamp},
            {"n": "station.sensor.dust", "u": "pm", "v": self.dust, "t": timestamp},
            {"n": "station.sensor.noise", "u": "db", "v": self.noise, "t": timestamp},
            {"n": "station.sensor.gas", "u": "ppm", "v": self.gas, "t": timestamp}
        ])