# src/process/alarm.py

# sub data collector / manager -> TO DO

import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import json

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
TOPIC_MANAGER = os.getenv("TOPIC_MANAGER")

# subscribe to topics 
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Subscribe to manager commands for this alarm
    # Topic: /base/manager/alarm/alarm_id/command (using wildcard for all alarms for now or specific)
    # Let's subscribe to all alarm commands from manager
    command_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/{TOPIC_ALARM}/#"
    client.subscribe(command_topic)
    print(f"✅ Subscribed to: {command_topic}")

# method to receive asynchronous messages
def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        topic = message.topic
        print(f"\n📨 Received: {topic}")
        print(f"📦 Payload: {payload}")

        command = payload.get("command")
        
        if command == "turn_siren_on":
            alarm_system.turn_siren_on()
            print(f"[ALM] 📥 CMD | Siren ON  📢")
        elif command == "turn_siren_off":
            alarm_system.turn_siren_off()
            print(f"[ALM] 📥 CMD | Siren OFF 🔕")
        elif command == "update_display":
            import csv
            
            new_zones = sorted(list(set(payload.get("zones", []))))
            
            # Write key output to display.csv
            display_csv = ROOT / "data" / "display.csv"
            try:
                with open(display_csv, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["zone_id"])
                    for z_id in new_zones:
                        writer.writerow([z_id])
                print(f"[ALM] 💾 Saved dangerous zones to {display_csv}")
            except Exception as e:
                print(f"❌ Failed to write display.csv: {e}")

            # Keep existing logic for internal state (if needed later)
            current_zones = set(alarm_system.display)
            
            # Identify zones to add and remove
            to_add = set(new_zones) - current_zones
            to_remove = current_zones - set(new_zones)
            
            for z_id in to_add:
                alarm_system.add_dangerous_zone(z_id)
                
            for z_id in to_remove:
                alarm_system.remove_dangerous_zone(z_id)
            
            print(f"[ALM] 📥 CMD | Update Display | Zones: {alarm_system.display}")
        else:
            print(f"ℹ️  Unknown command: {command}")

    except json.JSONDecodeError:
        print(f"❌ Failed to decode JSON payload: {message.payload}")
    except Exception as e:
        print(f"❌ Error processing message: {e}")


# configuration variables
alarm_id = "alarm_001"
alarm_system = SafetyAlarmSystem()

mqtt_client = mqtt.Client(alarm_id)
mqtt_client.on_message = on_message
mqtt_client.on_connect = on_connect

# Set Account Username & Password
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

print("Connecting to " + BROKER_ADDRESS + " port: " + str(BROKER_PORT))
mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT)

# start comunication
try:
    print(f"🔔 Alarm {alarm_id} started. Waiting for commands...")
    mqtt_client.loop_forever()
except KeyboardInterrupt:
    print("\n🛑 Shutting down alarm...")
    mqtt_client.disconnect()