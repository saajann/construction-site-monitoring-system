
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

    # Center of the map
    center_lat = df['p1_lat'].mean()
    center_lon = df['p1_lon'].mean()

    # Draw each sector as a CLOSED polygon
    for _, row in df.iterrows():
        # Coordinates for the rectangle (closing the loop by repeating the first point)
        lats = [row['p1_lat'], row['p2_lat'], row['p3_lat'], row['p4_lat'], row['p1_lat']]
        lons = [row['p1_lon'], row['p2_lon'], row['p3_lon'], row['p4_lon'], row['p1_lon']]
        
        sector_id = row['id']

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
        
        # Add center label (invisible point just for text?) 
        # Optional: Adds clutter if too many sectors.
        # fig.add_trace(go.Scattermapbox(
        #     mode="text",
        #     lon=[sum(lons[:-1])/4],
        #     lat=[sum(lats[:-1])/4],
        #     text=[sector_id],
        #     textposition="middle center",
        #     showlegend=False
        # ))

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
