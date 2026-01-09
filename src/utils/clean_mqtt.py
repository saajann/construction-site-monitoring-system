import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import time

# Add src to path to load env correctly if needed, though we just need dotenv
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

load_dotenv()

BROKER_ADDRESS = os.getenv("BROKER_ADDRESS")
BROKER_PORT = int(os.getenv("BROKER_PORT"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC") + MQTT_USERNAME

received_topics = set()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to {BROKER_ADDRESS} with result code {rc}")
    topic = f"{MQTT_BASIC_TOPIC}/#"
    print(f"Subscribing to {topic} to find retained messages...")
    client.subscribe(topic)

def on_message(client, userdata, msg):
    if msg.retain:
        print(f"🧹 Clearing retained message on: {msg.topic}")
        # To clear a retained message, publish an empty payload with retain=True
        client.publish(msg.topic, payload=None, qos=0, retain=True)
        received_topics.add(msg.topic)

def main():
    client = mqtt.Client("cleaner_script")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT)
        client.loop_start()
        
        print("Waiting for retained messages (5 seconds)...")
        time.sleep(5)
        
        if not received_topics:
            print("✨ No retained messages found.")
        else:
            print(f"✅ Cleared {len(received_topics)} retained messages.")
            
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
