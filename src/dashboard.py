# src/dashboard.py
"""
Terminal-based Real-time Dashboard (Pure MQTT version)
Monitors 4 major topics: Helmet Telemetry, Station Telemetry, Helmet Commands, and Alarm Commands.
"""

import paho.mqtt.client as mqtt
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import time
import threading
from collections import deque

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

# Global data (Thread-safe)
helmets_data = {}
stations_data = {}
command_log = deque(maxlen=10) # Store last 10 commands
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
    GRAY = '\033[90m'

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_battery_bar(battery, width=15):
    """Generate a visual battery bar"""
    battery = max(0, min(100, battery))
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
    elif led == 2:
        return f"{Colors.RED}🚨 DANGER{Colors.END}"
    else:
        return f"{Colors.CYAN}⚒️  WORKING{Colors.END}"

def print_dashboard():
    """Print the dashboard to terminal"""
    with data_lock:
        helmets = dict(helmets_data)
        stations = dict(stations_data)
        current_alarm = dict(alarm_state)
        logs = list(command_log)
    
    clear_screen()
    
    # === HEADER ===
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🏗️  PURE MQTT MONITORING DASHBOARD{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*90}{Colors.END}\n")
    
    # Connection Status
    status = f"{Colors.GREEN}✅ CONNECTED{Colors.END}" if mqtt_connected else f"{Colors.RED}❌ DISCONNECTED{Colors.END}"
    print(f"📡 MQTT Status: {status}  |  📊 Total Messages: {Colors.BOLD}{message_count}{Colors.END}")
    print(f"⏰ Local Time: {Colors.BOLD}{datetime.now().strftime('%H:%M:%S')}{Colors.END}")
    print(f"{Colors.CYAN}{'─'*90}{Colors.END}\n")
    
    # === DEVICES OVERVIEW (HELMETS & STATIONS) ===
    col_width = 44
    
    # Split into two columns
    print(f"{Colors.BOLD}{'⛑️  SMART HELMETS':<{col_width}} | {'🌩️  ENVIRONMENTAL STATIONS':<{col_width}}{Colors.END}")
    print(f"{'─'*col_width}─┼─{'─'*col_width}")
    
    max_rows = max(len(helmets), len(stations))
    h_ids = sorted(helmets.keys())
    s_ids = sorted(stations.keys())
    
    for i in range(max(max_rows, 1)):
        # Helmet Column
        h_info = ""
        if i < len(h_ids):
            h_id = h_ids[i]
            h = helmets[h_id]
            batt = h.get('battery', 0)
            led = h.get('led', 0)
            h_info = f"{Colors.BOLD}{h_id}{Colors.END} {get_battery_bar(batt, 10)} {batt:3d}% {get_status_icon(led)}"
        elif i == 0 and not h_ids:
            h_info = f"{Colors.GRAY}Waiting for helmets...{Colors.END}"
            
        # Station Column
        s_info = ""
        if i < len(s_ids):
            s_id = s_ids[i]
            s = stations[s_id]
            dust, noise, gas = s.get('dust', 0), s.get('noise', 0), s.get('gas', 0)
            # Threshold markers
            is_warn = (dust > 50 or noise > 80 or gas > 1.0)
            warn_icon = "🔴" if is_warn else "🟢"
            s_info = f"{Colors.BOLD}{s_id}{Colors.END} {warn_icon} D:{dust:4.1f} N:{noise:4.1f} G:{gas:4.2f}"
        elif i == 0 and not s_ids:
            s_info = f"{Colors.GRAY}Waiting for stations...{Colors.END}"
            
        print(f"{h_info:<{col_width + (10 if i < len(h_ids) else 0)}} | {s_info}")
    
    print(f"{Colors.CYAN}{'─'*90}{Colors.END}\n")

    # === ALARM & DISPLAY SECTION ===
    print(f"{Colors.BOLD}🚨 SYSTEM ALARM & DISPLAY{Colors.END}")
    print(f"{'─'*90}")
    siren = f"{Colors.RED}📢 ON (SOUNDING){Colors.END}" if current_alarm['siren'] else f"{Colors.GREEN}🔕 OFF (SILENT){Colors.END}"
    print(f"🔊 Siren Status: {siren}")
    
    zones = current_alarm['zones']
    if zones:
        print(f"🖥️  Dangerous Zones on Display: {Colors.RED}{', '.join(zones[:10])}{' ...' if len(zones) > 10 else ''}{Colors.END}")
    else:
        print(f"🖥️  Dangerous Zones on Display: {Colors.GREEN}None (All areas safe){Colors.END}")
    print(f"{Colors.CYAN}{'─'*90}{Colors.END}\n")

    # === COMMAND LOG (REAL-TIME COMMANDS FROM MANAGER) ===
    print(f"{Colors.BOLD}📜 MANAGER COMMAND LOG (RECENT){Colors.END}")
    print(f"{'─'*90}")
    if not logs:
        print(f"{Colors.GRAY}No commands recorded yet.{Colors.END}")
    else:
        for log in logs:
            print(f"{Colors.GRAY}[{log['time']}]{Colors.END} {log['msg']}")
    
    print(f"\n{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"Press {Colors.BOLD}Ctrl+C{Colors.END} to exit")

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        # Subscribe to EVERYTHING under the project namespace
        client.subscribe(f"{MQTT_BASIC_TOPIC}/#", qos=1)
        print(f"✅ Dashboard subscribed to all topics under: {MQTT_BASIC_TOPIC}")
    else:
        mqtt_connected = False

def on_message(client, userdata, message):
    global helmets_data, stations_data, alarm_state, message_count, command_log
    
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode("utf-8"))
        curr_time = datetime.now().strftime("%H:%M:%S")
        
        with data_lock:
            message_count += 1
            
            parts = topic.split('/')
            if len(parts) < 3:
                return

            device_type = parts[-3]
            device_id = parts[-2]
            msg_type = parts[-1]

            # DEVICE INFO (Discovery)
            if msg_type == "info":
                if device_type == TOPIC_HELMET:
                    if device_id not in helmets_data:
                        helmets_data[device_id] = {'battery': 0, 'led': 0}
                elif device_type == TOPIC_STATION:
                    if device_id not in stations_data:
                        stations_data[device_id] = {'dust': 0, 'noise': 0, 'gas': 0}

            # TELEMETRY (SenML)
            elif msg_type == "telemetry":
                data = {}
                if isinstance(payload, list):
                    for entry in payload:
                        n, v = entry.get('n', ''), entry.get('v')
                        if 'gps.lat' in n: data['latitude'] = v
                        elif 'gps.lon' in n: data['longitude'] = v
                        elif 'sensor.battery' in n: data['battery'] = v
                        elif 'actuator.led' in n: data['led'] = v
                        elif 'sensor.dust' in n: data['dust'] = v
                        elif 'sensor.noise' in n: data['noise'] = v
                        elif 'sensor.gas' in n: data['gas'] = v
                
                if device_type == TOPIC_HELMET:
                    helmets_data[device_id] = {
                        'battery': int(data.get('battery', 0)),
                        'led': int(data.get('led', 0)),
                        'lat': data.get('latitude', 0),
                        'lon': data.get('longitude', 0)
                    }
                elif device_type == TOPIC_STATION:
                    stations_data[device_id] = {
                        'dust': data.get('dust', 0),
                        'noise': data.get('noise', 0),
                        'gas': data.get('gas', 0)
                    }

            # COMMANDS (From Manager)
            elif parts[-4] == TOPIC_MANAGER:
                cmd = payload.get('command')
                
                if device_type == TOPIC_HELMET:
                    val = payload.get('led')
                    msg = f"{Colors.YELLOW}HELMET {device_id}{Colors.END} -> {Colors.BOLD}{cmd}{Colors.END} (led={val})"
                elif device_type == TOPIC_ALARM:
                    if cmd == 'turn_siren_on':
                        alarm_state['siren'] = True
                        msg = f"{Colors.RED}ALARM {device_id}{Colors.END} -> {Colors.BOLD}SIREN ON{Colors.END}"
                    elif cmd == 'turn_siren_off':
                        alarm_state['siren'] = False
                        msg = f"{Colors.GREEN}ALARM {device_id}{Colors.END} -> {Colors.BOLD}SIREN OFF{Colors.END}"
                    elif cmd == 'update_display':
                        zones = payload.get('zones', [])
                        alarm_state['zones'] = [str(z) for z in zones]
                        msg = f"{Colors.BLUE}ALARM {device_id}{Colors.END} -> {Colors.BOLD}ZONES UPDATED{Colors.END} ({len(zones)} zones)"
                    else:
                        msg = f"ALARM {device_id} -> {cmd}"
                
                command_log.append({'time': curr_time, 'msg': msg})
            
    except Exception as e:
        # Silently fail on malformed JSON or other errors
        pass

def main():
    import uuid
    client_id = f"dashboard-terminal-{uuid.uuid4().hex[:6]}"
    client = mqtt.Client(client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
        client.loop_start()
        
        while True:
            print_dashboard()
            time.sleep(1)
            
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        print(f"\n{Colors.GREEN}✅ Dashboard stopped{Colors.END}\n")

if __name__ == "__main__":
    main()