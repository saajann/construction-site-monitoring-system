# Multiple environmental monitoring stations equipped with:
# - Fine dust sensor
# - Noise level sensor
# - Dangerous gas sensor
# - GPS for positioning

import json
from model.gps import GPS

class EnvironmentalMonitoringStation:

    def __init__(self, position: GPS):
        self.position = position # GPS
        self.range = 10 # meters
        self.dust = 0
        self.noise = 0
        self.gas = 0

    def check_dust_level(self):
        ...

    def check_noise_level(self):
        ...

    def check_gas_level(self):
        ...

    def change_position(self):
        ...

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)