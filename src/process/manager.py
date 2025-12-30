# src/process/data_collector_manager.py

# publisher to helmet -> TO DO
# publisher to alarm -> TO DO

# subscriber to helmet -> TO DO
# subscriber to station -> TO DO

import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from model.safety_alarm_system import SafetyAlarmSystem

load_dotenv()

# FIXED VARIABLES
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS")
BROKER_PORT = int(os.getenv("BROKER_PORT"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC") + MQTT_USERNAME

TOPIC_ALARM = os.getenv("TOPIC_ALARM")
TOPIC_HELMET = os.getenv("TOPIC_HELMET")
TOPIC_STATION = os.getenv("TOPIC_STATION")
TOPIC_MANAGER = os.getenv("TOPIC_MANAGER")






# SUB HELMET

# subscribe to topics 
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # subscribe to the TELEMETRY topic for the helmet
    helmet_telemetry_topic = "{0}/{1}/#".format(
        MQTT_BASIC_TOPIC,
        TOPIC_HELMET,
        )

    mqtt_client.subscribe(helmet_telemetry_topic)
    print("Subscribed to: " + helmet_telemetry_topic)

# method to receive asynchronous messages
def on_message(client, userdata, message):
    message_payload = str(message.payload.decode("utf-8"))
    print(f"Received IoT Message: Topic: {message.topic} Payload: {message_payload}")

# configuration variables
# manager = "alarm_001"

mqtt_client = mqtt.Client(TOPIC_MANAGER)
mqtt_client.on_message = on_message
mqtt_client.on_connect = on_connect

# Set Account Username & Password
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

print("Connecting to " + BROKER_ADDRESS + " port: " + str(BROKER_PORT))
mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT)

# start comunication
mqtt_client.loop_forever()