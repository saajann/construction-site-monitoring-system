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

# FIXED VARIABLES
BROKER_ADDRESS=os.getenv("BROKER_ADDRESS")
BROKER_PORT=int(os.getenv("BROKER_PORT"))
MQTT_USERNAME=os.getenv("MQTT_USERNAME")
MQTT_PASSWORD=os.getenv("MQTT_PASSWORD")
MQTT_BASIC_TOPIC=os.getenv("MQTT_BASIC_TOPIC")
TOPIC='helmet'

MESSAGE_LIMIT = 1000


#  needed by default
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

# function to publish device info 
def publish_info():
    target_topic = "{0}/{1}/{2}".format(
                        MQTT_BASIC_TOPIC,
                        TOPIC,
                        helmet.id
                        )
    
    # turn into json
    device_payload_string = helmet.info()

    mqtt_client.publish(target_topic, device_payload_string, 0, True)

    print(f"Vehicle Info Published: Topic: {target_topic} Payload: {device_payload_string}")

# function to publish device info 
def publish_telemetry():
    target_topic = "{0}/{1}/{2}".format(
                        MQTT_BASIC_TOPIC,
                        TOPIC,
                        helmet.id,
                        )
    
    # turn into json
    device_payload_string = helmet.info()

    mqtt_client.publish(target_topic, device_payload_string, 0, True)

    print(f"Vehicle Telemetry Published: Topic: {target_topic} Payload: {device_payload_string}")


# connect to the MQTT broker
helmet_id = '1'

mqtt_client = mqtt.Client(helmet_id)
mqtt_client.on_connect = on_connect

mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

print("Connecting to " + BROKER_ADDRESS + " port: " + str(BROKER_PORT))
mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT)


# start comunication
mqtt_client.loop_start()

position = GPS(45.0, 45.0)
helmet = WorkerSmartHelmet(helmet_id, position)

publish_info()

for message_id in range(MESSAGE_LIMIT):
    helmet.move()
    publish_telemetry()
    time.sleep(3)

mqtt_client.loop_stop()