# ============================================================================
# SAMSARA REEFER MONITORING DASHBOARD
# ============================================================================
# This Streamlit application provides a real-time and historical monitoring
# dashboard for refrigerated vehicles (reefers) using Samsara API data.
# 
# Key Features:
# - Real-time temperature and door status monitoring (updates every 5 seconds)
# - Historical temperature data visualization with interactive charts
# - Door open event tracking and visualization
# - Temperature threshold violation detection
# - Multi-vehicle support with sensor configuration display
# - Customizable time ranges and temperature units
# 
# UI Structure:
# - Sidebar: Organization info, vehicle selector, time range, thresholds
# - Main Content: Live metrics, temperature chart, statistics, violations
# ============================================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import functions as fn  # This is the functions.py file.
import time

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
# Configure Streamlit page settings including title, icon, layout, and sidebar

st.set_page_config(
    page_title="Reefer Monitoring",  # Browser tab title
    page_icon="🚚",  # Browser tab icon (truck emoji)
    layout="wide",  # Use full width of browser window
    initial_sidebar_state="expanded"  # Sidebar open by default
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
# Initialize session state for live update control

if 'stop_updates' not in st.session_state:
    st.session_state.stop_updates = False

# ============================================================================
# PAGE HEADER
# ============================================================================
# Display main title and subtitle for the dashboard

st.title("Reefer Overview")
st.markdown("Monitor temperatures and door events in real-time, analyze historical events.")

# ============================================================================
# SIDEBAR CONFIGURATION - ORGANIZATION DETAILS
# ============================================================================
# Fetch and display organization information at the top of the sidebar
# Uses caching to avoid repeated API calls (1 hour TTL)

@st.cache_data(ttl=3600)  # Cache for 1 hour to reduce API calls
def load_org_details():
    """
    Load organization details from Samsara API.
    Wrapper function for caching purposes.
    
    Returns:
        tuple: (org_id, org_name) from fn.get_org_details()
    """
    return fn.get_org_details()

# Fetch organization details
org_id, org_name = load_org_details()

# Display organization info at the top of sidebar
if org_id and org_name:
    st.sidebar.info(f"**Organization**\n\n**Name:** {org_name}\n\n**ID:** {org_id}")
else:
    # Show warning if organization details cannot be loaded
    st.sidebar.warning("⚠️ Unable to load organization details")

# ============================================================================
# SIDEBAR CONFIGURATION - VEHICLE SELECTION
# ============================================================================
# Load vehicles from API and provide dropdown selector for user to choose vehicle

st.sidebar.header("⚙️ Configuration")

@st.cache_data(ttl=300)  # Cache for 5 minutes to balance freshness and performance
def load_vehicles():
    """
    Load all vehicles and their sensors from Samsara API.
    Wrapper function for caching purposes.
    
    Returns:
        pandas.DataFrame: Vehicle and sensor data from fn.get_vehicles()
    """
    return fn.get_vehicles()

# Load vehicles with a loading spinner
with st.spinner("Loading vehicles..."):
    vehicles_df = load_vehicles()

# Stop execution if no vehicles are found
if vehicles_df.empty:
    st.error("No vehicles found.")
    st.stop()

# Build a list of unique vehicles (by id), keeping first occurrence of each vehicle
# This is necessary because vehicles_df has multiple rows per vehicle (one per sensor)
unique_vehicles = (
    vehicles_df
    .sort_values("id")  # Sort by vehicle ID for consistent ordering
    .drop_duplicates(subset=["id"])  # Keep only first row for each vehicle
    .reset_index(drop=True)  # Reset index for clean indexing
)

# Create list of vehicle names for the dropdown selector
vehicle_names = unique_vehicles["name"].fillna("Unnamed Vehicle").tolist()

# Vehicle selector dropdown - uses index but displays vehicle name
selected_vehicle_idx = st.sidebar.selectbox(
    "Select Vehicle",
    range(len(vehicle_names)),  # Use indices as values
    format_func=lambda x: vehicle_names[x]  # Display vehicle names
)

# Get the selected vehicle's data
selected_vehicle_row = unique_vehicles.iloc[selected_vehicle_idx]
vehicle_id = selected_vehicle_row["id"]

# ============================================================================
# SENSOR IDENTIFICATION
# ============================================================================
# Extract temperature and door sensor IDs for the selected vehicle
# Temperature sensor is required; door sensor is optional

# Get all sensors for the selected vehicle
vehicle_sensors = vehicles_df[vehicles_df["id"] == vehicle_id].copy()

# Find temperature sensor (required)
temp_sensor_row = vehicle_sensors[vehicle_sensors["sensorType"] == "temperature"]
if temp_sensor_row.empty:
    # Stop execution if no temperature sensor found
    st.sidebar.error("Selected vehicle has no temperature sensor.")
    st.stop()

# Extract temperature sensor ID
temp_sensor_row = temp_sensor_row.iloc[0]
temp_sensor_id = temp_sensor_row["sensorId"]

# Find door sensor (optional)
door_sensor_row = vehicle_sensors[vehicle_sensors["sensorType"] == "door"]
door_sensor_id = door_sensor_row.iloc[0]["sensorId"] if not door_sensor_row.empty else None

# ============================================================================
# SIDEBAR - SENSOR DISPLAY TABLE
# ============================================================================
# Display all sensors configured on the selected vehicle in a table format

st.sidebar.markdown("**Sensors on selected vehicle:**")

if not vehicle_sensors.empty:
    # Create display DataFrame with relevant sensor columns
    sensor_display_df = vehicle_sensors[["sensorType", "sensorPosition", "sensorName"]].copy()
    sensor_display_df = sensor_display_df.fillna("-")  # Replace None with dash
    # Display as interactive table
    st.sidebar.dataframe(sensor_display_df, hide_index=True, use_container_width=True)
else:
    # Show message if no sensors configured
    st.sidebar.write("_No sensors configured for this vehicle._")

# ============================================================================
# SIDEBAR - TIME RANGE CONFIGURATION
# ============================================================================
# Allow user to select time range for historical data
# Options: Last 24 hours, Last 7 days, Last 30 days, or Custom Range

st.sidebar.subheader("Time Range")

# Radio button selector for time range options
time_option = st.sidebar.radio(
    "Select time range:",
    ["Now (Last 24 hours)", "Last 7 days", "Last 30 days", "Custom Range"]
)

# Calculate start and end times based on selected option
if time_option == "Now (Last 24 hours)":
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
elif time_option == "Last 7 days":
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
elif time_option == "Last 30 days":
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)
else:  # Custom Range
    # Display date and time pickers in two columns
    col1, col2 = st.sidebar.columns(2)
    with col1:
        # Start date/time inputs
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        start_time_input = st.time_input("Start Time", datetime.now().time())
    with col2:
        # End date/time inputs
        end_date = st.date_input("End Date", datetime.now())
        end_time_input = st.time_input("End Time", datetime.now().time())
    
    # Combine date and time into datetime objects
    start_time = datetime.combine(start_date, start_time_input)
    end_time = datetime.combine(end_date, end_time_input)

