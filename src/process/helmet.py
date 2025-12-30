# src/process/helmet.py

# pub helmet info -> DONE
# sub data collector / manager -> TO DO

import paho.mqtt.client as mqtt
import time
import random
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

import csv
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from model.worker_smart_helmet import WorkerSmartHelmet
from model.gps import GPS

load_dotenv()

# FIXED VARIABLES
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS")
BROKER_PORT = int(os.getenv("BROKER_PORT"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC")
MESSAGE_LIMIT = int(os.getenv("MESSAGE_LIMIT"))
TIME_BETWEEN_MESSAGE = int(os.getenv("TIME_BETWEEN_MESSAGE"))

TOPIC='helmet'

CSV_PATH = ROOT / "data" / "helmets.csv"


def on_connect(client, userdata, flags, rc):
    print(f"Helmet {userdata['helmet_id']} connected with result code {rc}")

def start_helmet_device(helmet_id, latitude, longitude):
    """
    
    """
    # setup client MQTT
    mqtt_client = mqtt.Client(helmet_id)
    mqtt_client.user_data_set({'helmet_id': helmet_id})
    mqtt_client.on_connect = on_connect
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    print(f"Connecting helmet {helmet_id} to {BROKER_ADDRESS}:{BROKER_PORT}")
    mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT)
    mqtt_client.loop_start()
    
    # create helmet
    position = GPS(latitude, longitude)
    helmet = WorkerSmartHelmet(helmet_id, position)
    
    # publish initial info
    info_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC}/{helmet_id}/info"
    mqtt_client.publish(info_topic, helmet.info(), 0, True)
    print(f"Helmet {helmet_id} info published")
    
    # Loop telemetria
    telemetry_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC}/{helmet_id}"
    
    for message_id in range(MESSAGE_LIMIT):
        
        # non va bene, lo stato del led deve cambiare con un messaggio di attuazione
        # non sono sicuro, capire se posso farlo senza messaggio di attuazione o no
        # logica di business (check battery level) in data collector, toggle solo a seguito di comando del data manager 
        if helmet.led == 0:
            helmet.move()
            helmet.descrease_battery_level(random.randint(10,15))
            helmet.check_battery_level()
        else:
            helmet.recharge_battery(random.randint(1,10))    
        
        payload = helmet.info()
        mqtt_client.publish(telemetry_topic, payload, 0, False)
        print(f"Topic {telemetry_topic} - Message {message_id}: {payload}")
        time.sleep(TIME_BETWEEN_MESSAGE)
    
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print(f"Helmet {helmet_id} disconnected")

def load_helmets(csv_path):
    helmets = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            helmets.append(
                (row["id"], float(row["latitude"]), float(row["longitude"]))
            )
    return helmets

def main():
    print("=== Starting Helmets ===\n")

    helmets = load_helmets(CSV_PATH)

    threads = []

    for helmet in helmets:
        t = threading.Thread(
            target=start_helmet_device,
            args=helmet,
            daemon=True
        )
        t.start()
        threads.append(t)
        print(f"Helmet {helmet[0]} started")

    print("\nAll helmets running\n")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down system")

if __name__ == "__main__":
    main()