# Smart helmet associated with a single worker, equipped with:
# - GPS for worker position tracking
# - Battery level sensor
# - Multicolor LED

import json

class WorkerSmartHelmet:

    def __init__(self, position):
        self.position = position
        self.battery = 100
        self.led = 0 # if 0 then LED is green, if 1 then LED is yellow and needs to be recharged
    
    def check_if_dangerous(self):
        ...

    def check_battery_level(self):
        ...
    
    def recharge_battery(self):
        ...

    def move(self):
        ...

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)