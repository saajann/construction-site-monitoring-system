
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

def visualize_sectors():
    # Paths
    root = Path(__file__).resolve().parent # src directory
    csv_path = root / "data" / "sectors.csv"
    output_path = root / "data" / "sectors_map.html"

    if not csv_path.exists():
        print(f"❌ Error: {csv_path} not found.")
        return

    # Read Data
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} sectors.")

    fig = go.Figure()

    # Calculate center
    center_lat = 0
    center_lon = 0
    count = 0

    import json

    # Draw each sector as a CLOSED polygon
    for _, row in df.iterrows():
        sector_id = row['id']
        try:
            coords = json.loads(row['vertices_json'])
        except Exception as e:
            print(f"⚠️ Error parsing geometry for {sector_id}: {e}")
            continue
            
        if not coords:
            continue

        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        
        # Close the loop if not closed
        if lats[0] != lats[-1] or lons[0] != lons[-1]:
            lats.append(lats[0])
            lons.append(lons[0])
            
        center_lat += sum(lats) / len(lats)
        center_lon += sum(lons) / len(lons)
        count += 1

        # Add Polygon Trace
        fig.add_trace(go.Scattermapbox(
            mode="lines",
            lon=lons,
            lat=lats,
            marker={'size': 5},
            name=sector_id,
            line=dict(width=1, color='blue'),
            hoverinfo='text',
            text=f"Sector: {sector_id}"
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
        title="Construction Site Grid Sectors"
    )

    # Save
    fig.write_html(str(output_path))
    print(f"✅ Visualization saved to: {output_path}")
    
    # Try to open automatically (optional, might not work in headless)
    # import webbrowser
    # webbrowser.open(f'file://{output_path}')

if __name__ == "__main__":
    visualize_sectors()
