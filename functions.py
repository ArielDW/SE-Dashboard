# ============================================================================
# SAMSARA API INTEGRATION MODULE
# ============================================================================
# This module provides utility functions for interacting with the Samsara API
# to retrieve vehicle, sensor, and telemetry data for fleet monitoring.
# 
# Key Features:
# - Organization and vehicle data retrieval
# - Historical and current sensor readings (temperature, door status)
# - Time conversion utilities
# - Temperature unit conversion
# ============================================================================

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================

# Default sensor ID for testing/development purposes
# widgetId = 278018088211512

# Default time range in milliseconds since Unix epoch for testing
# startMs = 1763064102000  # Start time for historical queries
# endMs = 1763082815516    # End time for historical queries

# Samsara API authentication token retrieved from Streamlit secrets
SAMSARA_API = st.secrets["SAMSARA_API"]

# ============================================================================
# ACTIVE FUNCTIONS - Currently used in streamlit_app.py
# ============================================================================

def get_org_details():
    """
    Retrieve organization details from Samsara API.
    
    Makes a GET request to the /me endpoint to fetch the authenticated
    organization's ID and name.
    
    API Endpoint: GET https://api.samsara.com/me
    
    Used in UI: Sidebar - Organization Info Box
    - Displays organization name and ID at the top of the sidebar
    - Cached for 1 hour using @st.cache_data(ttl=3600)
    - Shows in blue info box with organization icon
    
    Returns:
        tuple: (org_id, org_name) - Organization ID and name as strings
               Returns (None, None) if an error occurs
    
    Example:
        org_id, org_name = get_org_details()
        # Returns: ("123456789", "Acme Transportation")
    """
    url = "https://api.samsara.com/me"
    headers = {"Authorization": f"Bearer {SAMSARA_API}"}
    
    try:
        # Make authenticated GET request
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Extract organization details from response
        org_id = data["data"]["id"]
        org_name = data["data"]["name"]
        return org_id, org_name
    except Exception as e:
        print(f"Error fetching org details: {e}")
        return None, None