# Convert datetime objects to milliseconds for API calls
start_ms = fn.datetime_to_ms(start_time)
end_ms = fn.datetime_to_ms(end_time)

# ============================================================================
# SIDEBAR - TEMPERATURE THRESHOLD CONFIGURATION
# ============================================================================
# Allow user to set minimum and maximum temperature thresholds
# Supports both Celsius and Fahrenheit units

st.sidebar.subheader("Temperature Thresholds")

# Temperature unit selector
temp_unit = st.sidebar.radio("Temperature Unit", ["Celsius", "Fahrenheit"])

# Set default threshold values based on selected unit
if temp_unit == "Celsius":
    default_min = 1  # 1°C
    default_max = 6  # 6°C
    temp_symbol = "°C"
else:
    # Approximate Fahrenheit equivalents
    default_min = 33  # ~1°C
    default_max = 43  # ~6°C
    temp_symbol = "°F"

# Number inputs for minimum and maximum thresholds
min_temp = st.sidebar.number_input(
    f"Minimum Temperature ({temp_symbol})",
    value=default_min,
    step=1  # Increment by 1 degree
)
max_temp = st.sidebar.number_input(
    f"Maximum Temperature ({temp_symbol})",
    value=default_max,
    step=1  # Increment by 1 degree
)

# ============================================================================
# SIDEBAR - DOOR EVENT DISPLAY OPTION
# ============================================================================
# Allow user to choose how door open events are displayed on the chart
# Options: Vertical lines across chart or markers on temperature line

