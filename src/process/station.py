# src/process/station.py

# pub station info -> DONE

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
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC") + MQTT_USERNAME
MESSAGE_LIMIT = int(os.getenv("MESSAGE_LIMIT"))
TIME_BETWEEN_MESSAGE = int(os.getenv("TIME_BETWEEN_MESSAGE"))
TOPIC_STATION = os.getenv("TOPIC_STATION")

CSV_PATH = ROOT / "data" / "static" / "stations.csv"


def on_connect(client, userdata, flags, rc):
    print(f"Station {userdata['station_id']} connected with result code {rc}")

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
    
    # Loop telemetry
    telemetry_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_STATION}/{station_id}/telemetry"
    
    # for message_id in range(MESSAGE_LIMIT):
    while True:
        
        station.update_dust_level()
        station.update_noise_level()
        station.update_gas_level()
        
        payload = station.info()
        mqtt_client.publish(telemetry_topic, payload, 0, False)
        
        log_msg = (
            f"[STA-{station_id}] 📤 SENT | "
            f"Dust: {station.dust:6.2f} | "
            f"Noise: {station.noise:6.2f} | "
            f"Gas: {station.gas:4.2f} | "
            f"Pos: ({station.position.latitude:.5f}, {station.position.longitude:.5f})"
        )
        print(log_msg)
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