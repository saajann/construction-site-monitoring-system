# il cantiere deve essere diviso in più zone (una specie di griglia)
# suppongo di dare in input le coordinate dei quattro vertici (per ora supponiamo che l'area abbia 4 lati per semplificare)
# un algoritmo calcola da solo la divisione dello spazio (taglia in verticale e in orizzontale)
# ad ogni settore (viene assegnato un ID e vengono salvate le coordinate dei suoi 4 vertici)

import math
import json
from model.gps import AreaVertices, GPS

class Site:

    def __init__(self, area_vertices: AreaVertices):
        self.area_vertices = area_vertices # list with 4 floats (vertices of the site)
        self.grid = [] # list of vertices, one list for every grid sector

    def create_grid(self, sector_size_meters=10.0):
        """
        Divides the site area into a grid of sectors.
        Assumes area_vertices describes a roughly rectangular area.
        """
        # Get bounds
        min_lat = min(p.latitude for p in self.area_vertices.vertices)
        max_lat = max(p.latitude for p in self.area_vertices.vertices)
        min_lon = min(p.longitude for p in self.area_vertices.vertices)
        max_lon = max(p.longitude for p in self.area_vertices.vertices)

        # Earth radius approximation
        R = 6378137

        # Calculate dimensions in meters
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon
        
        height_meters = lat_diff * (3.14159 / 180) * R
        width_meters = lon_diff * (3.14159 / 180) * R * 0.7  # Cos approx (avg lat ~45)

        rows = int(height_meters / sector_size_meters) + 1
        cols = int(width_meters / sector_size_meters) + 1
        
        # Calculate steps
        lat_step = lat_diff / rows
        lon_step = lon_diff / cols

        self.grid = []

        for r in range(rows):
            for c in range(cols):
                # Calculate sector vertices
                p1 = GPS(min_lat + r * lat_step, min_lon + c * lon_step)
                p2 = GPS(min_lat + r * lat_step, min_lon + (c+1) * lon_step)
                p3 = GPS(min_lat + (r+1) * lat_step, min_lon + (c+1) * lon_step)
                p4 = GPS(min_lat + (r+1) * lat_step, min_lon + c * lon_step)
                
                sector_vertices = AreaVertices([p1, p2, p3, p4])
                
                # Create sector ID
                sector_id = f"Zone-{r}-{c}"
                
                sector = Sector(sector_id, sector_vertices)
                self.grid.append(sector)

    def get_sector_by_coords(self, lat, lon):
        """Finds which sector contains the given coordinates"""
        # Simple bounding box check (optimization possible with grid math)
        for sector in self.grid:
            # Check if point is inside sector
            # Simplified: check against bounds of sector
            v = sector.area_vertices.vertices
             # Assuming rectangular and oriented
            s_min_lat = min(p.latitude for p in v)
            s_max_lat = max(p.latitude for p in v)
            s_min_lon = min(p.longitude for p in v)
            s_max_lon = max(p.longitude for p in v)

            if s_min_lat <= lat <= s_max_lat and s_min_lon <= lon <= s_max_lon:
                return sector
        return None

    def get_sectors_in_radius(self, center_lat, center_lon, radius_meters):
        """
        Returns a list of Sectors that fall within the radius.
        """
        affected_sectors = []
        
        # Simple centroid distance check
        for sector in self.grid:
             # Calculate centroid
            v = sector.area_vertices.vertices
            avg_lat = sum(p.latitude for p in v) / 4
            avg_lon = sum(p.longitude for p in v) / 4
            
            # Distance calc (Haversine or simple flat earth for small area)
            R = 6378137
            d_lat = (avg_lat - center_lat) * (math.pi / 180) * R
            d_lon = (avg_lon - center_lon) * (math.pi / 180) * R * math.cos(center_lat * math.pi / 180)
            
            dist = math.sqrt(d_lat**2 + d_lon**2)
            
            # Use radius + half sector diagonal (approx 7m for 10m sector) to be safe/inclusive
            # or just simple radius check. Let's be slightly inclusive.
            if dist <= radius_meters + 7.0: 
                affected_sectors.append(sector)
                
        return affected_sectors

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
    
class Sector:

    def __init__(self, id: str, area_vertices: AreaVertices):
        self.id = id
        self.area_vertices = area_vertices
        self.status = 0 # 0 -> SAFE, 1 -> DANGEROUS

    def set_safe(self):
        self.status = 0

    def set_dangerous(self):
        self.status = 1

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)