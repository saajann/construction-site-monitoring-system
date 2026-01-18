# src/process/helmet.py
# pub helmet info -> DONE
# sub data collector / manager -> DONE

import paho.mqtt.client as mqtt
import time
import random
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import csv
import threading
import json

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
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC") + MQTT_USERNAME
MESSAGE_LIMIT = int(os.getenv("MESSAGE_LIMIT"))
TIME_BETWEEN_MESSAGE = int(os.getenv("TIME_BETWEEN_MESSAGE"))
TOPIC_HELMET = os.getenv("TOPIC_HELMET")
TOPIC_MANAGER = os.getenv("TOPIC_MANAGER")

CSV_PATH = ROOT / "data" / "static" / "helmets.csv"
SITE_CSV_PATH = ROOT / "data" / "static" / "site.csv"


def load_site_boundaries(csv_path):
    """Load site boundaries from CSV and return polygon vertices"""
    polygon = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            polygon.append((lat, lon))
    
    return {"polygon": polygon}


def on_connect(client, userdata, flags, rc):
    """Callback when helmet connects to broker"""
    helmet_id = userdata['helmet_id']
    print(f"Helmet {helmet_id} connected with result code {rc}")
    
    if rc == 0:
        # Subscribe to commands from manager for this specific helmet
        command_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/{TOPIC_HELMET}/{helmet_id}/command"
        client.subscribe(command_topic, qos=0)
        print(f"✅ Helmet {helmet_id} subscribed to: {command_topic}")


def on_message(client, userdata, message):
    """Callback when helmet receives a command from manager"""
    helmet = userdata['helmet']
    helmet_id = userdata['helmet_id']
    
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode("utf-8"))
        
        print(f"\n{'='*50}")
        print(f"📨 Helmet {helmet_id} received command")
        print(f"   Topic: {topic}")
        print(f"   Payload: {payload}")
        
        # Process command
        command = payload.get('command')
        
        if command == 'set_led':
            new_led_status = payload.get('led')
            if new_led_status is not None:
                helmet.set_led(new_led_status)
                print(f"✅ LED status updated: {new_led_status}")
                if new_led_status == 1:
                    print(f"🔋 Helmet {helmet_id} entering CHARGING mode")
                else:
                    print(f"⚒️  Helmet {helmet_id} entering WORK mode")
        
        elif command == 'alert':
            alert_message = payload.get('message', 'Alert!')
            print(f"🚨 ALERT received: {alert_message}")
            # TODO: Implement alert handling (buzzer, vibration, etc.)
        
        else:
            print(f"⚠️  Unknown command: {command}")
        
        print(f"{'='*50}\n")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
    except Exception as e:
        print(f"❌ Error processing command: {e}")


def start_helmet_device(helmet_id, latitude, longitude, boundaries):
    """
    Start a helmet device that:
    1. Publishes telemetry
    2. Subscribes to manager commands
    3. Reacts to commands by changing state
    """
    # Setup client MQTT with unique ID
    client_id = f"python-helmet-{helmet_id}-{MQTT_USERNAME}"
    mqtt_client = mqtt.Client(client_id)
    
    # Create helmet instance
    position = GPS(latitude, longitude)
    helmet = WorkerSmartHelmet(helmet_id, position, boundaries)
    
    # Set user data (shared between callbacks)
    mqtt_client.user_data_set({
        'helmet_id': helmet_id,
        'helmet': helmet
    })
    
    # Set callbacks
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    # Set credentials
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    print(f"Connecting helmet {helmet_id} to {BROKER_ADDRESS}:{BROKER_PORT}")
    mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT)
    
    # Start loop (non-blocking)
    mqtt_client.loop_start()
    
    # Topics
    info_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_HELMET}/{helmet_id}/info"
    telemetry_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_HELMET}/{helmet_id}/telemetry"
    
    # 1. Publish static info ONCE with retain=True
    info_payload = helmet.static_info()
    mqtt_client.publish(info_topic, info_payload, qos=1, retain=True)
    print(f"[HLM-{helmet_id}] ℹ️  INFO Published: {info_topic}")
    
    # Telemetry publishing loop
    
    # for message_id in range(MESSAGE_LIMIT):
    while True:
        # Simulate helmet behavior based on LED status
        # LED = 0 -> WORK mode (moving, battery decreasing)
        # LED = 1 -> CHARGING mode (stationary, battery increasing)
        
        if helmet.led == 0:
            # WORK MODE
            helmet.move()
            helmet.descrease_battery_level(random.randint(1, 10))  # Slower drain
        else:
            # CHARGING MODE
            helmet.recharge_battery(random.randint(5, 10))  # Faster charge
        
        # Publish telemetry (SenML)
        payload = helmet.senml_telemetry()
        mqtt_client.publish(telemetry_topic, payload, 0, False)
        
        # Clean Logic
        log_msg = (
            f"[HLM-{helmet_id}] 📤 SENT | "
            f"Bat: {helmet.battery:3d}% | "
            f"LED: {helmet.led} | "
            f"Pos: ({helmet.position.latitude:.5f}, {helmet.position.longitude:.5f})"
        )
        print(log_msg)
        
        time.sleep(TIME_BETWEEN_MESSAGE)
    
    # Cleanup
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print(f"Helmet {helmet_id} disconnected")


def load_helmets(csv_path):
    """Load helmet configuration from CSV"""
    helmets = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            helmets.append(
                (row["id"], float(row["latitude"]), float(row["longitude"]))
            )
    return helmets


def main():
    print("\n" + "="*60)
    print("⛑️  STARTING SMART HELMETS")
    print("="*60 + "\n")
    
    helmets = load_helmets(CSV_PATH)
    boundaries = load_site_boundaries(SITE_CSV_PATH)
    threads = []
    
    for helmet in helmets:
        t = threading.Thread(
            target=start_helmet_device,
            args=(*helmet, boundaries),
            daemon=True
        )
        t.start()
        threads.append(t)
        print(f"✅ Helmet {helmet[0]} started")
    
    print(f"\n{'='*60}")
    print(f"All {len(helmets)} helmets running")
    print(f"{'='*60}\n")
    
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down helmets...")


if __name__ == "__main__":
    main()