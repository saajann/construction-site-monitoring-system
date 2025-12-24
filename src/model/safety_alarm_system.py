# qua potrei far aprire una finestra che appunto mostra gli ID delle zone pericolose e se per caso
# un worker entra dentro ad una di esse, inizia realmente a suonare una sirena

# Remotely controllable alarm system equipped with:
# - Acoustic siren (ON/OFF)
# - Display showing the IDs of dangerous zones

import json

class SafetyAlarmSystem:

    def __init__(self):
        self.siren = False # True if siren is ON, False if siren is OFF
        self.display = [] # add IDs of the dangerous sectors 

    def turn_siren_on(self):
        self.siren = True
    
    def turn_siren_off(self):
        self.siren = False

    def add_dangerous_zone(self, id: int):
        self.display.append(id)

    def remove_dangerous_zone(self, id: int):
        self.display.remove(id)    

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)