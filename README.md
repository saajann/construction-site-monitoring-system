# Construction Site Monitoring System

Industrial IoT system for real-time monitoring of construction sites, enhancing worker safety through automated tracking, environmental sensing, and intelligent alarm management.

Project for the course **"Intelligent Internet of Things"**, part of the Bachelor's Degree in **Computer Engineering** at the **Mantova campus of UNIMORE**, during the third year of study.

---

## Table of Contents
- [Project Idea](#project-idea)
- [Involved Devices](#involved-devices)
- [High-Level Architecture](#high-level-architecture)
- [System Features](#system-features)
- [Data Models](#data-models)
- [Protocols & Communication](#protocols--communication)
- [How to Run](#how-to-run)

---

## Project Idea
The application scenario is **Industrial IoT** for the smart monitoring of a construction site. The system is designed to improve workers’ safety through real-time tracking, environmental monitoring, and automated alarm management.

---

## Involved Devices
The system involves multiple types of IoT devices. The project is designed to support **N devices for each type**, depending on the application scenario.

During the demo, a minimal configuration is emulated:
- **N Worker Smart Helmets**
- **N Environmental Monitoring Stations**
- **1 Safety Alarm System**

### Device Overview

| Name | Type | Description |
|------|------|-------------|
| **Worker Smart Helmet** | Sensor & Actuator | Associated with a worker, equipped with GPS for tracking, battery level sensor, and multicolor LED. |
| **Environmental Monitoring Station** | Sensor | Equipped with GPS, fine dust sensor, noise level sensor, and dangerous gas sensor. |
| **Safety Alarm System** | Actuator | Remotely controllable via MQTT, equipped with an acoustic siren (ON/OFF) and a display for dangerous zone IDs. |

---

## High-Level Architecture
The system follows an IoT hub-and-spoke architecture with an MQTT broker facilitating communication between simulators, the logic manager, and monitoring interfaces.



---

## System Features

### Real-Time Worker Tracking with Geofencing
- The **Data Collector** continuously collects GPS data from all Worker Smart Helmets, enabling real-time tracking of each worker.
- The construction site is modeled as a **grid of sectors**, each identified by a unique ID.
- If a worker enters a sector marked as **dangerous**, the system detects the violation.
- Under normal conditions, the helmet LED is **green**. Detection of a safety violation triggers the **Siren**.

### Helmet Battery Management
- The system monitors battery levels in real-time.
- **Battery ≥ 10%** → Green LED (Work Mode)
- **Battery < 10%** → Yellow LED (Charging Required)
- Workers must stop and recharge to 100% when the battery drops below the 10% threshold.

### Environmental Monitoring
- **Environmental Monitoring Stations** measure fine dust, noise, and gas presence.
- Each station has a **coverage radius of 10 meters**.
- Exceeding safety thresholds marks all sectors within the 10m radius as **dangerous**.
- The **Safety Alarm System** display updates in real-time with the IDs of dangerous zones.

### Dynamic Station Positioning
- Stations are mobile and can be repositioned.
- The system tracks GPS positions of stations and dynamically recalculates affected grid sectors and danger zones in real-time.

---

## Data Models

### 1. Telemetry Messages (JSON)
**Helmet Telemetry**
```json
{
  "id": "001",
  "latitude": 45.1602, "longitude": 10.7874,
  "battery": 85, "led": 0, "timestamp": 1736698123.45
}
```

### 2. Command Messages (JSON)
**Command (Manager -> Actuator)**
```json
{
  "command": "turn_siren_on",
  "timestamp": 1736698126.88
}
```

---

## Protocols & Communication

| Topic Mapping | Publisher | Subscriber |
|---------------|-----------|------------|
| `helmet/[id]/telemetry` | Helmet | Manager, Dashboard |
| `station/[id]/telemetry` | Station | Manager, Dashboard |
| `manager/helmet/[id]/command` | Manager | Helmet, Dashboard |
| `manager/alarm/[id]/command` | Manager | Alarm, Dashboard |

---

## How to Run

1. **Install Dependencies**: `pip install -r requirements.txt`
2. **Configure Environment**: Copy `.env.example` to `.env` and set broker details.
3. **Run Scenario**: `python3 run_scenario.py`
4. **View Dashboard**: `python3 src/dashboard.py`
5. **Web Interface**: [http://localhost:5001](http://localhost:5001)

---
Project developed by **Saajan Saini**
