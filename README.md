# Construction Site Monitoring System

Project for the course **"Intelligent Internet of Things"**, part of the Bachelor's Degree in **Computer Engineering** at the **Mantova campus of UNIMORE**, during the third year of study.

---

## Project Idea

The application scenario is **Industrial IoT** for the **smart monitoring of a construction site**.  
The system is designed to improve workers’ safety through real-time tracking, environmental monitoring, and automated alarm management.

---

## Involved Devices

The system involves multiple types of IoT devices.  
The project is designed to support **N devices for each type**, depending on the application scenario.

During the demo, a minimal configuration can be emulated to demonstrate the correct functioning of the system:
- **N Worker Smart Helmets**
- **N Environmental Monitoring Stations**
- **1 Safety Alarm System**

### Device Overview

| Name | Type | Description |
|----|----|----|
| **Worker Smart Helmet** | Sensor & Actuator | Smart helmet associated with a single worker, equipped with:<br>- GPS for worker position tracking<br>- Battery level sensor<br>- Multicolor LED |
| **Environmental Monitoring Station** | Sensor | Multiple environmental monitoring stations equipped with:<br>- Fine dust sensor<br>- Noise level sensor<br>- Dangerous gas sensor<br>- GPS for positioning |
| **Safety Alarm System** | Actuator | Remotely controllable alarm system equipped with:<br>- Acoustic siren (ON/OFF)<br>- Display showing the IDs of dangerous zones |

---

## Real-Time Worker Tracking with Geofencing

- The **Data Collector** continuously collects GPS data from all **Worker Smart Helmets**, enabling real-time tracking of each worker inside the construction site.
- The construction site is modeled as a **grid of sectors**, each identified by a unique ID.
- The system maintains an updated map of sectors classified as **safe** or **dangerous**.
- For each position update:
  - the sector in which the worker is located is determined;
  - the system checks whether the sector is marked as dangerous.
- Under normal conditions, the helmet LED is **green**.
- If a worker enters a dangerous sector, the system automatically detects the safety violation.

---

## Helmet Battery Management and Safety Notifications

- The **Data Collector** continuously monitors the battery level of each **Worker Smart Helmet**.
- Battery behavior:
  - Battery ≥ 10% → **Green LED**
  - Battery < 10% → **Yellow LED**
- When the battery level drops below 10%, the system reports a critical condition.
- In this case, the worker must immediately stop working and recharge the helmet to 100% before resuming activity.
- This functionality ensures that safety devices are always operational.

---

## Environmental Monitoring and Automatic Classification of Dangerous Sectors

- The **Environmental Monitoring Stations** continuously measure:
  - fine dust levels;
  - noise levels;
  - presence of dangerous gases.
- Each station is equipped with GPS and has an approximate **coverage radius of 10 meters**.
- The **Data Collector** compares the measured values with predefined safety thresholds.
- If one or more thresholds are exceeded:
  - all grid sectors that fall (even partially) within the 10-meter radius of the station are automatically marked as **dangerous**;
  - dangerous sectors are identified through their unique IDs.
- The **Safety Alarm System** is automatically activated:
  - the display shows the IDs of the sectors to avoid;
  - if a worker enters one of these dangerous sectors, the acoustic siren is activated.

---

## Dynamic Management of Environmental Station Positioning

- Environmental monitoring stations are **mobile** and can be freely repositioned within the construction site.
- The **Data Collector**:
  - tracks the GPS position of each station;
  - dynamically updates the association between stations, coverage radius, and grid sectors;
  - automatically recalculates which sectors are affected by each station’s measurements.
- This approach enables a **dynamic and continuously updated environmental map**, adapting in real time to operational changes within the construction site.

---

## Project Structure

*(To be defined)*

---

Project developed by **Saajan Saini**
