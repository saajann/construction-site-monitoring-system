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
import csv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from model.site import Site, Sector
from model.gps import AreaVertices, GPS
import math

load_dotenv()

# FIXED VARIABLES
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS")
BROKER_PORT = int(os.getenv("BROKER_PORT"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC") + MQTT_USERNAME

MONITORING_STATION_RANGE = int(os.getenv("MONITORING_STATION_RANGE", 10))


TOPIC_HELMET = os.getenv("TOPIC_HELMET")
TOPIC_MANAGER = os.getenv("TOPIC_MANAGER")
TOPIC_STATION = os.getenv("TOPIC_STATION")
TOPIC_ALARM = os.getenv("TOPIC_ALARM")

# Battery limits
BATTERY_LOW_LIMIT = int(os.getenv("BATTERY_LOW_LIMIT", 10))
BATTERY_FULL_LIMIT = int(os.getenv("BATTERY_FULL_LIMIT", 100))

# Environmental Limits
DUST_LIMIT = float(os.getenv("DUST_LIMIT", 50.0))
NOISE_LIMIT = float(os.getenv("NOISE_LIMIT", 50.0))
GAS_LIMIT = float(os.getenv("GAS_LIMIT", 1.0)) # Presence of gas

# Grid Configuration
SECTOR_SIZE_METERS = float(os.getenv("SECTOR_SIZE_METERS", 10.0))


class DataCollectorManager:
    """Main manager class for helmet monitoring and control"""
    
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        
        # Track helmet states
        self.helmet_states = {}  # {helmet_id: {'battery': int, 'led': int, 'position': tuple}}
        self.station_states = {} # {station_id: {...}}
        
        # Load Site Vertices from Static CSV
        site_csv_path = ROOT / "data" / "static" / "site.csv"
        vertices = []
        try:
            with open(site_csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vertices.append(GPS(float(row["latitude"]), float(row["longitude"])))
            
            if len(vertices) != 4:
                print("⚠️  Warning: site.csv does not have exactly 4 vertices. Using default hardcoded area.")
                raise ValueError("Valid site.csv not found")
                
            print(f"✅ Loaded {len(vertices)} site vertices from {site_csv_path}")
            self.site = Site(AreaVertices(vertices))
            
        except Exception as e:
            print(f"⚠️  Failed to load site.csv: {e}. Using default values.")
            # Fallback to hardcoded (100x100m approximate area)
            # Try to get from env or use defaults
            fallback_lat = float(os.getenv("SITE_ORIGIN_LAT", 45.156))
            fallback_lon = float(os.getenv("SITE_ORIGIN_LON", 10.791))
            
            p1 = GPS(fallback_lat, fallback_lon)
            p2 = GPS(fallback_lat, fallback_lon + 0.0012)
            p3 = GPS(fallback_lat + 0.0009, fallback_lon + 0.0012)
            p4 = GPS(fallback_lat + 0.0009, fallback_lon)
            self.site = Site(AreaVertices([p1, p2, p3, p4]))

        self.site.create_grid(sector_size_meters=SECTOR_SIZE_METERS)
        
        # Internal States for Tracking
        self.helmet_states = {} # {id: {latitude, longitude, battery, ...}}
        self.station_states = {} # {id: {latitude, longitude, is_dangerous, ...}}
        self.station_danger_zones = {} # {station_id: [sector_id, ...]}
        self.current_dangerous_sector_ids = set() # Set of sector IDs currently dangerous
        self.workers_in_danger = set() # Set of helmet_ids currently in danger
        self.last_sent_zones = None # For optimization
        self.siren_active = False # To avoid redundant siren commands
        
        self._load_helmets_from_csv()
        self._load_stations_from_csv()
        self.update_sectors_csv() # Initial save
        self.update_helmets_csv() # Initial save with header
        self.update_stations_csv() # Initial save with header
        self.update_alarm_status_csv() # Initial save with header
    
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
            
            # Print less verbose logs for cleaner output
            # if random.random() < 0.1: # Sample logs
            #     print(f"📨 Received: {topic}")
            
            # Route message based on topic
            if f"/{TOPIC_HELMET}/" in topic:
                self._handle_helmet_message(topic, payload)
                self.update_helmets_csv()
            elif f"/{TOPIC_STATION}/" in topic:
                self._handle_station_message(topic, payload)
                self.update_stations_csv()
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")

    def _handle_station_message(self, topic, payload):
        """Process station telemetry"""
        station_id = payload.get('id')
        if not station_id:
            return

        # Store/Update station state
        self.station_states[station_id] = payload
        
        dust = float(payload.get('dust', 0))
        noise = float(payload.get('noise', 0))
        gas = float(payload.get('gas', 0))
        lat = float(payload.get('latitude', 0))
        lon = float(payload.get('longitude', 0))

        # Check thresholds
        is_dangerous = False
        danger_reasons = []
        
        if dust > DUST_LIMIT:
            is_dangerous = True
            danger_reasons.append(f"Dust ({dust})")
        if noise > NOISE_LIMIT:
            is_dangerous = True
            danger_reasons.append(f"Noise ({noise})")
        if gas > GAS_LIMIT:
            is_dangerous = True
            danger_reasons.append(f"Gas ({gas})")

        # Dynamic Grid Update
        if station_id not in self.station_states:
            self.station_states[station_id] = {}
        
        self.station_states[station_id].update({
            'latitude': lat,
            'longitude': lon,
            'dust': dust,
            'noise': noise,
            'gas': gas,
            'is_dangerous': is_dangerous
        })
        
        self._update_station_danger_zone(station_id, lat, lon, is_dangerous)

        status_icon = "🟢" if not is_dangerous else "🔴"
        print(
            f"[MGR] 📥 RECV Station {station_id} | "
            f"{status_icon} Status | "
            f"Dust: {dust:5.1f}, Noise: {noise:5.1f}, Gas: {gas:4.2f}"
        )

        if is_dangerous:
             print(f"    ⚠️  DANGER DETAIL: {', '.join(danger_reasons)}")

    def _update_station_danger_zone(self, station_id, lat, lon, is_dangerous):
        """
        Update the grid map based on station status.
        If station moves, we clear old danger zones.
        If new readings are safe, we clear danger zones.
        If new readings are dangerous, we mark sectors within 10m radius.
        """
        # 1. Clear previous danger zones for this station
        if station_id in self.station_danger_zones:
            old_sector_ids = self.station_danger_zones[station_id]
            for s_id in old_sector_ids:
                if s_id in self.current_dangerous_sector_ids:
                    self.current_dangerous_sector_ids.remove(s_id)
            del self.station_danger_zones[station_id]

        # 2. If dangerous, calculate new sectors and mark them
        if is_dangerous:
            affected_sectors = self.site.get_sectors_in_radius(lat, lon, float(MONITORING_STATION_RANGE))
            affected_ids = []
            
            for sector in affected_sectors:
                self.current_dangerous_sector_ids.add(sector.id)
                affected_ids.append(sector.id)
            
            self.station_danger_zones[station_id] = affected_ids
        
        # 3. Send updated list of dangerous zones to Alarm Display ONLY if changed
        all_dangerous_zones = sorted(list(self.current_dangerous_sector_ids))
        
        # Compare with last sent
        if self.last_sent_zones != all_dangerous_zones:
            self.last_sent_zones = all_dangerous_zones
            self._send_alarm_display_update("alarm_001", all_dangerous_zones)
            self.update_sectors_csv() # Update CSV on change
        else:
            # print(f"    [MGR] ℹ️  Zones unchanged, skipping update")
            pass

    def _send_alarm_display_update(self, alarm_id, zones):
        """
        Send list of dangerous zones to alarm display
        """
        command_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/{TOPIC_ALARM}/{alarm_id}/command"
        
        payload = {
            "command": "update_display",
            "zones": zones,
            "timestamp": time.time()
        }
        
        self.mqtt_client.publish(command_topic, json.dumps(payload), qos=0, retain=False)
        print(f"    [MGR] 📤 CMD SENT to Alarm {alarm_id} | Update Zones: {zones}")


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
            pass # print(f"🚨 Command sent to alarm {alarm_id}: {command}")
        else:
            print(f"❌ Failed to send command to alarm {alarm_id}")

    def _handle_helmet_message(self, topic, payload):
        """Process helmet telemetry and apply business logic"""
        helmet_id = payload.get('id')
        battery = payload.get('battery')
        led_status = payload.get('led')
        lat = payload.get('latitude')
        lon = payload.get('longitude')
        
        if not helmet_id:
            return
        
        # Update helmet state
        if helmet_id not in self.helmet_states:
            self.helmet_states[helmet_id] = {}
        
        self.helmet_states[helmet_id].update({
            'battery': battery,
            'led': led_status,
            'latitude': lat,
            'longitude': lon
        })
        
        # Apply business logic
        self._check_helmet_battery(helmet_id, battery, led_status)
        self._check_worker_safety(helmet_id, lat, lon)

        print(
            f"[MGR] 📥 RECV Helmet  {helmet_id} | "
            f"Bat: {battery:3d}% | "
            f"LED: {led_status} | "
            f"Pos: ({lat:.5f}, {lon:.5f})"
        )

    def _check_worker_safety(self, helmet_id, lat, lon):
        """
        Check if worker is in a dangerous sector
        """
        if lat is None or lon is None:
            return

        if lat is None or lon is None:
            return

        sector = self.site.get_sector_by_coords(lat, lon)
        in_danger = False
        
        if sector and sector.id in self.current_dangerous_sector_ids:
            in_danger = True
            if helmet_id not in self.workers_in_danger:
                print(f"🚨 ALERT: Worker {helmet_id} entered DANGEROUS Sector ({sector.id})!")
                self.workers_in_danger.add(helmet_id)
        else:
            if helmet_id in self.workers_in_danger:
                 print(f"✅ Worker {helmet_id} left dangerous sector")
                 self.workers_in_danger.remove(helmet_id)

        # Update Siren State based on global danger
        should_siren_be_on = len(self.workers_in_danger) > 0
        
        if should_siren_be_on and not self.siren_active:
            print(f"📢 DANGER ACTIVE (Workers: {len(self.workers_in_danger)}) -> SIREN ON")
            self._send_alarm_command("alarm_001", "turn_siren_on")
            self.siren_active = True
            self.update_alarm_status_csv()  # Update alarm status file
            
        elif not should_siren_be_on and self.siren_active:
            print(f"🟢 ALL CLEAR -> SIREN OFF")
            self._send_alarm_command("alarm_001", "turn_siren_off")
            self.siren_active = False
            self.update_alarm_status_csv()  # Update alarm status file
    
    def _check_helmet_battery(self, helmet_id, battery, current_led_status):
        """
        Business Logic: Battery monitoring
        - If battery < 10 and LED is OFF (0) -> Turn LED ON (1) for charging
        - If battery >= 100 and LED is ON (1) -> Turn LED OFF (0) for work
        """
        
        if battery is None or current_led_status is None:
            return
        
        # Battery LOW: activate charging mode (LED ON)
        if battery < BATTERY_LOW_LIMIT and current_led_status == 0:
            print(f"    🔋 LOW BATTERY ({battery}%) -> CMD: CHARGE ON")
            self._send_led_command(helmet_id, 1)
        
        # Battery FULL: deactivate charging mode (LED OFF)
        elif battery >= BATTERY_FULL_LIMIT and current_led_status == 1:
            print(f"    🔋 BATTERY FULL ({battery}%) -> CMD: CHARGE OFF")
            self._send_led_command(helmet_id, 0)
        
        else:
            # print(f"ℹ️  Helmet {helmet_id}: Battery={battery}%, LED={current_led_status} (no action needed)")
            pass
    
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
            print(f"    [MGR] 📤 CMD SENT to Helmet {helmet_id}: {payload_json}")
        else:
            print(f"❌ Failed to send command to helmet {helmet_id}")
        
        return result
    
    def get_helmet_status(self, helmet_id):
        """Get current status of a helmet"""
        return self.helmet_states.get(helmet_id, {})

    def update_sectors_csv(self):
        """
        Saves the current grid to map.csv with STATUS.
        Format: id, vertices_json, status
        status: 0 = SAFE, 1 = DANGEROUS
        """
        import csv
        filepath = ROOT / "data" / "dynamic" / "map.csv"
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "vertices_json", "status"])
                for sector in self.site.grid:
                    is_dangerous = 1 if sector.id in self.current_dangerous_sector_ids else 0
                    coords = [[p.latitude, p.longitude] for p in sector.area_vertices.vertices]
                    writer.writerow([sector.id, json.dumps(coords), is_dangerous])
            # print(f"    [MGR] 💾 Saved map.csv")
        except Exception as e:
            print(f"❌ Failed to save map.csv: {e}")

    def update_helmets_csv(self):
        """
        Saves current helmet positions and states to helmets.csv
        Format: id, latitude, longitude, battery, is_dangerous
        """
        import csv
        filepath = ROOT / "data" / "dynamic" / "helmets.csv"
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "latitude", "longitude", "battery", "led"])
                for helmet_id, state in self.helmet_states.items():
                    lat = state.get("latitude", 0)
                    lon = state.get("longitude", 0)
                    battery = state.get("battery", 0)
                    led = state.get("led", 0)
                    writer.writerow([helmet_id, lat, lon, battery, led])
            # print(f"    [MGR] 💾 Saved helmets.csv")
        except Exception as e:
            print(f"❌ Failed to save helmets.csv: {e}")

    def _load_helmets_from_csv(self):
        """Loads initial helmet data from STATIC CSV to avoid wiping config"""
        filepath = ROOT / "data" / "static" / "helmets.csv"
        if not filepath.exists():
            return
        try:
            with open(filepath, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    h_id = row.get('id')
                    if h_id:
                        self.helmet_states[h_id] = {
                            'latitude': float(row.get('latitude', 0)),
                            'longitude': float(row.get('longitude', 0)),
                            'battery': int(float(row.get('battery', 0))),
                            'led': int(float(row.get('led', 0)))
                        }
        except Exception as e:
            print(f"⚠️ Error loading helmets.csv: {e}")

    def update_stations_csv(self):
        """
        Saves current station positions and states to stations.csv
        Format: id, latitude, longitude, is_dangerous
        """
        import csv
        filepath = ROOT / "data" / "dynamic" / "stations.csv"
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "latitude", "longitude", "dust", "noise", "gas", "is_dangerous"])
                for station_id, state in self.station_states.items():
                    lat = state.get("latitude", 0)
                    lon = state.get("longitude", 0)
                    dust = state.get("dust", 0)
                    noise = state.get("noise", 0)
                    gas = state.get("gas", 0)
                    is_dangerous = 1 if state.get("is_dangerous", False) else 0
                    writer.writerow([station_id, lat, lon, dust, noise, gas, is_dangerous])
        except Exception as e:
            print(f"❌ Failed to save stations.csv: {e}")

    def _load_stations_from_csv(self):
        """Loads initial station data from STATIC CSV to avoid wiping config"""
        filepath = ROOT / "data" / "static" / "stations.csv"
        if not filepath.exists():
            return
        try:
            with open(filepath, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    s_id = row.get('id')
                    if s_id:
                        self.station_states[s_id] = {
                            'latitude': float(row.get('latitude', 0)),
                            'longitude': float(row.get('longitude', 0)),
                            'is_dangerous': int(row.get('is_dangerous', 0)) == 1
                        }
        except Exception as e:
            print(f"⚠️ Error loading stations.csv: {e}")

    def update_alarm_status_csv(self):
        """
        Saves current alarm status to alarm_status.csv
        Format: alarm_active
        """
        import csv
        filepath = ROOT / "data" / "dynamic" / "alarm_status.csv"
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["alarm_active"])
                writer.writerow([1 if self.siren_active else 0])
        except Exception as e:
            print(f"❌ Failed to save alarm_status.csv: {e}")


def main():
    print("\n" + "="*60)
    print("🏗️  CONSTRUCTION SITE DATA COLLECTOR & MANAGER")
    print("="*60 + "\n")
    
    # Setup MQTT client with unique ID
    # Setup MQTT client with unique ID to avoid conflicts
    import uuid
    client_id = f"python-manager-{MQTT_USERNAME}-{uuid.uuid4().hex[:6]}"
    mqtt_client = mqtt.Client(client_id)
    
    # Create manager instance
    manager = DataCollectorManager(mqtt_client)
    
    # Set callbacks
    mqtt_client.on_connect = manager.on_connect
    mqtt_client.on_message = manager.on_message
    
    def on_disconnect(client, userdata, rc):
        if rc != 0:
            print(f"❌ Unexpected disconnection. Result code: {rc}")
    
    mqtt_client.on_disconnect = on_disconnect
    
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