st.sidebar.subheader("Door Events")
door_display = st.sidebar.radio(
    "Display door events as:",
    ["Vertical Lines", "Markers"]  # Two visualization options
)

# ============================================================================
# SIDEBAR - REFRESH BUTTON
# ============================================================================
# Provide button to clear cache and reload all data

if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()  # Clear all cached data
    st.session_state.stop_updates = False  # Reset stop flag
    st.rerun()  # Rerun the entire app

# ============================================================================
# LIVE STATUS SECTION
# ============================================================================
# Display real-time metrics that update every 5 seconds
# Shows: Vehicle name, current temperature, current door status

# Live status header with inline countdown
status_header = st.empty()
status_header.markdown("### 🟡 Connecting...")

# Create three columns for live metrics
col1, col2, col3 = st.columns(3)

# Column 1: Vehicle name (static)
with col1:
    st.metric("Vehicle", selected_vehicle_row["name"])

# Column 2: Current temperature (updates every 5 seconds)
with col2:
    temp_placeholder = st.empty()  # Placeholder for dynamic updates

# Column 3: Current door status (updates every 5 seconds)
with col3:
    door_placeholder = st.empty()  # Placeholder for dynamic updates

# ============================================================================
# LIVE UPDATE CONTROL BUTTONS
# ============================================================================
# Provide buttons to stop/resume live updates

button_col1, button_col2 = st.columns(2)

with button_col1:
    if st.button("⏸️ Stop Live Updates", use_container_width=True):
        st.session_state.stop_updates = True

with button_col2:
    if st.button("▶️ Resume Live Updates", use_container_width=True):
        st.session_state.stop_updates = False
        st.rerun()

# ============================================================================
# LIVE METRICS UPDATE FUNCTION
# ============================================================================
# Function to fetch and display current temperature and door status
# Called initially and then every 5 seconds in the update loop

def update_live_metrics():
    """
    Fetch and display current temperature and door status.
    
    This function:
    1. Calls fn.get_current_temperature() to get latest temperature
    2. Converts temperature to selected unit (Celsius or Fahrenheit)
    3. Updates temperature metric display
    4. Calls fn.get_current_door_status() to get latest door status
    5. Updates door status metric display
    
    Uses st.empty() placeholders (temp_placeholder, door_placeholder)
    to update metrics without rerunning the entire app.
    """
    # Fetch current temperature from API
    temp_data = fn.get_current_temperature(temp_sensor_id)
    if temp_data and temp_data.get("ambientTemperature") is not None:
        # Convert from millidegrees Celsius to Celsius
        temp_celsius = temp_data["ambientTemperature"] / 1000.0
        # Convert to Fahrenheit if needed
        if temp_unit == "Fahrenheit":
            current_temp = fn.celsius_to_fahrenheit(temp_celsius)
        else:
            current_temp = temp_celsius
        # Update temperature display with 1 decimal place
        temp_placeholder.metric("Current Temperature", f"🌡️ {current_temp:.1f}{temp_symbol}")
    else:
        # Show N/A if no data available
        temp_placeholder.metric("Current Temperature", "N/A")
    
    # Fetch current door status from API (only if door sensor exists)
    if door_sensor_id:
        door_data = fn.get_current_door_status(door_sensor_id)
        if door_data and "doorClosed" in door_data:
            # Display with emoji: ✅ for closed, ⚠️ for open
            door_status = "✅ Closed" if door_data["doorClosed"] else "⚠️ Open"
            door_placeholder.metric("Door Status", door_status)
        else:
            # Show N/A if no data available
            door_placeholder.metric("Door Status", "N/A")
    else:
        # Show "No Sensor" if vehicle has no door sensor
        door_placeholder.metric("Door Status", "No Sensor")

# Initial update - display metrics immediately on page load
update_live_metrics()

# ============================================================================
# STATIC CONTENT - HISTORICAL DATA SECTION
# ============================================================================
# Fetch and display historical temperature and door data
# This section is rendered once and does not update in the live loop

