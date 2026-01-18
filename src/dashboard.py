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

def parse_senml(payload):
    """Helper to parse SenML list into a flat dictionary"""
    result = {}
    if isinstance(payload, list):
        for record in payload:
            if 'bn' in record and ':' in record['bn']:
                result['id'] = record['bn'].split(':')[-1]
            if 'n' in record:
                name = record['n']
                value = record.get('v')
                if value is None: value = record.get('vs')
                result[name] = value
    return result

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
        # Subscribe to all 4 main topic patterns
        # Subscribe to all telemetry and info topics
        topics = [
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_HELMET}/+/telemetry", 0),
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_HELMET}/+/info", 0),
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_STATION}/+/telemetry", 0),
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_STATION}/+/info", 0),
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/{TOPIC_HELMET}/+/command", 0),
            (f"{MQTT_BASIC_TOPIC}/{TOPIC_MANAGER}/{TOPIC_ALARM}/+/command", 0)
        ]
        client.subscribe(topics)
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
            
            # HELMET TELEMETRY or INFO
            if f"/{TOPIC_HELMET}/" in topic and (topic.endswith("/telemetry") or topic.endswith("/info")):
                data = parse_senml(payload)
                h_id = str(data.get('id', '???'))
                if h_id not in helmets_data: helmets_data[h_id] = {}
                
                # Update only fields that are present
                for key, data_key in [('battery', 'battery'), ('led', 'led'), ('lat', 'latitude'), ('lon', 'longitude')]:
                    if data_key in data:
                        helmets_data[h_id][key] = data[data_key]

            # STATION TELEMETRY or INFO
            elif f"/{TOPIC_STATION}/" in topic and (topic.endswith("/telemetry") or topic.endswith("/info")):
                data = parse_senml(payload)
                s_id = str(data.get('id', '???'))
                if s_id not in stations_data: stations_data[s_id] = {}
                
                for key in ['dust', 'noise', 'gas', 'latitude', 'longitude']:
                    if key in data:
                        stations_data[s_id][key] = data[key]

            # HELMET COMMANDS (From Manager)
            elif f"/{TOPIC_MANAGER}/{TOPIC_HELMET}/" in topic:
                h_id = topic.split('/')[-2]
                cmd = payload.get('command')
                val = payload.get('led')
                msg = f"{Colors.YELLOW}HELMET {h_id}{Colors.END} -> {Colors.BOLD}{cmd}{Colors.END} (led={val})"
                command_log.append({'time': curr_time, 'msg': msg})

            # ALARM COMMANDS (From Manager)
            elif f"/{TOPIC_MANAGER}/{TOPIC_ALARM}/" in topic:
                a_id = topic.split('/')[-2]
                cmd = payload.get('command')
                
                if cmd == 'turn_siren_on':
                    alarm_state['siren'] = True
                    msg = f"{Colors.RED}ALARM {a_id}{Colors.END} -> {Colors.BOLD}SIREN ON{Colors.END}"
                elif cmd == 'turn_siren_off':
                    alarm_state['siren'] = False
                    msg = f"{Colors.GREEN}ALARM {a_id}{Colors.END} -> {Colors.BOLD}SIREN OFF{Colors.END}"
                elif cmd == 'update_display':
                    zones = payload.get('zones', [])
                    alarm_state['zones'] = zones
                    msg = f"{Colors.BLUE}ALARM {a_id}{Colors.END} -> {Colors.BOLD}ZONES UPDATED{Colors.END} ({len(zones)} zones)"
                else:
                    msg = f"ALARM {a_id} -> {cmd}"
                
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