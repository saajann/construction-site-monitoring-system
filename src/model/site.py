# il cantiere deve essere diviso in più zone (una specie di griglia)
# suppongo di dare in input le coordinate dei quattro vertici (per ora supponiamo che l'area abbia 4 lati per semplificare)
# un algoritmo calcola da solo la divisione dello spazio (taglia in verticale e in orizzontale)
# ad ogni settore (viene assegnato un ID e vengono salvate le coordinate dei suoi 4 vertici)

import json

class Site:

    def __init__(self, site: list[float]):
        self.site = site # list with 4 floats (vertices of the site)
        self.grid = [] # list of vertices, one list for every grid sector

    def create_grid(self):
        ...

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)