st.markdown("---")  # Horizontal separator

# ============================================================================
# DATA FETCHING - TEMPERATURE HISTORY
# ============================================================================
# Fetch historical temperature data for the selected time range
# Uses 60-second intervals (stepMs=60000) for detailed visualization

with st.spinner("Loading temperature data..."):
    temp_df = fn.get_historic_temperature(temp_sensor_id, start_ms, end_ms, stepMs=60000)

# ============================================================================
# DATA FETCHING - DOOR HISTORY
# ============================================================================
# Fetch historical door status data for the selected time range
# Uses 5-second intervals (stepMs=5000) for precise event detection
# Only fetches if vehicle has a door sensor

if door_sensor_id:
    with st.spinner("Loading door events..."):
        door_df = fn.get_historic_door(door_sensor_id, start_ms, end_ms, stepMs=5000)
else:
    # Create empty DataFrame if no door sensor
    door_df = pd.DataFrame()

# ============================================================================
# DATA PROCESSING - TEMPERATURE
# ============================================================================
# Process temperature data: convert timestamps, convert units, remove nulls

if not temp_df.empty:
    # Convert millisecond timestamps to datetime objects
    temp_df["datetime"] = temp_df["timeMs"].apply(fn.ms_to_datetime)

    # Convert from millicelsius to celsius (API returns millidegrees)
    temp_df["celsius"] = temp_df["ambientTemperature"] / 1000.0

    # Convert temperature to selected unit
    if temp_unit == "Fahrenheit":
        temp_df["temperature"] = temp_df["celsius"].apply(fn.celsius_to_fahrenheit)
    else:
        temp_df["temperature"] = temp_df["celsius"]

    # Remove null values for cleaner visualization
    temp_df = temp_df[temp_df["temperature"].notna()]

# ============================================================================
# DATA PROCESSING - DOOR EVENTS
# ============================================================================
# Process door data to detect door open events
# Door open event = transition from doorClosed=True to doorClosed=False

door_events = []  # List to store datetime objects of door open events
if not door_df.empty:
    # Convert millisecond timestamps to datetime objects
    door_df["datetime"] = door_df["timeMs"].apply(fn.ms_to_datetime)

    # Detect door open events (when doorClosed changes from True to False)
    # shift(1) compares current row with previous row
    door_df["door_opened"] = (door_df["doorClosed"] == False) & (door_df["doorClosed"].shift(1) == True)
    
    # Extract datetime values where door_opened is True
    door_events = door_df[door_df["door_opened"]]["datetime"].tolist()

# ============================================================================
# CHART CREATION - TEMPERATURE PLOT WITH THRESHOLDS AND DOOR EVENTS
# ============================================================================
# Create interactive Plotly chart showing:
# - Temperature line (blue)
# - Min threshold line (blue dashed)
# - Max threshold line (red dashed)
# - Door open events (orange vertical lines or markers)

