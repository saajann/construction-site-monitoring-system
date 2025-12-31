# src/process/manager.py
"""
Data Collector & Manager
Responsibilities:
- Subscribe to helmet telemetry
- Analyze helmet data
- Publish commands to helmets (LED control)
"""

import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import json
import time
import random

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

load_dotenv()

# FIXED VARIABLES
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS")
BROKER_PORT = int(os.getenv("BROKER_PORT"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC") + MQTT_USERNAME

TOPIC_HELMET = os.getenv("TOPIC_HELMET")
TOPIC_MANAGER = os.getenv("TOPIC_MANAGER")
TOPIC_STATION = os.getenv("TOPIC_STATION")
TOPIC_ALARM = os.getenv("TOPIC_ALARM")

# Battery thresholds
BATTERY_LOW_THRESHOLD = 10
BATTERY_FULL_THRESHOLD = 100


class DataCollectorManager:
    """Main manager class for helmet monitoring and control"""
    
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        
        # Track helmet states
        self.helmet_states = {}  # {helmet_id: {'battery': int, 'led': int, 'position': tuple}}
        self.station_states = {} # {station_id: {...}}
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        print(f"Manager connected with result code {rc}")
        
        if rc == 0:
            # Subscribe to all helmet telemetry
            helmet_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_HELMET}/#"
            client.subscribe(helmet_topic, qos=0)
            print(f"✅ Subscribed to: {helmet_topic}")

            # Subscribe to all station telemetry
            station_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_STATION}/#"
            client.subscribe(station_topic, qos=0)
            print(f"✅ Subscribed to: {station_topic}")
        else:
            print(f"❌ Connection failed with code {rc}")
    
    def on_message(self, client, userdata, message):
        """Callback when message is received"""
        try:
            topic = message.topic
            payload = json.loads(message.payload.decode("utf-8"))
            
            print(f"\n{'='*60}")
            print(f"📨 Received: {topic}")
            print(f"📦 Payload: {payload}")
            
            # Route message based on topic
            if f"/{TOPIC_HELMET}/" in topic:
                self._handle_helmet_message(topic, payload)
            elif f"/{TOPIC_STATION}/" in topic:
                self._handle_station_message(topic, payload)
            
            print(f"{'='*60}\n")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")

    def _handle_station_message(self, topic, payload):
        """Process station telemetry"""
        station_id = payload.get('id')
        if not station_id:
            print("⚠️  No station ID in payload")
            return

        # Store/Update station state
        self.station_states[station_id] = payload
        print(f"🏢 Station {station_id} update: Dust={payload.get('dust_level')}, Noise={payload.get('noise_level')}")
        
        # Check for random alarm condition (Temporary Logic)
        rand = random.random()
        if rand < 0.15: 
            print("🎲 Random check triggered SIREN ON!")
            self._send_alarm_command("alarm_001", "turn_siren_on")
        elif rand < 0.30:
            print("🎲 Random check triggered SIREN OFF!")
            self._send_alarm_command("alarm_001", "turn_siren_off")

    def _send_alarm_command(self, alarm_id, command):
        """
        Send command to an alarm device
        """
        # Topic: /base/manager/alarm/alarm_id/command
        command_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/{TOPIC_ALARM}/{alarm_id}/command"
        
        payload = {
            "command": command,
            "timestamp": time.time()
        }
        
        payload_json = json.dumps(payload)
        
        result = self.mqtt_client.publish(command_topic, payload_json, qos=0, retain=False)
        
        if result.rc == 0:
            print(f"🚨 Command sent to alarm {alarm_id}: {command}")
        else:
            print(f"❌ Failed to send command to alarm {alarm_id}")

    def _handle_helmet_message(self, topic, payload):
        """Process helmet telemetry and apply business logic"""
        helmet_id = payload.get('id')
        battery = payload.get('battery')
        led_status = payload.get('led')
        
        if not helmet_id:
            print("⚠️  No helmet ID in payload")
            return
        
        # Update helmet state
        if helmet_id not in self.helmet_states:
            self.helmet_states[helmet_id] = {}
        
        self.helmet_states[helmet_id].update({
            'battery': battery,
            'led': led_status,
            'latitude': payload.get('latitude'),
            'longitude': payload.get('longitude')
        })
        
        # Apply business logic
        self._check_helmet_battery(helmet_id, battery, led_status)
    
    def _check_helmet_battery(self, helmet_id, battery, current_led_status):
        """
        Business Logic: Battery monitoring
        - If battery < 10 and LED is OFF (0) -> Turn LED ON (1) for charging
        - If battery >= 100 and LED is ON (1) -> Turn LED OFF (0) for work
        """
        
        if battery is None or current_led_status is None:
            return
        
        # Battery LOW: activate charging mode (LED ON)
        if battery < BATTERY_LOW_THRESHOLD and current_led_status == 0:
            print(f"🔋 LOW BATTERY DETECTED for helmet {helmet_id}: {battery}%")
            print(f"📤 Sending command: ACTIVATE CHARGING (LED ON)")
            self._send_led_command(helmet_id, 1)
        
        # Battery FULL: deactivate charging mode (LED OFF)
        elif battery >= BATTERY_FULL_THRESHOLD and current_led_status == 1:
            print(f"🔋 FULL BATTERY DETECTED for helmet {helmet_id}: {battery}%")
            print(f"📤 Sending command: DEACTIVATE CHARGING (LED OFF)")
            self._send_led_command(helmet_id, 0)
        
        else:
            print(f"ℹ️  Helmet {helmet_id}: Battery={battery}%, LED={current_led_status} (no action needed)")
    
    def _send_led_command(self, helmet_id, led_status):
        """
        Send LED control command to a specific helmet
        
        Args:
            helmet_id (str): ID of the helmet
            led_status (int): 0 = OFF (work mode), 1 = ON (charging mode)
        """
        # Topic structure: /base_topic/manager/helmet/helmet_id/command
        command_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/{TOPIC_HELMET}/{helmet_id}/command"
        
        payload = {
            "command": "set_led",
            "led": led_status,
            "timestamp": time.time()
        }
        
        payload_json = json.dumps(payload)
        
        # Publish command
        result = self.mqtt_client.publish(command_topic, payload_json, qos=0, retain=False)
        
        if result.rc == 0:
            print(f"✅ Command sent to helmet {helmet_id}")
            print(f"   Topic: {command_topic}")
            print(f"   Payload: {payload_json}")
        else:
            print(f"❌ Failed to send command to helmet {helmet_id}")
        
        return result
    
    def get_helmet_status(self, helmet_id):
        """Get current status of a helmet"""
        return self.helmet_states.get(helmet_id, {})


def main():
    print("\n" + "="*60)
    print("🏗️  CONSTRUCTION SITE DATA COLLECTOR & MANAGER")
    print("="*60 + "\n")
    
    # Setup MQTT client with unique ID
    client_id = f"python-manager-{MQTT_USERNAME}"
    mqtt_client = mqtt.Client(client_id)
    
    # Create manager instance
    manager = DataCollectorManager(mqtt_client)
    
    # Set callbacks
    mqtt_client.on_connect = manager.on_connect
    mqtt_client.on_message = manager.on_message
    
    # Set credentials
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # Connect
    print(f"🔌 Connecting to {BROKER_ADDRESS}:{BROKER_PORT}")
    mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    
    print("✅ Manager started. Monitoring helmets...\n")
    
    # Start loop
    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down manager...")
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()