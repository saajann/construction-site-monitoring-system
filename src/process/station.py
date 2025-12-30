# src/process/station.py
import paho.mqtt.client as mqtt
import time
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

import csv
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from model.environmental_monitoring_station import EnvironmentalMonitoringStation
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

TOPIC='station'

CSV_PATH = ROOT / "data" / "stations.csv"


def on_connect(client, userdata, flags, rc):
    print(f"Helmet {userdata['station_id']} connected with result code {rc}")

def start_station_device(station_id, latitude, longitude):
    """
    
    """
    # setup client MQTT
    mqtt_client = mqtt.Client(station_id)
    mqtt_client.user_data_set({'station_id': station_id})
    mqtt_client.on_connect = on_connect
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    print(f"Connecting station {station_id} to {BROKER_ADDRESS}:{BROKER_PORT}")
    mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT)
    mqtt_client.loop_start()
    
    # create station
    position = GPS(latitude, longitude)
    station = EnvironmentalMonitoringStation(station_id, position)
    
    # publish initial info
    info_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC}/{station_id}/info"
    mqtt_client.publish(info_topic, station.info(), 0, True)
    print(f"Station {station_id} info published")
    
    # Loop telemetria
    telemetry_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC}/{station_id}"
    
    for message_id in range(MESSAGE_LIMIT):
        
        station.update_dust_level()
        station.update_noise_level()
        station.update_gas_level()
        
        payload = station.info()
        mqtt_client.publish(telemetry_topic, payload, 0, False)
        print(f"Topic {telemetry_topic} - Message {message_id}: {payload}")
        time.sleep(TIME_BETWEEN_MESSAGE)
    
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print(f"Station {station_id} disconnected")

def load_stations(csv_path):
    stations = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stations.append(
                (row["id"], float(row["latitude"]), float(row["longitude"]))
            )
    return stations

def main():
    print("=== Starting Stations ===\n")

    stations = load_stations(CSV_PATH)

    threads = []

    for station in stations:
        t = threading.Thread(
            target=start_station_device,
            args=station,
            daemon=True
        )
        t.start()
        threads.append(t)
        print(f"Station {station[0]} started")

    print("\nAll stations running\n")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down system")

if __name__ == "__main__":
    main()