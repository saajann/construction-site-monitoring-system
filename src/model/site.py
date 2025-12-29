# il cantiere deve essere diviso in più zone (una specie di griglia)
# suppongo di dare in input le coordinate dei quattro vertici (per ora supponiamo che l'area abbia 4 lati per semplificare)
# un algoritmo calcola da solo la divisione dello spazio (taglia in verticale e in orizzontale)
# ad ogni settore (viene assegnato un ID e vengono salvate le coordinate dei suoi 4 vertici)

import json
from model.gps import AreaVertices

class Site:

    def __init__(self, area_vertices: AreaVertices):
        self.area_vertices = area_vertices # list with 4 floats (vertices of the site)
        self.grid = [] # list of vertices, one list for every grid sector

    def create_grid(self):
        # create all sectors and add them to self.grid
        ...

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