import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import functions as fn # This is the functions.py file.
import time

# Page configuration
st.set_page_config(
    page_title="Reefer Monitoring",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 10px;
        border-radius: 5px;
    }
    div[data-testid="metric-container"] label {
        color: #31333F !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #31333F !important;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 10px;
    }
    .stAlert {
        margin-top: 10px;
    }
    .org-info {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 20px;
    }
    .org-info p {
        margin: 5px 0;
        color: #31333F;
    }
    .org-info strong {
        color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("Refeer Overview")
st.markdown("Monitor temperatures and door events in real-time, analyze historical events.")

# Sidebar configuration
# Get organization details
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_org_details():
    return fn.get_org_details()

org_id, org_name = load_org_details()

# Display organization info at the top of sidebar
if org_id and org_name:
    st.sidebar.markdown(f"""
    <div class="org-info">
        <p><strong>Organization</strong></p>
        <p><strong>Name:</strong> {org_name}</p>
        <p><strong>ID:</strong> {org_id}</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.warning("⚠️ Unable to load organization details")

st.sidebar.header("⚙️ Configuration")

# Load vehicles data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_vehicles():
    return fn.get_vehicles()

with st.spinner("Loading vehicles..."):
    vehicles_df = load_vehicles()

if vehicles_df.empty:
    st.error("No vehicles found.")
    st.stop()

# Build a list of unique vehicles (by id), keeping a representative row (first occurrence)
unique_vehicles = (
    vehicles_df
    .sort_values("id")
    .drop_duplicates(subset=["id"])
    .reset_index(drop=True)
)

# Vehicle selector: show only vehicle name
vehicle_names = unique_vehicles["name"].fillna("Unnamed Vehicle").tolist()

selected_vehicle_idx = st.sidebar.selectbox(
    "Select Vehicle",
    range(len(vehicle_names)),
    format_func=lambda x: vehicle_names[x]
)

selected_vehicle_row = unique_vehicles.iloc[selected_vehicle_idx]
vehicle_id = selected_vehicle_row["id"]

# All sensors for the selected vehicle
vehicle_sensors = vehicles_df[vehicles_df["id"] == vehicle_id].copy()

# Choose the temperature sensor row to use for temperature history
temp_sensor_row = vehicle_sensors[vehicle_sensors["sensorType"] == "temperature"]
if temp_sensor_row.empty:
    st.sidebar.error("Selected vehicle has no temperature sensor.")
    st.stop()

temp_sensor_row = temp_sensor_row.iloc[0]
temp_sensor_id = temp_sensor_row["sensorId"]

# Get door sensor for the same vehicle
door_sensor_row = vehicle_sensors[vehicle_sensors["sensorType"] == "door"]
door_sensor_id = door_sensor_row.iloc[0]["sensorId"] if not door_sensor_row.empty else None

# Display sensors for selected vehicle under the vehicle selector
st.sidebar.markdown("**Sensors on selected vehicle:**")

if not vehicle_sensors.empty:
    sensor_display_df = vehicle_sensors[["sensorType", "sensorPosition", "sensorName"]].copy()
    sensor_display_df = sensor_display_df.fillna("-")
    st.sidebar.dataframe(sensor_display_df, hide_index=True, use_container_width=True)
else:
    st.sidebar.write("_No sensors configured for this vehicle._")

# Date range selector
st.sidebar.subheader("Time Range")

time_option = st.sidebar.radio(
    "Select time range:",
    ["Now (Last 24 hours)", "Last 7 days", "Last 30 days", "Custom Range"]
)

if time_option == "Now (Last 24 hours)":
    hours_back = 24
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours_back)
elif time_option == "Last 7 days":
    hours_back = 24 * 7
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours_back)
elif time_option == "Last 30 days":
    hours_back = 24 * 30
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours_back)
else:  # Custom Range
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        start_time_input = st.time_input("Start Time", datetime.now().time())
    with col2:
        end_date = st.date_input("End Date", datetime.now())
        end_time_input = st.time_input("End Time", datetime.now().time())
    
    start_time = datetime.combine(start_date, start_time_input)
    end_time = datetime.combine(end_date, end_time_input)

start_ms = fn.datetime_to_ms(start_time)
end_ms = fn.datetime_to_ms(end_time)

# Temperature thresholds
st.sidebar.subheader("Temperature Thresholds")
temp_unit = st.sidebar.radio("Temperature Unit", ["Celsius", "Fahrenheit"])

if temp_unit == "Celsius":
    default_min = 1
    default_max = 6
    temp_symbol = "°C"
else:
    # Approximate Fahrenheit equivalents
    default_min = 33
    default_max = 43
    temp_symbol = "°F"

min_temp = st.sidebar.number_input(
    f"Minimum Temperature ({temp_symbol})",
    value=default_min,
    step=1
)
max_temp = st.sidebar.number_input(
    f"Maximum Temperature ({temp_symbol})",
    value=default_max,
    step=1
)

# Door event display option
st.sidebar.subheader("Door Events")
door_display = st.sidebar.radio(
    "Display door events as:",
    ["Vertical Lines", "Markers"]
)

# Refresh button
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ===== LIVE STATUS SECTION (updates every 5 seconds) =====
st.markdown("### 🟢 Live Status ")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Vehicle", selected_vehicle_row["name"])

with col2:
    temp_placeholder = st.empty()

with col3:
    door_placeholder = st.empty()

# Countdown placeholder (below the metrics row)
countdown_placeholder = st.empty()

# Function to update live metrics
def update_live_metrics():
    # Fetch current temperature
    temp_data = fn.get_current_temperature(temp_sensor_id)
    if temp_data and temp_data.get("ambientTemperature") is not None:
        temp_celsius = temp_data["ambientTemperature"] / 1000.0
        if temp_unit == "Fahrenheit":
            current_temp = fn.celsius_to_fahrenheit(temp_celsius)
        else:
            current_temp = temp_celsius
        temp_placeholder.metric("Current Temperature", f"{current_temp:.1f}{temp_symbol}")
    else:
        temp_placeholder.metric("Current Temperature", "N/A")
    
    # Fetch current door status
    if door_sensor_id:
        door_data = fn.get_current_door_status(door_sensor_id)
        if door_data and "doorClosed" in door_data:
            door_status = "🔒 Closed" if door_data["doorClosed"] else "🔓 Open"
            door_placeholder.metric("Door Status", door_status)
        else:
            door_placeholder.metric("Door Status", "N/A")
    else:
        door_placeholder.metric("Door Status", "No Sensor")

# Initial update
update_live_metrics()
countdown_placeholder.markdown("Next update in **5s**")

# ===== STATIC CONTENT: Historic data & plot (rendered once) =====
st.markdown("---")

# Fetch data
with st.spinner("Loading temperature data..."):
    temp_df = fn.get_historic_temperature(temp_sensor_id, start_ms, end_ms, stepMs=60000)

if door_sensor_id:
    with st.spinner("Loading door events..."):
        door_df = fn.get_historic_door(door_sensor_id, start_ms, end_ms, stepMs=5000)
else:
    door_df = pd.DataFrame()

# Process temperature data
if not temp_df.empty:
    temp_df["datetime"] = temp_df["timeMs"].apply(fn.ms_to_datetime)

    # Convert from millicelsius to celsius
    temp_df["celsius"] = temp_df["ambientTemperature"] / 1000.0

    # Convert temperature if needed
    if temp_unit == "Fahrenheit":
        temp_df["temperature"] = temp_df["celsius"].apply(fn.celsius_to_fahrenheit)
    else:
        temp_df["temperature"] = temp_df["celsius"]

    # Remove null values for cleaner visualization
    temp_df = temp_df[temp_df["temperature"].notna()]

# Process door data
door_events = []
if not door_df.empty:
    door_df["datetime"] = door_df["timeMs"].apply(fn.ms_to_datetime)

    # Detect door open events (when doorClosed changes from True to False)
    door_df["door_opened"] = (door_df["doorClosed"] == False) & (door_df["doorClosed"].shift(1) == True)
    door_events = door_df[door_df["door_opened"]]["datetime"].tolist()

# Create the plot
if not temp_df.empty:
    fig = go.Figure()

    # Add temperature line
    fig.add_trace(go.Scatter(
        x=temp_df["datetime"],
        y=temp_df["temperature"],
        mode="lines",
        name="Temperature",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="<b>Time:</b> %{x}<br><b>Temperature:</b> %{y:.1f}" + temp_symbol + "<extra></extra>"
    ))

    # Add min threshold line
    fig.add_trace(go.Scatter(
        x=[temp_df["datetime"].min(), temp_df["datetime"].max()],
        y=[min_temp, min_temp],
        mode="lines",
        name=f"Min Threshold ({min_temp}{temp_symbol})",
        line=dict(color="blue", width=2, dash="dash"),
        hovertemplate=f"<b>Min Threshold:</b> {min_temp}{temp_symbol}<extra></extra>"
    ))

    # Add max threshold line
    fig.add_trace(go.Scatter(
        x=[temp_df["datetime"].min(), temp_df["datetime"].max()],
        y=[max_temp, max_temp],
        mode="lines",
        name=f"Max Threshold ({max_temp}{temp_symbol})",
        line=dict(color="red", width=2, dash="dash"),
        hovertemplate=f"<b>Max Threshold:</b> {max_temp}{temp_symbol}<extra></extra>"
    ))

    # Add door events
    if door_events:
        if door_display == "Vertical Lines":
            for event_time in door_events:
                fig.add_shape(
                    type="line",
                    x0=event_time,
                    x1=event_time,
                    y0=0,
                    y1=1,
                    yref="paper",
                    line=dict(color="orange", width=2, dash="dot")
                )

            # Dummy trace for legend
            fig.add_trace(go.Scatter(
                x=[door_events[0]],
                y=[None],
                mode="lines",
                name="Door Opened",
                line=dict(color="orange", width=2, dash="dot"),
                showlegend=True
            ))
        else:  # Markers
            event_temps = []
            for event_time in door_events:
                time_diff = abs(temp_df["datetime"] - event_time)
                closest_idx = time_diff.argmin()
                closest_temp = temp_df.iloc[closest_idx]
                event_temps.append(closest_temp["temperature"])

            fig.add_trace(go.Scatter(
                x=door_events,
                y=event_temps,
                mode="markers",
                name="Door Opened",
                marker=dict(
                    color="orange",
                    size=10,
                    symbol="diamond",
                    line=dict(color="darkorange", width=2)
                ),
                hovertemplate="<b>Door Opened</b><br><b>Time:</b> %{x}<br><b>Temperature:</b> %{y:.1f}" + temp_symbol + "<extra></extra>"
            ))

    # Update layout
    fig.update_layout(
        title=f"Temperature Monitoring - {selected_vehicle_row['name']}",
        xaxis_title="Time",
        yaxis_title=f"Temperature ({temp_symbol})",
        hovermode="x unified",
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor="white",
        xaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            showline=True,
            linecolor="black"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            showline=True,
            linecolor="black"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Statistics
    st.subheader("📊 Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_temp = temp_df["temperature"].mean()
        st.metric("Average Temperature", f"{avg_temp:.1f}{temp_symbol}")

    with col2:
        min_temp_val = temp_df["temperature"].min()
        st.metric("Minimum Temperature", f"{min_temp_val:.1f}{temp_symbol}")

    with col3:
        max_temp_val = temp_df["temperature"].max()
        st.metric("Maximum Temperature", f"{max_temp_val:.1f}{temp_symbol}")

    with col4:
        st.metric("Door Open Events", len(door_events))

    # Threshold violations
    violations = temp_df[
        (temp_df["temperature"] < min_temp) |
        (temp_df["temperature"] > max_temp)
    ]

    if not violations.empty:
        st.warning(f"⚠️ {len(violations)} temperature readings outside threshold range!")

        with st.expander("View Violations"):
            violations_display = violations[["datetime", "temperature"]].copy()
            violations_display["temperature"] = violations_display["temperature"].apply(
                lambda x: f"{x:.1f}{temp_symbol}"
            )
            st.dataframe(violations_display, use_container_width=True)
    else:
        st.success("✅ All temperature readings within threshold range!")

    # Door events table
    if door_events:
        with st.expander(f"View Door Events ({len(door_events)} events)"):
            door_events_df = pd.DataFrame({
                "Event Time": door_events,
                "Event": ["Door Opened"] * len(door_events)
            })
            st.dataframe(door_events_df, use_container_width=True)

else:
    st.warning("No temperature data available for the selected time range.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Temperature & Door Monitoring Dashboard | "
    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>",
    unsafe_allow_html=True
)

# ===== CONTINUOUS UPDATE LOOP WITH COUNTDOWN =====
cycles = 24  # 24 cycles * 5 seconds = 120 seconds (2 minutes)

for _ in range(cycles):
    for remaining in range(5, 0, -1):
        countdown_placeholder.markdown(f"Next update in **{remaining}s**")
        time.sleep(1)
    update_live_metrics()

# After the loop ends
countdown_placeholder.markdown("Live updates stopped. Click **🔄 Refresh Data** to resume.")