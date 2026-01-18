# Multiple environmental monitoring stations equipped with:
# - Fine dust sensor
# - Noise level sensor
# - Dangerous gas sensor
# - GPS for positioning

import json
import random
import time
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
    
    def senml_telemetry(self):
        """Returns telemetry in SenML+JSON format"""
        base_name = f"station:{self.id}"
        timestamp = time.time()
        
        data = [
            {"bn": base_name, "t": timestamp, "n": "dust", "u": "ug/m3", "v": self.dust},
            {"n": "noise", "u": "dB", "v": self.noise},
            {"n": "gas", "u": "ppm", "v": self.gas},
            {"n": "latitude", "u": "lat", "v": self.position.latitude},
            {"n": "longitude", "u": "lon", "v": self.position.longitude}
        ]
        return json.dumps(data)

    def static_info(self):
        """Returns static device information in SenML+JSON format"""
        base_name = f"station:{self.id}"
        data = [
            {"bn": base_name, "n": "type", "vs": "monitoring_station"},
            {"n": "manufacturer", "vs": "UniMoRe IoT Lab"},
            {"n": "version", "vs": "1.0.0"},
            {"n": "range", "u": "m", "v": self.range}
        ]
        return json.dumps(data)