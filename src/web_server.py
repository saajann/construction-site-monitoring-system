import os
import json
import pandas as pd
from flask import Flask, render_template, jsonify
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MONITORING_STATION_RANGE = int(os.getenv("MONITORING_STATION_RANGE", 50))

app = Flask(__name__)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

@app.route("/")
def index():
    """Serves the main dashboard page"""
    return render_template("index.html")

@app.route("/api/data")
def get_data():
    """API endpoint to get real-time site data"""
    map_csv = DATA_DIR / "map.csv"
    helmets_csv = DATA_DIR / "helmets.csv"
    
    data = {
        "sectors": [],
        "helmets": [],
        "stations": [],
        "station_range": MONITORING_STATION_RANGE
    }
    
    # Load sectors
    if map_csv.exists():
        try:
            df_grid = pd.read_csv(map_csv, dtype={'id': str})
            for _, row in df_grid.iterrows():
                data["sectors"].append({
                    "id": row["id"],
                    "vertices": json.loads(row["vertices_json"]),
                    "status": int(row.get("status", 0))
                })
        except Exception as e:
            print(f"Error reading map.csv: {e}")

    # Load helmets
    if helmets_csv.exists():
        try:
            df_helmets = pd.read_csv(helmets_csv, dtype={'id': str})
            for _, row in df_helmets.iterrows():
                # Use .get() but with a default and better type conversion
                lat = row.get("latitude")
                lon = row.get("longitude")
                if pd.isna(lat) or pd.isna(lon):
                    continue
                    
                data["helmets"].append({
                    "id": str(row["id"]),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "battery": int(row["battery"]) if not pd.isna(row.get("battery")) else 0,
                    "led": int(row["led"]) if not pd.isna(row.get("led")) else 0
                })
        except Exception as e:
            print(f"Error reading helmets.csv: {e}")
            
    # Load stations
    data["stations"] = []
    stations_csv = DATA_DIR / "stations.csv"
    if stations_csv.exists():
        try:
            df_stations = pd.read_csv(stations_csv, dtype={'id': str})
            for _, row in df_stations.iterrows():
                lat = row["latitude"]
                lon = row["longitude"]
                if pd.isna(lat) or pd.isna(lon):
                    continue
                data["stations"].append({
                    "id": row["id"],
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "dust": float(row.get("dust", 0)) if not pd.isna(row.get("dust")) else 0,
                    "noise": float(row.get("noise", 0)) if not pd.isna(row.get("noise")) else 0,
                    "gas": float(row.get("gas", 0)) if not pd.isna(row.get("gas")) else 0,
                    "is_dangerous": int(row.get("is_dangerous", 0)) == 1
                })
        except Exception as e:
            print(f"Error reading stations.csv: {e}")
            
    # Load alarm status
    alarm_csv = DATA_DIR / "alarm_status.csv"
    data["alarm_active"] = False
    if alarm_csv.exists():
        try:
            df_alarm = pd.read_csv(alarm_csv)
            if not df_alarm.empty:
                data["alarm_active"] = bool(df_alarm.iloc[0]["alarm_active"] == 1)
        except Exception as e:
            print(f"Error reading alarm_status.csv: {e}")
            
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
