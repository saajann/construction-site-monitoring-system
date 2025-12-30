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

# Global data
helmets_data = {}
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

def get_battery_bar(battery, width=20):
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
    
    clear_screen()
    
    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🏗️  CONSTRUCTION SITE MONITORING DASHBOARD{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")
    
    # Connection Status
    if mqtt_connected:
        status = f"{Colors.GREEN}✅ CONNECTED{Colors.END}"
    else:
        status = f"{Colors.RED}❌ DISCONNECTED{Colors.END}"
    
    print(f"📡 MQTT Status: {status}")
    print(f"📊 Messages Received: {Colors.BOLD}{message_count}{Colors.END}")
    print(f"⏰ Last Update: {Colors.BOLD}{datetime.now().strftime('%H:%M:%S')}{Colors.END}")
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}\n")
    
    if not helmets:
        print(f"{Colors.YELLOW}⏳ Waiting for helmet data...{Colors.END}\n")
        print(f"Make sure helmets are running:")
        print(f"  {Colors.CYAN}python ./src/process/helmet.py{Colors.END}\n")
        return
    
    # Overview Metrics
    total = len(helmets)
    charging = sum(1 for h in helmets.values() if h['led'] == 1)
    working = total - charging
    avg_battery = sum(h['battery'] for h in helmets.values()) / total if total > 0 else 0
    
    print(f"{Colors.BOLD}📊 OVERVIEW{Colors.END}")
    print(f"{'─'*80}")
    print(f"👷 Total Helmets: {Colors.BOLD}{total}{Colors.END}  |  ", end="")
    print(f"⚒️  Working: {Colors.CYAN}{working}{Colors.END}  |  ", end="")
    print(f"🔋 Charging: {Colors.YELLOW}{charging}{Colors.END}  |  ", end="")
    print(f"⚡ Avg Battery: {Colors.BOLD}{avg_battery:.0f}%{Colors.END}")
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}\n")
    
    # Helmet Details
    print(f"{Colors.BOLD}⛑️  HELMET STATUS{Colors.END}")
    print(f"{'─'*80}")
    
    for helmet_id, data in sorted(helmets.items()):
        battery = data['battery']
        led = data['led']
        
        # Battery color
        if battery < 10:
            battery_color = Colors.RED
        elif battery < 30:
            battery_color = Colors.YELLOW
        else:
            battery_color = Colors.GREEN
        
        print(f"\n{Colors.BOLD}Helmet {helmet_id}{Colors.END}")
        print(f"  Status: {get_status_icon(led)}")
        print(f"  Battery: {battery_color}{battery}%{Colors.END} {get_battery_bar(battery)}")
        print(f"  Position: {Colors.CYAN}Lat {data['lat']:.6f}, Lon {data['lon']:.6f}{Colors.END}")
        print(f"  Last Update: {data['time']}")
    
    print(f"\n{Colors.CYAN}{'─'*80}{Colors.END}\n")
    
    # Alerts
    print(f"{Colors.BOLD}⚠️  ALERTS{Colors.END}")
    print(f"{'─'*80}")
    
    low_battery = [h for h, d in helmets.items() if d['battery'] < 10 and d['led'] == 0]
    
    if low_battery:
        for helmet_id in low_battery:
            battery = helmets[helmet_id]['battery']
            print(f"{Colors.RED}🔴 CRITICAL: Helmet {helmet_id} at {battery}% and NOT charging!{Colors.END}")
    else:
        print(f"{Colors.GREEN}✅ All helmets operating normally{Colors.END}")
    
    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}Press Ctrl+C to exit{Colors.END}\n")

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        helmet_topic = f"{MQTT_BASIC_TOPIC}/{TOPIC_HELMET}/#"
        client.subscribe(helmet_topic, qos=0)
    else:
        mqtt_connected = False

def on_message(client, userdata, message):
    global helmets_data, message_count
    
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        helmet_id = payload.get('id')
        
        if helmet_id:
            message_count += 1
            with data_lock:
                helmets_data[helmet_id] = {
                    'id': helmet_id,
                    'lat': payload.get('latitude'),
                    'lon': payload.get('longitude'),
                    'battery': payload.get('battery'),
                    'led': payload.get('led'),
                    'time': datetime.now().strftime("%H:%M:%S")
                }
            
    except Exception as e:
        pass

def start_mqtt():
    """Start MQTT client"""
    client_id = f"dashboard-terminal-{MQTT_USERNAME}"
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
    print(f"\n{Colors.BOLD}{Colors.CYAN}Starting Construction Site Dashboard...{Colors.END}\n")
    
    # Start MQTT
    mqtt_client = start_mqtt()
    
    if not mqtt_client:
        print(f"{Colors.RED}Failed to connect to MQTT broker{Colors.END}")
        return
    
    print(f"{Colors.GREEN}✅ MQTT client started{Colors.END}")
    print(f"Connecting to {BROKER_ADDRESS}:{BROKER_PORT}...")
    time.sleep(2)
    
    # Main loop - refresh every second
    try:
        while True:
            print_dashboard()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Shutting down dashboard...{Colors.END}")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print(f"{Colors.GREEN}✅ Dashboard stopped{Colors.END}\n")

if __name__ == "__main__":
    main()