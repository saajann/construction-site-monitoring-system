# Study Guide: Construction Site Monitoring System

Questo documento è una guida completa per la presentazione orale del progetto. Copre l'architettura, le scelte tecnologiche e le possibili domande d'esame.

---

## 1. Architettura di Sistema (High-Level)

Il sistema segue un'architettura **IoT End-to-End** strutturata su tre livelli principali:

1.  **Edge Layer (Dispositivi)**: Helmets e Stations che generano dati. Sono i "Producer".
2.  **Network/Broker Layer**: Il broker MQTT (Mosquitto) che permette il disaccoppiamento spaziale e temporale tra chi produce dati e chi li consuma.
3.  **Cloud/Processing Layer**:
    *   **Manager (Data Collector)**: Il "cervello" che processa la logica di business.
    *   **Dashboard & Web Server**: Interfacce di monitoraggio.

---

## 2. Scelte Tecnologiche Chiave

### Perché MQTT?
*   **Lightweight**: Ideale per dispositivi con risorse limitate (Edge).
*   **Pub/Sub**: Permette a un sensore di inviare dati senza sapere chi li leggerà (Manager, Dashboard, etc.).
*   **Intermettent Connectivity**: MQTT gestisce i cali di connessione meglio di HTTP grazie a sessioni persistenti e messaggi di "Keep Alive".

### SenML+JSON (The Standard)
Abbiamo scelto lo standard **SenML (Sensor Measurement Lists)** per la telemetria.
*   **Perché?**: Evita di creare formati JSON custom. SenML è uno standard IETF che include nome del sensore (`n`), unità di misura (`u`), valore (`v`) e timestamp (`t`).
*   **Nomi Gerarchici**: Usiamo nomi come `helmet.gps.lat` per rendere il dato auto-esplicativo (Self-Describing Data).

### Discovery via Retained Info
Ogni device pubblica un messaggio sul topic `/info` all'avvio:
*   **QoS 2**: Garantisce che il metadato (ID, tipo, capacità) arrivi esattamente una volta.
*   **Retain Flag**: Fondamentale. Se la Dashboard si connette *dopo* che un elmetto è già online, il Broker le invierà immediatamente l'ultimo messaggio `/info` memorizzato. Senza questo, la Dashboard "vedrebbe" l'elmetto solo al prossimo riavvio del device.

---

## 3. Analisi dei Componenti (Codebase)

*   **`src/model/`**: Contiene la logica ad oggetti (OOP). Qui definiamo le classi `WorkerSmartHelmet`, `EnvironmentalStation`, etc. È qui che avviene la conversione in SenML.
*   **`src/process/`**:
    *   `helmet.py`/`station.py`: Simulano il comportamento fisico e la connessione MQTT.
    *   `manager.py`: La logica centrale. Riceve SenML, aggiorna il file `map.csv` e decide se far suonare l'allarme.
*   **`src/web_server.py`**: Bridge tra i dati persistiti (CSV) e l'interfaccia browser via **REST API**.
*   **`src/dashboard.py`**: Un monitor "trasparente" che usa il wildcard `#` per mostrare tutto il traffico MQTT in tempo reale.

---

## 4. Domande "Killer" del Professore (Q&A)

**D: Come hai gestito l'affidabilità della consegna dei messaggi?**
**R**: Usando i livelli di QoS di MQTT. QoS 1 per la telemetria (vogliamo che arrivi, anche se duplicata). **QoS 2** per le info critiche di discovery e per tutti i **comandi** (sirena, LED).

### Tabella Riassuntiva QoS e Topic

| Topic Pattern | Scopo | QoS Pub | QoS Sub | Garanzia di Consegna |
| :--- | :--- | :--- | :--- | :--- |
| `+/+/info` | Discovery (Metadati) | **2** (Retained) | **2** (Manager) | Exactly Once |
| `+/+/telemetry` | Telemetria (SenML) | **1** | **1** (Manager) | At Least Once |
| `manager/+/+/command`| Comandi (Attuazione) | **2** | **2** (Actuators)| Exactly Once |
| `#` | Dashboard Universale | - | **1** | At Least Once |

**Perché queste differenze?**
*   **QoS 2**: Usato per dati **critici** e statici (info) o azioni che devono essere eseguite esattamente una volta (comandi). Non vogliamo doppioni o perdite.
*   **QoS 1**: Usato per dati **frequenti** (telemetria). Se un dato di batteria arriva due volte non è un problema, l'importante è che non vada perso.
*   **Dashboard (QoS 1)**: La dashboard è un osservatore passivo. Il QoS 1 è un buon compromesso tra prestazioni e affidabilità.

**D: Cosa succede se il Manager va offline?**
**R**: I device continuano a inviare dati al Broker. Grazie al sistema Pub/Sub, appena il Manager torna online, ricomincerà a processare i messaggi. Tuttavia, i dati in tempo reale andrebbero persi se non usassimo code persistenti sul broker.

**D: SenML è pesante per un sensore?**
**R**: JSON è un po' verboso, ma SenML può essere usato anche in formato **CBOR** (binario) per risparmiare banda. Nel nostro progetto usiamo JSON per semplicità e leggibilità durante il monitoraggio.

**D: Perché usi i CSV invece di un database (es. InfluxDB)?**
**R**: Per un prototipo di monitoraggio da cantiere, il CSV offre persistenza immediata e facilità di debug. In una produzione reale, useremmo un **Time-Series Database (TSDB)** come InfluxDB per gestire migliaia di sensori in modo efficiente.

**D: Come hai risolto il problema di far vedere elmetti già connessi a una Dashboard appena aperta?**
**R**: Usando il **Retain Flag** sul topic `/info`. Il broker funge da memoria per l'anagrafica dei dispositivi.

---

## 5. Tips per la Presentazione
1.  **Mostra lo Schema**: Parte dal diagramma di architettura, è la base di tutto.
2.  **Esegui `run_scenario.py`**: Fai vedere i log che scorrono. Mostra come il Manager rileva un pericolo e attiva la sirena.
3.  **Enfatizza lo Standard**: Dire "uso SenML" invece di "uso un mio JSON" fa salire il voto perché dimostra conoscenza degli standard IoT reali.