def get_vehicles():
    """
    Retrieve all vehicles from Samsara API with their sensor configurations.
    
    This function fetches all vehicles in the organization and expands each
    vehicle into multiple rows based on the number of sensors installed.
    Handles pagination automatically to retrieve all vehicles.
    
    API Endpoint: GET https://api.samsara.com/fleet/vehicles
    
    Used in UI: Multiple Locations
    1. Sidebar - Vehicle Selector Dropdown
       - Populates the "Select Vehicle" dropdown with vehicle names
       - Cached for 5 minutes using @st.cache_data(ttl=300)
    
    2. Sidebar - Sensors Table
       - Displays all sensors for the selected vehicle
       - Shows sensorType, sensorPosition, and sensorName columns
    
    3. Main Logic - Sensor ID Extraction
       - Filters to get temperature sensor ID for the selected vehicle
       - Filters to get door sensor ID for the selected vehicle
    
    Returns:
        pandas.DataFrame: DataFrame with the following columns:
            - id: Vehicle ID
            - name: Vehicle name
            - licensePlate: License plate number
            - make: Vehicle manufacturer
            - model: Vehicle model
            - serial: Serial number
            - vin: Vehicle Identification Number
            - year: Manufacturing year
            - sensorType: Type of sensor (temperature, humidity, door, or None)
            - sensorPosition: Position of sensor (middle, back, etc.)
            - sensorName: Human-readable sensor name
            - sensorId: Unique sensor ID (widgetId)
            - sensorMac: MAC address of sensor
    
    Data Structure:
        - Vehicles with multiple sensors appear on multiple rows
        - Each row represents one sensor on a vehicle
        - Vehicles without sensors have one row with None sensor values
    
    Example Output:
        id              name            sensorType  sensorId
        281474985231664 Vehicle 01      temperature 278018088211512
        281474985231664 Vehicle 01      door        278018089917378
        281474999314344 Vehicle 02 (SE) temperature 278018084915903
    """
    url = "https://api.samsara.com/fleet/vehicles"
    params = {}
    headers = {"Authorization": f"Bearer {SAMSARA_API}"}
    
    vehicles_list = []
    hasNextPage = True
    
    # Pagination loop - continues until all pages are retrieved
    while hasNextPage:
        try:
            response = requests.request("GET", url, headers=headers, params=params).json()
            
            # Process each vehicle in the current page
            for vehicle in response["data"]:
                # Extract basic vehicle information
                vehicle_id = vehicle.get("id")
                vehicle_name = vehicle.get("name")
                license_plate = vehicle.get("licensePlate")
                make = vehicle.get("make")
                model = vehicle.get("model")
                serial = vehicle.get("serial")
                vin = vehicle.get("vin")
                year = vehicle.get("year")
                
                # Check if vehicle has sensor configuration
                sensor_config = vehicle.get("sensorConfiguration")
                
                if sensor_config:
                    # Process temperature sensors from each area
                    areas = sensor_config.get("areas", [])
                    for area in areas:
                        # Add row for each temperature sensor
                        for temp_sensor in area.get("temperatureSensors", []):
                            vehicles_list.append({
                                "id": vehicle_id,
                                "name": vehicle_name,
                                "licensePlate": license_plate,
                                "make": make,
                                "model": model,
                                "serial": serial,
                                "vin": vin,
                                "year": year,
                                "sensorType": "temperature",
                                "sensorPosition": area.get("position"),
                                "sensorName": temp_sensor.get("name"),
                                "sensorId": temp_sensor.get("id"),
                                "sensorMac": temp_sensor.get("mac")
                            })
                        
                        # Add row for each humidity sensor
                        for humidity_sensor in area.get("humiditySensors", []):
                            vehicles_list.append({
                                "id": vehicle_id,
                                "name": vehicle_name,
                                "licensePlate": license_plate,
                                "make": make,
                                "model": model,
                                "serial": serial,
                                "vin": vin,
                                "year": year,
                                "sensorType": "humidity",
                                "sensorPosition": area.get("position"),
                                "sensorName": humidity_sensor.get("name"),
                                "sensorId": humidity_sensor.get("id"),
                                "sensorMac": humidity_sensor.get("mac")
                            })
                    
                    # Process door sensors
                    doors = sensor_config.get("doors", [])
                    for door in doors:
                        door_sensor = door.get("sensor", {})
                        vehicles_list.append({
                            "id": vehicle_id,
                            "name": vehicle_name,
                            "licensePlate": license_plate,
                            "make": make,
                            "model": model,
                            "serial": serial,
                            "vin": vin,
                            "year": year,
                            "sensorType": "door",
                            "sensorPosition": door.get("position"),
                            "sensorName": door_sensor.get("name"),
                            "sensorId": door_sensor.get("id"),
                            "sensorMac": door_sensor.get("mac")
                        })
                else:
                    # Vehicle has no sensors - add one row with None values
                    vehicles_list.append({
                        "id": vehicle_id,
                        "name": vehicle_name,
                        "licensePlate": license_plate,
                        "make": make,
                        "model": model,
                        "serial": serial,
                        "vin": vin,
                        "year": year,
                        "sensorType": None,
                        "sensorPosition": None,
                        "sensorName": None,
                        "sensorId": None,
                        "sensorMac": None
                    })
            
            # Check if there are more pages to fetch
            hasNextPage = response["pagination"]["hasNextPage"]
            if hasNextPage:
                # Set cursor for next page
                params["after"] = response["pagination"]["endCursor"]
            
        except Exception as e:
            print(f"Error fetching vehicles: {e}")
            break
    
    # Convert list of dictionaries to DataFrame and return
    df = pd.DataFrame(vehicles_list)
    return df


