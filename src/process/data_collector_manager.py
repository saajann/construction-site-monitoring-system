# src/process/data_collector_manager.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from process.publisher.helmet import start_helmet_device
# from process.publisher.robot import start_robot_device
# from process.publisher.env_sensor import start_env_sensor_device

def main():
    """
    Data Collector & Manager
    """
    print("=== Starting Construction Site IoT System ===\n")
    
    # start helmets 
    print("Starting helmets...")
    start_helmet_device("001", 45.0, 45.0)
    # start_helmet_device("helmet_002", 45.1, 9.1)
    # start_helmet_device("helmet_003", 45.2, 9.2)
    
    print("\n=== All devices completed ===")

if __name__ == "__main__":
    main()