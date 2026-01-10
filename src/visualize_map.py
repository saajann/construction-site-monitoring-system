
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

import time

def visualize_map():
    # Paths
    root = Path(__file__).resolve().parent # src directory
    map_csv_path = root / "data" / "map.csv"
    helmets_csv_path = root / "data" / "helmets.csv"
    output_path = root / "data" / "map.html"

    if not map_csv_path.exists():
        print(f"❌ Error: {map_csv_path} not found.")
        return

    print("🔄 Starting real-time visualization loop (updates every 5s)...")
    print("👉 Open the map file to view: " + str(output_path))

    while True:
        try:
            # 1. Read Grid Data
            if map_csv_path.exists():
                df_grid = pd.read_csv(map_csv_path)
            else:
                print(f"⚠️ {map_csv_path} not found.")
                time.sleep(5)
                continue

            # 2. Read Helmet Data
            df_helmets = pd.DataFrame()
            if helmets_csv_path.exists():
                try:
                    df_helmets = pd.read_csv(helmets_csv_path)
                except Exception as e:
                    print(f"⚠️ Error reading helmets.csv: {e}")

            fig = go.Figure()

            # Center calc
            center_lat = 0
            center_lon = 0
            count = 0

            import json

            # Draw Sectors
            for _, row in df_grid.iterrows():
                sector_id = row['id']
                try:
                    coords = json.loads(row['vertices_json'])
                except: continue
                if not coords: continue
                
                status = int(row.get('status', 0))
                is_dangerous = (status == 1)

                lats = [c[0] for c in coords]
                lons = [c[1] for c in coords]
                if lats[0] != lats[-1] or lons[0] != lons[-1]:
                    lats.append(lats[0])
                    lons.append(lons[0])
                
                center_lat += sum(lats) / len(lats)
                center_lon += sum(lons) / len(lons)
                count += 1

                color = 'red' if is_dangerous else 'blue'
                fill_color = 'rgba(255,0,0,0.3)' if is_dangerous else 'rgba(0,0,255,0.05)'

                fig.add_trace(go.Scattermapbox(
                    mode="lines",
                    lon=lons, lat=lats,
                    fill="toself", fillcolor=fill_color,
                    line=dict(width=1, color=color),
                    name=f"Sector {sector_id}",
                    hoverinfo='text',
                    text=f"Sector: {sector_id} | Status: {'DANGER' if is_dangerous else 'Safe'}"
                ))

            # Draw Helmets
            if not df_helmets.empty:
                for _, row in df_helmets.iterrows():
                    h_id = row['id']
                    
                    # Robust Lat/Lon extraction
                    try:
                        h_lat = float(row['latitude'])
                        h_lon = float(row['longitude'])
                        if pd.isna(h_lat) or pd.isna(h_lon):
                            continue
                    except:
                        continue

                    h_bat = row.get('battery', 0)
                    if pd.isna(h_bat): h_bat = 0
                    
                    # Robust danger check
                    h_danger_raw = row.get('is_dangerous', 0)
                    h_danger = False
                    try:
                        if not pd.isna(h_danger_raw):
                            h_danger = int(float(h_danger_raw)) == 1
                    except:
                        pass
                    
                    marker_color = 'red' if h_danger else 'lime'
                    
                    fig.add_trace(go.Scattermapbox(
                        mode="markers+text",
                        lon=[h_lon], lat=[h_lat],
                        marker=dict(size=14, color=marker_color, opacity=1.0),
                        text=[f"👷 {h_id}"],
                        textposition="top center",
                        name=f"Helmet {h_id}",
                        hoverinfo='text',
                        textfont=dict(size=14, color='white'),
                        customdata=[[h_bat, "DANGER" if h_danger else "Safe"]],
                        hovertemplate="<b>Helmet %{text}</b><br>Pos: (%{lat:.5f}, %{lon:.5f})<br>Bat: %{customdata[0]}%<br>Status: %{customdata[1]}<extra></extra>"
                    ))

            if count > 0:
                center_lat /= count
                center_lon /= count

            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox=dict(center=dict(lat=center_lat, lon=center_lon), zoom=18),
                margin={"r":0,"t":0,"l":0,"b":0},
                title=f"Site Live Map (Updated: {time.strftime('%H:%M:%S')})",
                showlegend=False
            )

            fig.write_html(str(output_path))
            print(f"✅ Map updated at {time.strftime('%H:%M:%S')}")
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n🛑 Visualization stopped.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    visualize_map()
