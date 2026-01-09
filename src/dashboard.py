# src/dashboard_terminal.py
"""
Terminal-based Real-time Dashboard
No external UI libraries - just beautiful terminal output
"""

import paho.mqtt.client as mqtt
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import time
import threading

load_dotenv()

# MQTT Configuration
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS")
BROKER_PORT = int(os.getenv("BROKER_PORT"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASIC_TOPIC = os.getenv("MQTT_BASIC_TOPIC") + MQTT_USERNAME

TOPIC_HELMET = os.getenv("TOPIC_HELMET")
TOPIC_STATION = os.getenv("TOPIC_STATION")
TOPIC_MANAGER = os.getenv("TOPIC_MANAGER")
TOPIC_ALARM = os.getenv("TOPIC_ALARM")

# Global data
helmets_data = {}
stations_data = {}
alarm_state = {
    'siren': False,
    'zones': []
}

mqtt_connected = False
message_count = 0
data_lock = threading.Lock()

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_battery_bar(battery, width=15):
    """Generate a visual battery bar"""
    filled = int((battery / 100) * width)
    empty = width - filled
    
    if battery < 10:
        color = Colors.RED
    elif battery < 30:
        color = Colors.YELLOW
    else:
        color = Colors.GREEN
    
    bar = color + '█' * filled + Colors.END + '░' * empty
    return bar

def get_status_icon(led):
    """Get status icon and color"""
    if led == 1:
        return f"{Colors.YELLOW}🔋 CHARGING{Colors.END}"
    else:
        return f"{Colors.CYAN}⚒️  WORKING{Colors.END}"

def print_dashboard():
    """Print the dashboard to terminal"""
    with data_lock:
        helmets = dict(helmets_data)
        stations = dict(stations_data)
        current_alarm = dict(alarm_state)
    
    clear_screen()
    
    # === HEADER ===
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🏗️  CONSTRUCTION SITE MONITORING DASHBOARD (ALL DATA){Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")
    
    # Connection Status
    if mqtt_connected:
        status = f"{Colors.GREEN}✅ CONNECTED{Colors.END}"
    else:
        status = f"{Colors.RED}❌ DISCONNECTED{Colors.END}"
    
    print(f"📡 MQTT Status: {status}  |  📊 Messages: {Colors.BOLD}{message_count}{Colors.END}")
    print(f"⏰ Last Update: {Colors.BOLD}{datetime.now().strftime('%H:%M:%S')}{Colors.END}")
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}\n")
    
    if not helmets and not stations:
        print(f"{Colors.YELLOW}⏳ Waiting for device data...{Colors.END}\n")
        return

    # === ALARM SECTION ===
    print(f"{Colors.BOLD}🚨 ALARM SYSTEM{Colors.END}")
    print(f"{'─'*80}")
    
    siren_status = f"{Colors.RED}📢 ON (SOUNDING){Colors.END}" if current_alarm['siren'] else f"{Colors.GREEN}🔕 OFF (SILENT){Colors.END}"
    print(f"🔊 Siren Status: {siren_status}")
    
    zones = current_alarm['zones']
    if zones:
        zone_str = ", ".join(zones)
        print(f"🖥️  Display Zones: {Colors.RED}{zone_str}{Colors.END}")
    else:
        print(f"🖥️  Display Zones: {Colors.GREEN}None (Safe){Colors.END}")
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}\n")


    # === STATIONS SECTION ===
    print(f"{Colors.BOLD}🌩️  ENVIRONMENTAL STATIONS{Colors.END}")
    print(f"{'─'*80}")
    
    if not stations:
         print(f"{Colors.YELLOW}No stations connected.{Colors.END}")
    else:
        # Header Row
        print(f"{Colors.UNDERLINE}{'ID':<10} {'Dust':<10} {'Noise':<10} {'Gas':<10} {'Position':<25} {'Status'}{Colors.END}")
        
        for s_id, data in sorted(stations.items()):
            dust = data['dust']
            noise = data['noise']
            gas = data['gas']
            
            # Simple threshold check for display color
            d_col = Colors.RED if dust > 50 else Colors.GREEN
            n_col = Colors.RED if noise > 80 else Colors.GREEN
            g_col = Colors.RED if gas > 1.0 else Colors.GREEN
            
            pos_str = f"({data['lat']:.4f}, {data['lon']:.4f})"
            warn_icon = "🔴" if (dust > 50 or noise > 80 or gas > 1.0) else "🟢"
            
            print(
                f"{s_id:<10} "
                f"{d_col}{dust:<10.2f}{Colors.END} "
                f"{n_col}{noise:<10.2f}{Colors.END} "
                f"{g_col}{gas:<10.2f}{Colors.END} "
                f"{pos_str:<25} "
                f"{warn_icon}"
            )
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}\n")


    # === HELMETS SECTION ===
    print(f"{Colors.BOLD}⛑️  SMART HELMETS{Colors.END}")
    print(f"{'─'*80}")
    
    if not helmets:
        print(f"{Colors.YELLOW}No helmets connected.{Colors.END}")
    else:
        for helmet_id, data in sorted(helmets.items()):
            battery = data['battery']
            
            # Battery color
            if battery < 10:
                batt_col = Colors.RED
            elif battery < 30:
                batt_col = Colors.YELLOW
            else:
                batt_col = Colors.GREEN
            
            icon = get_status_icon(data['led'])
            pos_str = f"Lat {data['lat']:.5f}, Lon {data['lon']:.5f}"
            
            print(f"User {Colors.BOLD}{helmet_id}{Colors.END}: {icon}  |  Bat: {batt_col}{battery}%{Colors.END} {get_battery_bar(battery)}  |  Pos: {Colors.CYAN}{pos_str}{Colors.END}")

    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}Press Ctrl+C to exit{Colors.END}\n")

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        
        # Subscribe to everything
        topics = [
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_HELMET}/#", 0),
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_STATION}/#", 0),
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/#", 0)
        ]
        client.subscribe(topics)
    else:
        mqtt_connected = False

