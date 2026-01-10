
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

import time

def visualize_sectors():
    # Paths
    root = Path(__file__).resolve().parent # src directory
    csv_path = root / "data" / "sectors.csv"
    display_csv_path = root / "data" / "display.csv"
    output_path = root / "data" / "sectors_map.html"

    if not csv_path.exists():
        print(f"❌ Error: {csv_path} not found.")
        return

    # Read Geometry Data (Static)
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} sectors geometry.")

    print("🔄 Starting real-time visualization loop (updates every 5s)...")
    print("👉 Open the map file to view: " + str(output_path))

    while True:
        try:
            # Read Dynamic Status
            dangerous_zones = set()
            if display_csv_path.exists():
                try:
                    df_status = pd.read_csv(display_csv_path)
                    if 'zone_id' in df_status.columns:
                        dangerous_zones = set(df_status['zone_id'])
                except Exception as e:
                    print(f"⚠️ Error reading display.csv: {e}")

            fig = go.Figure()

            # Calculate center (recalc each time or static? Static is fine if geometry doesn't change)
            center_lat = 0
            center_lon = 0
            count = 0

            import json

            # Draw each sector
            for _, row in df.iterrows():
                sector_id = row['id']
                try:
                    coords = json.loads(row['vertices_json'])
                except Exception as e:
                    continue
                    
                if not coords:
                    continue

                lats = [c[0] for c in coords]
                lons = [c[1] for c in coords]
                
                # Close loop
                if lats[0] != lats[-1] or lons[0] != lons[-1]:
                    lats.append(lats[0])
                    lons.append(lons[0])
                    
                center_lat += sum(lats) / len(lats)
                center_lon += sum(lons) / len(lons)
                count += 1

                # Determine Color
                is_dangerous = sector_id in dangerous_zones
                color = 'red' if is_dangerous else 'blue'
                opacity = 0.6 if is_dangerous else 0.1
                fill_color = 'red' if is_dangerous else 'rgba(0,0,255,0.05)'

                # Add Polygon Trace
                fig.add_trace(go.Scattermapbox(
                    mode="lines",
                    lon=lons,
                    lat=lats,
                    marker={'size': 5},
                    name=sector_id,
                    line=dict(width=2 if is_dangerous else 1, color=color),
                    fill="toself",
                    fillcolor=fill_color,
                    hoverinfo='text',
                    text=f"Sector: {sector_id} | Status: {'DANGER' if is_dangerous else 'Safe'}"
                ))

            if count > 0:
                center_lat /= count
                center_lon /= count

            # Update Layout
            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox=dict(
                    center=dict(lat=center_lat, lon=center_lon),
                    zoom=18
                ),
                margin={"r":0,"t":0,"l":0,"b":0},
                title=f"Construction Site Grid (Updated: {time.strftime('%H:%M:%S')})"
            )

            # Save
            fig.write_html(str(output_path))
            # print(f"✅ Map updated at {time.strftime('%H:%M:%S')}")
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n🛑 Visualization stopped.")
            break
        except Exception as e:
            print(f"❌ Error in loop: {e}")
            time.sleep(5)
    
    # Try to open automatically (optional, might not work in headless)
    # import webbrowser
    # webbrowser.open(f'file://{output_path}')

if __name__ == "__main__":
    visualize_sectors()