def get_historic_temperature(widgetId, startMs, endMs, stepMs=300000):
    """
    Get historical temperature data for a specific sensor over a time range.
    
    Retrieves temperature readings at regular intervals for analysis and
    visualization. Uses the Samsara sensors history API.
    
    API Endpoint: POST https://api.samsara.com/v1/sensors/history
    
    Used in UI: Main Content - Temperature Chart
    - Fetches historical temperature data for the selected time range
    - Called with stepMs=60000 (1 minute intervals) for detailed plotting
    - Data is converted to Celsius, then optionally to Fahrenheit
    - Plotted as a blue line chart with Plotly
    - Used to calculate statistics (avg, min, max temperature)
    - Used to detect threshold violations
    
    Args:
        widgetId (int): Sensor ID to query for temperature data
        startMs (int): Start time in milliseconds since Unix epoch
        endMs (int): End time in milliseconds since Unix epoch
        stepMs (int, optional): Time interval between data points in milliseconds.
                                Defaults to 300000 (5 minutes)
    
    Returns:
        pandas.DataFrame: DataFrame with columns:
            - timeMs: Timestamp in milliseconds
            - ambientTemperature: Temperature reading in millidegrees Celsius
                                 (divide by 1000 to get actual °C)
        Returns empty DataFrame with proper columns if no data found
    
    Note:
        - fillMissing is set to "withNull" - missing data points are null
        - Temperature values are in millidegrees Celsius (e.g., 25000 = 25°C)
    
    Example:
        df = get_historic_temperature(278018088211512, 1763064102000, 1763082815516)
        # Returns DataFrame with temperature readings every 5 minutes
    """
    url = "https://api.samsara.com/v1/sensors/history"
    
    # Construct API payload
    payload = {
        "fillMissing": "withNull",  # Fill missing data with null values
        "series": [
            {
                "field": "ambientTemperature",  # Request temperature data
                "widgetId": widgetId
            }
        ],
        "endMs": endMs,
        "startMs": startMs,
        "stepMs": stepMs  # Interval between data points
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }
    
    try:
        # Make POST request to retrieve historical data
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        # Check if results exist
        if not data.get("results"):
            return pd.DataFrame(columns=["timeMs", "ambientTemperature"])
        
        # Convert results to DataFrame
        df = pd.DataFrame(data["results"])
        # Extract temperature value from nested series array
        df['ambientTemperature'] = df['series'].str[0]
        # Remove original series column
        df = df.drop(columns=['series'])
        return df
    except Exception as e:
        print(f"Error fetching temperature data: {e}")
        return pd.DataFrame(columns=["timeMs", "ambientTemperature"])


def get_historic_door(widgetId, startMs, endMs, stepMs=5000):
    """
    Get historical door status data for a specific sensor over a time range.
    
    Retrieves door open/closed status at regular intervals. Uses a smaller
    step size than temperature to capture door events more precisely.
    
    API Endpoint: POST https://api.samsara.com/v1/sensors/history
    
    Used in UI: Main Content - Door Events on Temperature Chart
    - Fetches historical door status for the selected time range
    - Called with stepMs=5000 (5 second intervals) for precise event detection
    - Detects door open events (when doorClosed changes from True to False)
    - Events displayed as either:
      * Orange vertical dotted lines across the chart, OR
      * Orange diamond markers on the temperature line
    - Door event count shown in statistics section
    - Door events table available in expandable section
    
    Args:
        widgetId (int): Door sensor ID to query
        startMs (int): Start time in milliseconds since Unix epoch
        endMs (int): End time in milliseconds since Unix epoch
        stepMs (int, optional): Time interval between data points in milliseconds.
                                Defaults to 5000 (5 seconds)
    
    Returns:
        pandas.DataFrame: DataFrame with columns:
            - timeMs: Timestamp in milliseconds
            - doorClosed: Boolean value (True = closed, False = open)
        Returns empty DataFrame with proper columns if no data found
    
    Note:
        - fillMissing is set to "withPrevious" - carries forward last known status
        - Smaller stepMs (5s vs 5min for temp) for granular door event tracking
    
    Example:
        df = get_historic_door(278018089917378, 1763064102000, 1763082815516)
        # Returns DataFrame with door status every 5 seconds
    """
    url = "https://api.samsara.com/v1/sensors/history"
    
    # Construct API payload
    payload = {
        "series": [
            {
                "field": "doorClosed",  # Request door status data
                "widgetId": widgetId
            }
        ],
        "endMs": endMs,
        "fillMissing": "withPrevious",  # Carry forward last known status
        "startMs": startMs,
        "stepMs": stepMs  # Interval between data points
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }
    
    try:
        # Make POST request to retrieve historical data
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        # Check if results exist
        if not data.get("results"):
            return pd.DataFrame(columns=["timeMs", "doorClosed"])
        
        # Convert results to DataFrame
        df = pd.DataFrame(data["results"])
        # Extract door status from nested series array
        df['doorClosed'] = df['series'].str[0]
        # Remove original series column
        df = df.drop(columns=['series'])
        return df
    except Exception as e:
        print(f"Error fetching door data: {e}")
        return pd.DataFrame(columns=["timeMs", "doorClosed"])


