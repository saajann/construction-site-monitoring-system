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
        self.dust = 0
        self.noise = 0
        self.gas = 0

    def update_dust_level(self):
        self.dust += 1

    def update_noise_level(self):
        self.noise += 1

    def update_gas_level(self):
        self.gas += 1

    def change_position(self):
        # temporary logic
        self.position.update_latitude(self.position.latitude + 1)
        self.position.update_longitude(self.position.longitude + 1)
    
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