if not temp_df.empty:
    # Initialize Plotly figure
    fig = go.Figure()

    # ========================================================================
    # TRACE 1: Temperature Line
    # ========================================================================
    # Main temperature data as a blue line
    fig.add_trace(go.Scatter(
        x=temp_df["datetime"],  # X-axis: time
        y=temp_df["temperature"],  # Y-axis: temperature
        mode="lines",  # Line chart
        name="Temperature",  # Legend label
        line=dict(color="#1f77b4", width=2),  # Blue line, 2px width
        hovertemplate="<b>Time:</b> %{x}<br><b>Temperature:</b> %{y:.1f}" + temp_symbol + "<extra></extra>"
    ))

    # ========================================================================
    # TRACE 2: Minimum Threshold Line
    # ========================================================================
    # Horizontal dashed line showing minimum acceptable temperature
    fig.add_trace(go.Scatter(
        x=[temp_df["datetime"].min(), temp_df["datetime"].max()],  # Span entire time range
        y=[min_temp, min_temp],  # Constant y value
        mode="lines",  # Line chart
        name=f"Min Threshold ({min_temp}{temp_symbol})",  # Legend label
        line=dict(color="blue", width=2, dash="dash"),  # Blue dashed line
        hovertemplate=f"<b>Min Threshold:</b> {min_temp}{temp_symbol}<extra></extra>"
    ))

    # ========================================================================
    # TRACE 3: Maximum Threshold Line
    # ========================================================================
    # Horizontal dashed line showing maximum acceptable temperature
    fig.add_trace(go.Scatter(
        x=[temp_df["datetime"].min(), temp_df["datetime"].max()],  # Span entire time range
        y=[max_temp, max_temp],  # Constant y value
        mode="lines",  # Line chart
        name=f"Max Threshold ({max_temp}{temp_symbol})",  # Legend label
        line=dict(color="red", width=2, dash="dash"),  # Red dashed line
        hovertemplate=f"<b>Max Threshold:</b> {max_temp}{temp_symbol}<extra></extra>"
    ))

    # ========================================================================
    # DOOR EVENTS VISUALIZATION
    # ========================================================================
    # Display door open events as either vertical lines or markers
    # User selects display mode via sidebar radio button
    
    if door_events:
        if door_display == "Vertical Lines":
            # Option 1: Vertical dotted lines spanning the entire chart height
            for event_time in door_events:
                fig.add_shape(
                    type="line",
                    x0=event_time,  # X position of line
                    x1=event_time,  # Same X (vertical line)
                    y0=0,  # Bottom of chart (paper coordinates)
                    y1=1,  # Top of chart (paper coordinates)
                    yref="paper",  # Use paper coordinates (0-1) instead of data coordinates
                    line=dict(color="orange", width=2, dash="dot")  # Orange dotted line
                )

            # Add dummy trace for legend (shapes don't appear in legend)
            fig.add_trace(go.Scatter(
                x=[door_events[0]],  # Use first event time
                y=[None],  # No y value (won't be visible)
                mode="lines",
                name="Door Opened",  # Legend label
                line=dict(color="orange", width=2, dash="dot"),
                showlegend=True  # Show in legend
            ))
        else:  # Markers
            # Option 2: Diamond markers on the temperature line at door open times
            event_temps = []
            # For each door event, find the closest temperature reading
            for event_time in door_events:
                time_diff = abs(temp_df["datetime"] - event_time)  # Calculate time difference
                closest_idx = time_diff.argmin()  # Find index of closest time
                closest_temp = temp_df.iloc[closest_idx]  # Get temperature at that time
                event_temps.append(closest_temp["temperature"])

            # Add scatter trace with diamond markers
            fig.add_trace(go.Scatter(
                x=door_events,  # X: door event times
                y=event_temps,  # Y: temperature at those times
                mode="markers",  # Marker chart
                name="Door Opened",  # Legend label
                marker=dict(  # https://plotly.com/python/marker-style/
                    color="orange",  # Orange markers
                    size=8,  # 8px size
                    symbol="diamond",  # Diamond shape
                    line=dict(color="rgba(255, 140, 0, 0.8)", width=2)  # Orange border
                ),
                hovertemplate="<b>Door Opened</b><br><b>Time:</b> %{x}<br><b>Temperature:</b> %{y:.1f}" + temp_symbol + "<extra></extra>"
            ))

    # ========================================================================
    # CHART LAYOUT CONFIGURATION
    # ========================================================================
    # Configure chart appearance, axes, legend, and interactivity
    
    fig.update_layout(
        title=f"Temperature Monitoring - {selected_vehicle_row['name']}",  # Chart title with vehicle name
        xaxis_title="Time",  # X-axis label
        yaxis_title=f"Temperature ({temp_symbol})",  # Y-axis label with unit
        hovermode="x unified",  # Show all traces' values at same x position
        height=600,  # Chart height in pixels
        showlegend=True,  # Display legend
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="bottom",  # Anchor to bottom
            y=1.02,  # Position above chart
            xanchor="right",  # Anchor to right
            x=1  # Position at right edge
        ),
        plot_bgcolor="white",  # White background
        xaxis=dict(
            showgrid=True,  # Show vertical grid lines
            gridcolor="lightgray",  # Light gray grid
            showline=True,  # Show axis line
            linecolor="black"  # Black axis line
        ),
        yaxis=dict(
            showgrid=True,  # Show horizontal grid lines
            gridcolor="lightgray",  # Light gray grid
            showline=True,  # Show axis line
            linecolor="black"  # Black axis line
        )
    )

    # Display the chart in Streamlit (full container width)
    st.plotly_chart(fig, use_container_width=True)

    # ========================================================================
    # STATISTICS SECTION
    # ========================================================================
    # Display summary statistics in four columns:
    # Average, Minimum, Maximum temperatures, and Door open event count
    
    st.subheader("📊 Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Calculate and display average temperature
        avg_temp = temp_df["temperature"].mean()
        st.metric("Average Temperature", f"{avg_temp:.1f}{temp_symbol}")

    with col2:
        # Display minimum temperature
        min_temp_val = temp_df["temperature"].min()
        st.metric("Minimum Temperature", f"{min_temp_val:.1f}{temp_symbol}")

    with col3:
        # Display maximum temperature
        max_temp_val = temp_df["temperature"].max()
        st.metric("Maximum Temperature", f"{max_temp_val:.1f}{temp_symbol}")

    with col4:
        # Display count of door open events
        st.metric("Door Open Events", len(door_events))

    # ========================================================================
    # THRESHOLD VIOLATIONS SECTION
    # ========================================================================
    # Identify and display temperature readings outside threshold range
    # Shows warning if violations exist, success message if none
    
    # Filter temperature data for values outside threshold range
    violations = temp_df[
        (temp_df["temperature"] < min_temp) |  # Below minimum
        (temp_df["temperature"] > max_temp)  # Above maximum
    ]

    if not violations.empty:
        # Display warning with violation count
        st.warning(f"⚠️ {len(violations)} temperature readings outside threshold range!")

        # Expandable section to view violation details
        with st.expander("View Violations"):
            # Create display DataFrame with datetime and temperature
            violations_display = violations[["datetime", "temperature"]].copy()
            # Format temperature with unit symbol
            violations_display["temperature"] = violations_display["temperature"].apply(
                lambda x: f"{x:.1f}{temp_symbol}"
            )
            # Display as interactive table
            st.dataframe(violations_display, use_container_width=True)
    else:
        # Display success message if no violations
        st.success("✅ All temperature readings within threshold range!")

    # ========================================================================
    # DOOR EVENTS TABLE SECTION
    # ========================================================================
    # Display detailed table of all door open events in expandable section
    
    if door_events:
        # Expandable section with event count in title
        with st.expander(f"View Door Events ({len(door_events)} events)"):
            # Create DataFrame with event times and labels
            door_events_df = pd.DataFrame({
                "Event Time": door_events,
                "Event": ["Door Opened"] * len(door_events)  # Label for each event
            })
            # Display as interactive table
            st.dataframe(door_events_df, use_container_width=True)

else:
    # Display warning if no temperature data available for selected time range
    st.warning("No temperature data available for the selected time range.")

# ============================================================================
# FOOTER
# ============================================================================
# Display footer with last updated timestamp

st.markdown("---")  # Horizontal separator
st.markdown(
    f"*Temperature & Door Monitoring Dashboard | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
)

# ============================================================================
# CONTINUOUS UPDATE LOOP WITH COUNTDOWN
# ============================================================================
# Update live metrics every 5 seconds for 6 minutes (72 cycles)
# Displays countdown timer inside the Live Status header
# 72 cycles limit is set to stay within free tier API limits

cycles = 72  # 72 cycles * 5 seconds = 360 seconds (6 minutes) - optimized for free tier API limits

# Main update loop
for cycle in range(cycles):
    # Check if user requested to stop updates
    if st.session_state.stop_updates:
        status_header.markdown(
            '### ⏸️ Live Updates Paused. (Click "▶️ Resume Live Updates" to continue.)'
        )
        break
    
    # Countdown from 5 to 1 seconds
    for remaining in range(5, 0, -1):
        status_header.markdown(f"### 🟢 Live (_Next update in {remaining}s..._)")
        time.sleep(1)  # Wait 1 second
    
    # Update live metrics after countdown completes
    update_live_metrics()

# After the loop ends, display message that updates have stopped
if not st.session_state.stop_updates:
    status_header.markdown(
        '### 🛑 Live Updates Stopped. (Click "🔄 Refresh Data" to resume.)'
    )