def celsius_to_fahrenheit(celsius):
    """
    Convert temperature from Celsius to Fahrenheit.
    
    Uses the standard conversion formula: (°C × 9/5) + 32 = °F
    
    Used in UI: Multiple Locations (when Fahrenheit is selected)
    1. Live Status Section - Current Temperature Metric
       - Converts current temperature reading to Fahrenheit
    
    2. Main Chart - Temperature Data
       - Converts all historical temperature readings to Fahrenheit
       - Applied to entire temp_df["celsius"] column
    
    3. Statistics Section
       - Average, minimum, and maximum temperatures displayed in Fahrenheit
    
    Args:
        celsius (float or None): Temperature in Celsius
    
    Returns:
        float or None: Temperature in Fahrenheit, or None if input is None
    
    Example:
        temp_f = celsius_to_fahrenheit(25)  # Returns 77.0
        temp_f = celsius_to_fahrenheit(None)  # Returns None
    """
    if celsius is None:
        return None
    return (celsius * 9/5) + 32


def ms_to_datetime(ms):
    """
    Convert Unix timestamp in milliseconds to Python datetime object.
    
    Used in UI: Data Processing for Charts
    - Converts timeMs column from temperature DataFrame to datetime
    - Converts timeMs column from door DataFrame to datetime
    - Used for x-axis values in Plotly charts
    - Applied using: temp_df["datetime"] = temp_df["timeMs"].apply(fn.ms_to_datetime)
    
    Args:
        ms (int): Timestamp in milliseconds since Unix epoch (Jan 1, 1970)
    
    Returns:
        datetime: Python datetime object in local timezone
    
    Example:
        dt = ms_to_datetime(1763064102000)
        # Returns: datetime(2025, 11, 14, 10, 51, 30)
    """
    return datetime.fromtimestamp(ms / 1000)


def datetime_to_ms(dt):
    """
    Convert Python datetime object to Unix timestamp in milliseconds.
    
    Used in UI: Sidebar - Time Range Configuration
    - Converts start_time (datetime) to start_ms for API calls
    - Converts end_time (datetime) to end_ms for API calls
    - Handles all time range options:
      * "Now (Last 24 hours)"
      * "Last 7 days"
      * "Last 30 days"
      * "Custom Range" (from date/time pickers)
    
    Args:
        dt (datetime): Python datetime object
    
    Returns:
        int: Timestamp in milliseconds since Unix epoch
    
    Example:
        ms = datetime_to_ms(datetime(2025, 11, 14, 10, 51, 30))
        # Returns: 1763064102000
    """
    return int(dt.timestamp() * 1000)


