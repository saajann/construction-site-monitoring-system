# Smart helmet associated with a single worker, equipped with:
# - GPS for worker position tracking
# - Battery level sensor
# - Multicolor LED

import json
from model.gps import GPS

class WorkerSmartHelmet:

    def __init__(self, id: str, position: GPS):
        self.id = id
        self.position = position
        self.battery = 100
        self.led = 0 # if 0 then LED is green, if 1 then LED is yellow and needs to be recharged
        # forse è meglio cambiare la logica del led, conviene fare:
            # 0, green, tutto ok
            # 1, giallo, batteria sotto il 10% 
            # 2, rosso, è entrato in una zona pericolosa
    
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
            "battery": self.battery,
            "led": self.led
        }

        return json.dumps(data)