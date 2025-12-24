# verrà usato per salvare la posizione di varie cose: casco, monitoring station, coordinate dei settori
# per ora mi interessa salvare solo longitudine, latitudine e altitudine (quest'ultima sempre a 0 per semplificare)

import json

class GPS:

    def __init__(self, latitude: float, longitude: float, altitude: float):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude

    def update_latitude(self, latitude: float):
        self.latitude = latitude
    
    def update_longitude(self, longitude: float):
        self.longitude = longitude

    def update_altitude(self, altitude: float):
        self.altitude = altitude

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)