def get_current_temperature(widgetId):
    """
    Get the most recent temperature reading for a specific sensor.
    
    Retrieves the current/latest temperature value without needing to
    specify a time range. Useful for real-time monitoring dashboards.
    
    API Endpoint: POST https://api.samsara.com/v1/sensors/temperature
    
    Used in UI: Live Status Section - Current Temperature Metric
    - Updates every 5 seconds in the live metrics section
    - Displayed in the middle column of the 3-column layout
    - Shows temperature with 1 decimal place and unit symbol
    - Called by update_live_metrics() function
    - Runs in a loop for 2 minutes (24 cycles × 5 seconds)
    - Countdown timer shows "Next update in Xs"
    
    Args:
        widgetId (int): Sensor ID to query for current temperature
    
    Returns:
        dict or None: Dictionary containing sensor info and current temperature:
            - id: Sensor ID
            - name: Sensor name
            - ambientTemperature: Current temperature in millidegrees Celsius
            - ambientTemperatureTime: ISO 8601 timestamp of reading
            - vehicleId: Associated vehicle ID
        Returns None if no data found or error occurs
    
    Note:
        Temperature values are in millidegrees Celsius (divide by 1000 for °C)
    
    Example:
        sensor_data = get_current_temperature(278018088211512)
        # Returns: {
        #     'id': 278018088211512,
        #     'name': '01 - Reefer Temp (Mini fridge)',
        #     'ambientTemperature': 2539,  # 2.539°C
        #     'ambientTemperatureTime': '2025-11-14T10:51:30Z',
        #     'vehicleId': 281474985231664
        # }
    """
    url = "https://api.samsara.com/v1/sensors/temperature"

    # Construct API payload with sensor ID
    payload = {"sensors": [widgetId]}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }

    try:
        # Make POST request to retrieve current temperature
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()

        # Check if sensor data exists in response
        if data.get("sensors") and len(data["sensors"]) > 0:
            return data["sensors"][0]  # Return first (and only) sensor data
        else:
            print(f"No temperature data found for sensor {widgetId}")
            return None
    except Exception as e:
        print(f"Error fetching current temperature: {e}")
        return None


def get_current_door_status(widgetId):
    """
    Get the most recent door status for a specific sensor.
    
    Retrieves the current/latest door open/closed status without needing
    to specify a time range. Useful for real-time monitoring dashboards.
    
    API Endpoint: POST https://api.samsara.com/v1/sensors/door
    
    Used in UI: Live Status Section - Door Status Metric
    - Updates every 5 seconds in the live metrics section
    - Displayed in the right column of the 3-column layout
    - Shows "🔒 Closed" or "🔓 Open" with emoji icons
    - Called by update_live_metrics() function
    - Runs in a loop for 2 minutes (24 cycles × 5 seconds)
    - Only called if vehicle has a door sensor
    
    Args:
        widgetId (int): Door sensor ID to query for current status
    
    Returns:
        dict or None: Dictionary containing sensor info and current door status:
            - id: Sensor ID
            - name: Sensor name
            - doorClosed: Boolean (True = closed, False = open)
            - doorStatusTime: ISO 8601 timestamp of reading
            - vehicleId: Associated vehicle ID
        Returns None if no data found or error occurs
    
    Example:
        sensor_data = get_current_door_status(278018089917378)
        # Returns: {
        #     'id': 278018089917378,
        #     'name': '01 - Reefer Door (Mini fridge)',
        #     'doorClosed': True,
        #     'doorStatusTime': '2025-11-14T10:52:50Z',
        #     'vehicleId': 281474985231664
        # }
    """
    url = "https://api.samsara.com/v1/sensors/door"

    # Construct API payload with sensor ID
    payload = {"sensors": [widgetId]}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }

    try:
        # Make POST request to retrieve current door status
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()

        # Check if sensor data exists in response
        if data.get("sensors") and len(data["sensors"]) > 0:
            return data["sensors"][0]  # Return first (and only) sensor data
        else:
            print(f"No door status data found for sensor {widgetId}")
            return None
    except Exception as e:
        print(f"Error fetching current door status: {e}")
        return None


# ============================================================================
# UNUSED FUNCTIONS - Not currently called in streamlit_app.py
# ============================================================================
# These functions are commented out to clean up the codebase but are preserved
# for potential future use or reference. They were likely used in earlier
# versions of the application or are planned for future features.
#
# Included functions:
# - get_historic_humidity(): Retrieves historical humidity sensor data
# - get_current_status(): Aggregates all sensor data for a vehicle
# - fahrenheit_to_celsius(): Inverse temperature conversion
# - calculate_time_range_ms(): Helper for time range calculations
# - get_all_sensors(): Lists all sensors in the organization
#
# To use any of these functions, simply uncomment the desired function.
# ============================================================================

