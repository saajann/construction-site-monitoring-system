# src/process/publisher/helmet.py
import paho.mqtt.client as mqtt
import time
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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
    info_topic = f"{MQTT_BASIC_TOPIC}/helmet/{helmet_id}/info"
    mqtt_client.publish(info_topic, helmet.info(), 0, True)
    print(f"Helmet {helmet_id} info published")
    
    # Loop telemetria
    telemetry_topic = f"{MQTT_BASIC_TOPIC}/helmet/{helmet_id}"
    
    for message_id in range(MESSAGE_LIMIT):

        if helmet.led == 0:
            helmet.move()
            helmet.descrease_battery_level(15)
            helmet.check_battery_level()
        else:
            helmet.recharge_battery(5)    
        
        payload = helmet.info()
        mqtt_client.publish(telemetry_topic, payload, 0, False)
        print(f"Topic {telemetry_topic} - Message {message_id}: {payload}")
        time.sleep(TIME_BETWEEN_MESSAGE)
    
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print(f"Helmet {helmet_id} disconnected")

if __name__ == "__main__":
    # Test standalone
    start_helmet_device("helmet_001", 45.0, 9.0)