def on_message(client, userdata, message):
    global helmets_data, stations_data, alarm_state, message_count
    
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode("utf-8"))
        message_count += 1
        
        with data_lock:
            # HELMET TELEMETRY
            if f"/{TOPIC_HELMET}/" in topic and "telemetry" in topic:
                h_id = payload.get('id')
                if h_id:
                    helmets_data[h_id] = {
                        'id': h_id,
                        'lat': payload.get('latitude'),
                        'lon': payload.get('longitude'),
                        'battery': payload.get('battery'),
                        'led': payload.get('led'),
                        'time': datetime.now().strftime("%H:%M:%S")
                    }

            # STATION TELEMETRY
            elif f"/{TOPIC_STATION}/" in topic and "telemetry" in topic:
                s_id = payload.get('id')
                if s_id:
                    stations_data[s_id] = {
                        'id': s_id,
                        'lat': payload.get('latitude'),
                        'lon': payload.get('longitude'),
                        'dust': float(payload.get('dust', 0)),
                        'noise': float(payload.get('noise', 0)),
                        'gas': float(payload.get('gas', 0)),
                        'time': datetime.now().strftime("%H:%M:%S")
                    }

            # ALARM COMMANDS (Infer state from Manager commands)
            elif f"/{TOPIC_ALARM}/" in topic and "command" in topic:
                cmd = payload.get('command')
                if cmd == 'turn_siren_on':
                    alarm_state['siren'] = True
                elif cmd == 'turn_siren_off':
                    alarm_state['siren'] = False
                elif cmd == 'update_display':
                    alarm_state['zones'] = payload.get('zones', [])
            
    except Exception as e:
        pass

def start_mqtt():
    """Start MQTT client"""
    # Unique ID for dashboard
    import uuid
    client_id = f"dashboard-terminal-{MQTT_USERNAME}-{uuid.uuid4().hex[:6]}"
    
    mqtt_client = mqtt.Client(client_id)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    try:
        mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
        mqtt_client.loop_start()
        return mqtt_client
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def main():
    """Main dashboard loop"""
    # Start MQTT
    mqtt_client = start_mqtt()
    
    if not mqtt_client:
        return
    
    time.sleep(1) # Wait for connect
    
    # Main loop - refresh every second
    try:
        while True:
            print_dashboard()
            time.sleep(1)
    except KeyboardInterrupt:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print(f"\n{Colors.GREEN}✅ Dashboard stopped{Colors.END}\n")

if __name__ == "__main__":
    main()