# def get_historic_humidity(widgetId, startMs, endMs, stepMs=300000):
#     """
#     Get historical humidity data for a specific sensor over a time range.
#     
#     Similar to get_historic_temperature() but retrieves humidity readings
#     instead of temperature data.
#     
#     API Endpoint: POST https://api.samsara.com/v1/sensors/history
#     
#     NOT CURRENTLY USED IN UI
#     - Could be used to add humidity monitoring to the dashboard
#     - Would require similar chart and statistics as temperature
#     
#     Args:
#         widgetId (int): Humidity sensor ID to query
#         startMs (int): Start time in milliseconds since Unix epoch
#         endMs (int): End time in milliseconds since Unix epoch
#         stepMs (int, optional): Time interval between data points in milliseconds.
#                                 Defaults to 300000 (5 minutes)
#     
#     Returns:
#         pandas.DataFrame: DataFrame with columns:
#             - timeMs: Timestamp in milliseconds
#             - humidity: Humidity percentage (0-100)
#         Returns empty DataFrame with proper columns if no data found
#     
#     Note:
#         fillMissing is set to "withPrevious" - carries forward last known value
#     """
#     url = "https://api.samsara.com/v1/sensors/history"
#     
#     payload = {
#         "fillMissing": "withPrevious",
#         "series": [
#             {
#                 "field": "humidity",
#                 "widgetId": widgetId
#             }
#         ],
#         "endMs": endMs,
#         "startMs": startMs,
#         "stepMs": stepMs
#     }
#     
#     headers = {
#         "accept": "application/json",
#         "content-type": "application/json",
#         "authorization": f"Bearer {SAMSARA_API}"
#     }
#     
#     try:
#         response = requests.post(url, json=payload, headers=headers)
#         response.raise_for_status()
#         data = response.json()
#         
#         if not data.get("results"):
#             return pd.DataFrame(columns=["timeMs", "humidity"])
#         
#         df = pd.DataFrame(data["results"])
#         df['humidity'] = df['series'].str[0]
#         df = df.drop(columns=['series'])
#         return df
#     except Exception as e:
#         print(f"Error fetching humidity data: {e}")
#         return pd.DataFrame(columns=["timeMs", "humidity"])


# def get_current_status(vehicle_id, sensor_config):
#     """
#     Get current temperature, humidity, and door status for a vehicle.
#     
#     Aggregates all sensor readings for a vehicle into a single status object.
#     Useful for dashboard overview displays showing all metrics at once.
#     
#     NOT CURRENTLY USED IN UI
#     - Current UI uses separate calls to get_current_temperature() and 
#       get_current_door_status() instead
#     - Could be used to simplify the update_live_metrics() function
#     - Would need modification to work with current data structure
#     
#     Args:
#         vehicle_id (int): Vehicle ID to get status for
#         sensor_config (dict): Sensor configuration dictionary containing:
#             - temperature: List of temperature sensor configs
#             - humidity: List of humidity sensor configs
#             - door: List of door sensor configs
#     
#     Returns:
#         dict or None: Dictionary containing:
#             - temperature: Current temperature value or None
#             - humidity: Current humidity value or None
#             - door_status: "Closed" or "Open" or None
#             - last_updated: ISO timestamp of when status was retrieved
#         Returns None if error occurs
#     
#     Note:
#         Queries the last 5 minutes of data for temperature/humidity
#         and last 1 minute for door status to get most recent values
#     """
#     try:
#         status = {
#             "temperature": None,
#             "humidity": None,
#             "door_status": None,
#             "last_updated": datetime.now().isoformat()
#         }
#         
#         # Get temperature sensor data from last 5 minutes
#         if sensor_config.get("temperature"):
#             temp_sensor_id = sensor_config["temperature"][0]["id"]
#             current_time_ms = int(datetime.now().timestamp() * 1000)
#             start_time_ms = current_time_ms - 300000  # Last 5 minutes
#             
#             df_temp = get_historic_temperature(temp_sensor_id, start_time_ms, current_time_ms, stepMs=60000)
#             if not df_temp.empty:
#                 status["temperature"] = df_temp['ambientTemperature'].iloc[-1]
#         
#         # Get humidity sensor data from last 5 minutes
#         if sensor_config.get("humidity"):
#             humidity_sensor_id = sensor_config["humidity"][0]["id"]
#             current_time_ms = int(datetime.now().timestamp() * 1000)
#             start_time_ms = current_time_ms - 300000
#             
#             df_humidity = get_historic_humidity(humidity_sensor_id, start_time_ms, current_time_ms, stepMs=60000)
#             if not df_humidity.empty:
#                 status["humidity"] = df_humidity['humidity'].iloc[-1]
#         
#         # Get door status from last 1 minute
#         if sensor_config.get("door"):
#             door_sensor_id = sensor_config["door"][0]["id"]
#             current_time_ms = int(datetime.now().timestamp() * 1000)
#             start_time_ms = current_time_ms - 60000  # Last 1 minute
#             
#             df_door = get_historic_door(door_sensor_id, start_time_ms, current_time_ms, stepMs=5000)
#             if not df_door.empty:
#                 door_closed = df_door['doorClosed'].iloc[-1]
#                 status["door_status"] = "Closed" if door_closed else "Open"
#         
#         return status
#     except Exception as e:
#         print(f"Error getting current status: {e}")
#         return None


