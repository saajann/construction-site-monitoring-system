# verrà usato per salvare la posizione di varie cose: casco, monitoring station, coordinate dei settori
# per ora mi interessa salvare solo longitudine, latitudine e altitudine (quest'ultima sempre a 0 per semplificare)

import json

class GPS:

    def __init__(self, latitude: float, longitude: float, altitude: float = 0.0):
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


class AreaVertices:

    def __init__(self, vertices: list[GPS]):
        if len(vertices) < 3:
             # Basic check for a polygon
             pass 
             # raise ValueError("Area must have at least 3 vertices") 
             # Relaxed for now as point/line might be passed temporarily? No, likely >2 for a real sector.
        
        self.vertices = vertices

        self.top_left = None
        self.top_right = None
        self.bottom_left = None
        self.bottom_right = None

        if len(vertices) == 4:
            self.orient_vertices()

    def orient_vertices(self):
        if len(self.vertices) != 4:
            return

        sorted_by_lat = sorted(self.vertices, key=lambda p: p.latitude, reverse=True)

        top = sorted_by_lat[:2]
        bottom = sorted_by_lat[2:]

        self.top_left, self.top_right = sorted(top, key=lambda p: p.longitude)
        self.bottom_left, self.bottom_right = sorted(bottom, key=lambda p: p.longitude)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)