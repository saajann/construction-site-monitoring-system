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
        Divides the site area into a grid of sectors, clipping them to the site boundaries using Shapely.
        """
        from shapely.geometry import Polygon, box
        
        # 1. Create Site Polygon
        site_coords = [(p.latitude, p.longitude) for p in self.area_vertices.vertices]
        if len(site_coords) < 3:
            return # Invalid polygon
        
        site_poly = Polygon(site_coords)
        if not site_poly.is_valid:
            site_poly = site_poly.buffer(0) # Attempt to fix self-intersections

        # Get bounds
        min_lat, min_lon, max_lat, max_lon = site_poly.bounds

        # Earth radius approximation for meter conversion
        R = 6378137
        
        # Calculate approximate dimensions in degrees
        lat_diff_per_meter = (1 / ((2 * math.pi * R) / 360))
        # Longitudinal degrees vary with latitude, use center lat for approx
        center_lat = (min_lat + max_lat) / 2
        lon_diff_per_meter = (1 / ((2 * math.pi * R * math.cos(math.radians(center_lat))) / 360))
        
        step_lat = sector_size_meters * lat_diff_per_meter
        step_lon = sector_size_meters * lon_diff_per_meter

        rows = int((max_lat - min_lat) / step_lat) + 1
        cols = int((max_lon - min_lon) / step_lon) + 1

        self.grid = []

        for r in range(rows):
            for c in range(cols):
                # Create grid cell polygon
                cell_min_lat = min_lat + r * step_lat
                cell_max_lat = min_lat + (r+1) * step_lat
                cell_min_lon = min_lon + c * step_lon
                cell_max_lon = min_lon + (c+1) * step_lon
                
                # Shapely expects (x, y) -> (lat, lon) or (lon, lat). 
                # Let's use (lat, lon) consistently for our geometric operations 
                # BEWARE: Shapely usually treats cartesian, but for intersection logic it works if units are consistent.
                cell_poly = box(cell_min_lat, cell_min_lon, cell_max_lat, cell_max_lon)
                
                # Intersect
                intersection = site_poly.intersection(cell_poly)
                
                if not intersection.is_empty and intersection.area > 1e-10: # Filter tiny slivers
                    # If MultiPolygon (rare but possible with weird shapes), take biggest or all
                    polys = [intersection] if intersection.geom_type == 'Polygon' else intersection.geoms
                    
                    for i, poly in enumerate(polys):
                        # Extract coords
                        # poly.exterior.coords returns list of (lat, lon)
                        coords = list(poly.exterior.coords)
                        # Create GPS points
                        gps_vertices = [GPS(lat, lon) for lat, lon in coords]
                        
                        sector_vertices = AreaVertices(gps_vertices)
                        
                        # Create ID
                        suffix = f"-{i}" if len(polys) > 1 else ""
                        sector_id = f"Zone-{r}-{c}{suffix}"
                        
                        sector = Sector(sector_id, sector_vertices)
                        self.grid.append(sector)

    def get_sector_by_coords(self, lat, lon):
        """Finds which sector contains the given coordinates"""
        # Linear search for point-in-polygon
        # Optimization: use R-tree if many sectors, but linear ok for < 1000
        from shapely.geometry import Point, Polygon
        
        point = Point(lat, lon)
        
        for sector in self.grid:
            # Reconstruct polygon (cache this if performance needed)
            coords = [(p.latitude, p.longitude) for p in sector.area_vertices.vertices]
            poly = Polygon(coords)
            if poly.contains(point):
                return sector
        return None

    def get_sectors_in_radius(self, center_lat, center_lon, radius_meters):
        """
        Returns a list of Sectors that fall within the radius.
        Uses elliptical buffer to account for lat/lon scaling differences.
        """
        from shapely.geometry import Point, Polygon
        from shapely import affinity
        
        # Correct conversion from meters to degrees
        # 1 degree latitude ≈ 111,000 meters
        # 1 degree longitude ≈ 111,000 * cos(latitude) meters
        lat_deg_per_meter = 1.0 / 111000.0
        lon_deg_per_meter = 1.0 / (111000.0 * math.cos(math.radians(center_lat)))
        
        # Create elliptical buffer by scaling
        center_point = Point(center_lat, center_lon)
        
        # Scale radius differently for lat and lon to create proper circle
        lat_radius = radius_meters * lat_deg_per_meter
        lon_radius = radius_meters * lon_deg_per_meter
        
        # Create ellipse by buffering with average then scaling
        avg_radius = (lat_radius + lon_radius) / 2
        circle = center_point.buffer(avg_radius)
        
        # Scale to create ellipse that represents true circular distance
        scale_x = lat_radius / avg_radius
        scale_y = lon_radius / avg_radius
        search_area = affinity.scale(circle, xfact=scale_x, yfact=scale_y)
        
        affected_sectors = []
        for sector in self.grid:
            coords = [(p.latitude, p.longitude) for p in sector.area_vertices.vertices]
            poly = Polygon(coords)
            if search_area.intersects(poly):
                affected_sectors.append(sector)
                
        return affected_sectors

    def save_grid_to_csv(self, filepath):
        """
        Saves the current grid to a CSV file.
        Format: id, json_coords
        json_coords example: [[lat,lon], [lat,lon], ...]
        """
        import csv
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "vertices_json"])
                for sector in self.grid:
                    coords = [[p.latitude, p.longitude] for p in sector.area_vertices.vertices]
                    writer.writerow([sector.id, json.dumps(coords)])
            print(f"✅ Grid saved to {filepath}")
        except Exception as e:
            print(f"❌ Failed to save grid to {filepath}: {e}")

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
    
class Sector:

    def __init__(self, id: str, area_vertices: AreaVertices):
        self.id = id
        self.area_vertices = area_vertices
        # Status removed, managed by Manager

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)