# def fahrenheit_to_celsius(fahrenheit):
#     """
#     Convert temperature from Fahrenheit to Celsius.
#     
#     Inverse of celsius_to_fahrenheit(). Uses the standard conversion
#     formula: (°F - 32) × 5/9 = °C
#     
#     NOT CURRENTLY USED IN UI
#     - Current UI only converts from Celsius to Fahrenheit
#     - API always returns data in Celsius (millidegrees)
#     - Could be useful if user input in Fahrenheit is added
#     
#     Args:
#         fahrenheit (float or None): Temperature in Fahrenheit
#     
#     Returns:
#         float or None: Temperature in Celsius, or None if input is None
#     
#     Example:
#         temp_c = fahrenheit_to_celsius(77)  # Returns 25.0
#         temp_c = fahrenheit_to_celsius(None)  # Returns None
#     """
#     if fahrenheit is None:
#         return None
#     return (fahrenheit - 32) * 5/9


# def calculate_time_range_ms(hours):
#     """
#     Calculate start and end time in milliseconds based on hours back from now.
#     
#     Helper function to generate time ranges for historical queries without
#     manually calculating timestamps.
#     
#     NOT CURRENTLY USED IN UI
#     - Current UI calculates time ranges directly using datetime and timedelta
#     - Then converts using datetime_to_ms()
#     - Could simplify time range calculation in sidebar
#     
#     Args:
#         hours (int or float): Number of hours to look back from current time
#     
#     Returns:
#         tuple: (start_ms, end_ms) - Start and end timestamps in milliseconds
#     
#     Example:
#         start_ms, end_ms = calculate_time_range_ms(24)
#         # Returns timestamps for last 24 hours
#         df = get_historic_temperature(sensor_id, start_ms, end_ms)
#     """
#     current_time = datetime.now()
#     start_time = current_time - pd.Timedelta(hours=hours)
#     
#     return datetime_to_ms(start_time), datetime_to_ms(current_time)


# def get_all_sensors():
#     """
#     Get all sensors in the organization regardless of vehicle assignment.
#     
#     Retrieves a complete list of all sensors registered to the organization.
#     Unlike get_vehicles() which groups sensors by vehicle, this returns
#     a flat list of all sensors.
#     
#     API Endpoint: POST https://api.samsara.com/v1/sensors/list
#     
#     NOT CURRENTLY USED IN UI
#     - Current UI uses get_vehicles() which includes sensor information
#     - Could be useful for:
#       * Sensor inventory management page
#       * Finding unassigned sensors
#       * Sensor health monitoring across all devices
#     
#     Returns:
#         pandas.DataFrame: DataFrame containing all sensor information
#         Returns empty DataFrame if error occurs
#     
#     Note:
#         This endpoint may return sensors not currently assigned to vehicles
#     
#     Example:
#         df = get_all_sensors()
#         # Returns DataFrame with all sensors in the organization
#     """
#     url = "https://api.samsara.com/v1/sensors/list"
#     headers = {
#         "accept": "application/json",
#         "authorization": f"Bearer {SAMSARA_API}"
#     }
#     
#     try:
#         response = requests.post(url, headers=headers)
#         response.raise_for_status()
#         data = response.json()
#         df = pd.DataFrame(data["sensors"])
#         return df
#     except Exception as e:
#         print(f"Error fetching sensors: {e}")
#         return pd.DataFrame()