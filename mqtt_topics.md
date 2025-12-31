# MQTT Topics Summary

Questo documento riassume la struttura dei topic MQTT, chi pubblica e chi sottoscrive, con esempi di payload.

## Panoramica Architettura

- **Manager**: Colleziona dati e invia comandi.
- **Helmet**: Dispositivo IoT indossabile (Sensori + Attuatori).
- **Station**: Stazione di monitoraggio ambientale (Sensori).
- **Alarm**: Sistema di allarme (Sirena).

---

## 1. Helmet (Casco)

### Pubblica (Telemetry)
Il casco invia periodicamente i dati dei sensori.
- **Topic**: `[BASIC_TOPIC]/helmet/[helmet_id]`
- **Chi Sottoscrive**: Manager
- **Payload Esempio**:
```json
{
  "id": "helmet_001",
  "battery": 85,
  "led": 0,
  "latitude": 45.123,
  "longitude": 9.456,
  "timestamp": 1234567890
}
```

### Sottoscrive (Command)
Il casco riceve comandi per controllare i suoi attuatori (es. LED).
- **Topic**: `[BASIC_TOPIC]/manager/helmet/[helmet_id]/command`
- **Chi Pubblica**: Manager
- **Payload Esempio**:
```json
{
  "command": "set_led",
  "led": 1,
  "timestamp": 1700000000
}
```

---

## 2. Station (Stazione Ambientale)

### Pubblica (Telemetry)
La stazione invia dati ambientali.
- **Topic**: `[BASIC_TOPIC]/station/[station_id]`
- **Chi Sottoscrive**: Manager
- **Payload Esempio**:
```json
{
  "id": "station_001",
  "dust_level": 12,
  "noise_level": 45,
  "gas_level": 2,
  "latitude": 45.123,
  "longitude": 9.456
}
```

### Pubblica (Info)
La stazione invia informazioni statiche all'avvio.
- **Topic**: `[BASIC_TOPIC]/station/[station_id]/info`
- **Chi Sottoscrive**: (Opzionale/Dashboard)
- **Payload Esempio**:
```json
{
  "id": "station_001",
  "type": "environmental_station",
  "position": {"lat": 45.123, "lon": 9.456}
}
```

---

## 3. Alarm (Sirena)

### Sottoscrive (Command)
L'allarme riceve comandi di attivazione/disattivazione.
- **Topic**: `[BASIC_TOPIC]/manager/alarm/[alarm_id]/command` (o wildcard per tutti gli allarmi)
- **Chi Pubblica**: Manager
- **Payload Esempio (Attivazione)**:
```json
{
  "command": "turn_siren_on",
  "timestamp": 1700000000
}
```
- **Payload Esempio (Disattivazione)**:
```json
{
  "command": "turn_siren_off",
  "timestamp": 1700000000
}
```

---

## 4. Manager

### Flusso Logico Attuale
1.  **Ricezione Dati Helmet**: Aggiorna lo stato del casco. Controlla la batteria -> Se bassa, invia comando LED ON.
2.  **Ricezione Dati Station**: Aggiorna lo stato della stazione.
    - **Trigger Allarme**: Ad ogni aggiornamento della stazione, c'è una probabilità casuale (30%) di inviare un comando all'allarme.
        - 15% Probabilità: Invia `turn_siren_on`
        - 15% Probabilità: Invia `turn_siren_off`

---

### Legenda Variabili
- `[BASIC_TOPIC]`: Base topic configurato (es. `saajan/construction_site`)
- `[id]`: Identificativo univoco del dispositivo (es. `helmet_001`, `station_01`)
