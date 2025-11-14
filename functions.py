import streamlit as st
import requests
import pandas as pd
from datetime import datetime

widgetId = 278018088211512

startMs = 1763064102000

endMs = 1763082815516

SAMSARA_API = st.secrets["SAMSARA_API"]

# Gets the organization Name and ID.
def get_org_details():
    """Retrieve organization details from Samsara API"""
    url = "https://api.samsara.com/me"
    headers = {"Authorization": f"Bearer {SAMSARA_API}"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        org_id = data["data"]["id"]
        org_name = data["data"]["name"]
        return org_id, org_name
    except Exception as e:
        print(f"Error fetching org details: {e}")
        return None, None


# Gets the list of vehicles in the organization by Sensor
""" 
Example of returned dataframe:
                id                                     name licensePlate       make     model      serial                vin  year   sensorType sensorPosition                      sensorName         sensorId          sensorMac
0  281474985231664                               Vehicle 01      MEP360A  CHEVROLET  CAVALIER  GUWT47TT6X  LSGKB52HXJV192457  2018  temperature         middle  01 - Reefer Temp (Mini fridge)  278018088211512  fc:db:21:63:94:38
1  281474985231664                               Vehicle 01      MEP360A  CHEVROLET  CAVALIER  GUWT47TT6X  LSGKB52HXJV192457  2018         door           back  01 - Reefer Door (Mini fridge)  278018089917378  fc:db:21:7d:9b:c2
2  281474992923086                              Deactivated         None       None      None        None               None  None         None           None                            None             None               None
3  281474998055859  Sprinter Van [Last Mile Delivery Route]         None       None      None        None               None  None         None           None                            None             None               None
4  281474998055862                 Passenger Bus [UK Route]         None       None      None        None               None  None         None           None                            None             None               None
5  281474998055864                  Truck [CA <-> US Route]         None       None      None        None               None  None         None           None                            None             None               None
6  281474999239878                           GUWT47TT6X old         None       None      None        None               None  None         None           None                            None             None               None
7  281474999314344                          Vehicle 02 (SE)     QWERTY12       None      None  GPKDD5X475               None  None  temperature         middle                  02 - Temp (SE)  278018084915903  fc:db:21:31:4a:bf
8  281474999314344                          Vehicle 02 (SE)     QWERTY12       None      None  GPKDD5X475               None  None     humidity         middle                  02 - Temp (SE)  278018084915903  fc:db:21:31:4a:bf
9  281474999314344                          Vehicle 02 (SE)     QWERTY12       None      None  GPKDD5X475               None  None         door           back                  02 - Door (SE)  278018089941478  fc:db:21:7d:f9:e6

entries with the same vehicle id are the same vehicle but have multiple sensors installed. 
"""
def get_vehicles():
    """Retrieve all vehicles from Samsara API, filtering for those with sensors"""
    url = "https://api.samsara.com/fleet/vehicles"
    params = {}
    headers = {"Authorization": f"Bearer {SAMSARA_API}"}
    
    vehicles_list = []
    hasNextPage = True
    
    while hasNextPage:
        try:
            response = requests.request("GET", url, headers=headers, params=params).json()
            
            for vehicle in response["data"]:
                # Get basic vehicle info
                vehicle_id = vehicle.get("id")
                vehicle_name = vehicle.get("name")
                license_plate = vehicle.get("licensePlate")
                make = vehicle.get("make")
                model = vehicle.get("model")
                serial = vehicle.get("serial")
                vin = vehicle.get("vin")
                year = vehicle.get("year")
                
                # Check if vehicle has sensors
                sensor_config = vehicle.get("sensorConfiguration")
                
                if sensor_config:
                    # Get temperature sensors
                    areas = sensor_config.get("areas", [])
                    for area in areas:
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
                        
                        # Get humidity sensors
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
                    
                    # Get door sensors
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
                    # Vehicle has no sensors, add one row
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
            
            # Check if there are more pages
            hasNextPage = response["pagination"]["hasNextPage"]
            if hasNextPage:
                params["after"] = response["pagination"]["endCursor"]
            
        except Exception as e:
            print(f"Error fetching vehicles: {e}")
            break
    
    # Convert to DataFrame and return
    df = pd.DataFrame(vehicles_list)
    return df


def get_historic_temperature(widgetId, startMs, endMs, stepMs=300000):
    """Get historic temperature data for a specific sensor"""
    url = "https://api.samsara.com/v1/sensors/history"
    
    payload = {
        "fillMissing": "withNull",
        "series": [
            {
                "field": "ambientTemperature",
                "widgetId": widgetId
            }
        ],
        "endMs": endMs,
        "startMs": startMs,
        "stepMs": stepMs
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("results"):
            return pd.DataFrame(columns=["timeMs", "ambientTemperature"])
        
        df = pd.DataFrame(data["results"])
        df['ambientTemperature'] = df['series'].str[0]
        df = df.drop(columns=['series'])
        return df
    except Exception as e:
        print(f"Error fetching temperature data: {e}")
        return pd.DataFrame(columns=["timeMs", "ambientTemperature"])

# test = get_historic_temperature(widgetId=278018084915903, startMs=1763100000000, endMs=1763102700000, stepMs=300000)
# print(test)



def get_historic_humidity(widgetId, startMs, endMs, stepMs=300000):
    """Get historic humidity data for a specific sensor"""
    url = "https://api.samsara.com/v1/sensors/history"
    
    payload = {
        "fillMissing": "withPrevious",
        "series": [
            {
                "field": "humidity",
                "widgetId": widgetId
            }
        ],
        "endMs": endMs,
        "startMs": startMs,
        "stepMs": stepMs
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("results"):
            return pd.DataFrame(columns=["timeMs", "humidity"])
        
        df = pd.DataFrame(data["results"])
        df['humidity'] = df['series'].str[0]
        df = df.drop(columns=['series'])
        return df
    except Exception as e:
        print(f"Error fetching humidity data: {e}")
        return pd.DataFrame(columns=["timeMs", "humidity"])

# test = get_historic_humidity(widgetId=278018084915903, startMs=1763100000000, endMs=1763102700000, stepMs=300000)
# print(test)



def get_historic_door(widgetId, startMs, endMs, stepMs=5000):
    """Get historic door status data for a specific sensor"""
    url = "https://api.samsara.com/v1/sensors/history"
    
    payload = {
        "series": [
            {
                "field": "doorClosed",
                "widgetId": widgetId
            }
        ],
        "endMs": endMs,
        "fillMissing": "withPrevious",
        "startMs": startMs,
        "stepMs": stepMs
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("results"):
            return pd.DataFrame(columns=["timeMs", "doorClosed"])
        
        df = pd.DataFrame(data["results"])
        df['doorClosed'] = df['series'].str[0]
        df = df.drop(columns=['series'])
        return df
    except Exception as e:
        print(f"Error fetching door data: {e}")
        return pd.DataFrame(columns=["timeMs", "doorClosed"])

# test = get_historic_door(widgetId=278018084915903, startMs=1763100000000, endMs=1763102700000, stepMs=5000)
# print(test)


def get_current_status(vehicle_id, sensor_config):
    """Get current temperature, humidity, and door status for a vehicle"""
    try:
        status = {
            "temperature": None,
            "humidity": None,
            "door_status": None,
            "last_updated": datetime.now().isoformat()
        }
        
        # Get temperature sensor data
        if sensor_config.get("temperature"):
            temp_sensor_id = sensor_config["temperature"][0]["id"]
            current_time_ms = int(datetime.now().timestamp() * 1000)
            start_time_ms = current_time_ms - 300000  # Last 5 minutes
            
            df_temp = get_historic_temperature(temp_sensor_id, start_time_ms, current_time_ms, stepMs=60000)
            if not df_temp.empty:
                status["temperature"] = df_temp['ambientTemperature'].iloc[-1]
        
        # Get humidity sensor data
        if sensor_config.get("humidity"):
            humidity_sensor_id = sensor_config["humidity"][0]["id"]
            current_time_ms = int(datetime.now().timestamp() * 1000)
            start_time_ms = current_time_ms - 300000
            
            df_humidity = get_historic_humidity(humidity_sensor_id, start_time_ms, current_time_ms, stepMs=60000)
            if not df_humidity.empty:
                status["humidity"] = df_humidity['humidity'].iloc[-1]
        
        # Get door status
        if sensor_config.get("door"):
            door_sensor_id = sensor_config["door"][0]["id"]
            current_time_ms = int(datetime.now().timestamp() * 1000)
            start_time_ms = current_time_ms - 60000  # Last 1 minute
            
            df_door = get_historic_door(door_sensor_id, start_time_ms, current_time_ms, stepMs=5000)
            if not df_door.empty:
                door_closed = df_door['doorClosed'].iloc[-1]
                status["door_status"] = "Closed" if door_closed else "Open"
        
        return status
    except Exception as e:
        print(f"Error getting current status: {e}")
        return None




def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit"""
    if celsius is None:
        return None
    return (celsius * 9/5) + 32

def fahrenheit_to_celsius(fahrenheit):
    """Convert Fahrenheit to Celsius"""
    if fahrenheit is None:
        return None
    return (fahrenheit - 32) * 5/9

def ms_to_datetime(ms):
    """Convert milliseconds since epoch to datetime"""
    return datetime.fromtimestamp(ms / 1000)

def datetime_to_ms(dt):
    """Convert datetime to milliseconds since epoch"""
    return int(dt.timestamp() * 1000)

def calculate_time_range_ms(hours):
    """Calculate start and end time in milliseconds based on hours back"""
    current_time = datetime.now()
    start_time = current_time - pd.Timedelta(hours=hours)
    
    return datetime_to_ms(start_time), datetime_to_ms(current_time)

def get_all_sensors():
    """Get all sensors in the organization"""
    url = "https://api.samsara.com/v1/sensors/list"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }
    
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data["sensors"])
        return df
    except Exception as e:
        print(f"Error fetching sensors: {e}")
        return pd.DataFrame()


def get_current_temperature(widgetId):
    """Get current temperature for a specific sensor

    Args:
        sensor_id: The sensor ID (widgetId) to get temperature for

    Returns:
        dict: Dictionary containing sensor info and current temperature
        Example: {
            'id': 278018088211512,
            'name': '01 - Reefer Temp (Mini fridge)',
            'ambientTemperature': 2539,
            'ambientTemperatureTime': '2025-11-14T10:51:30Z',
            'vehicleId': 281474985231664
        }
    """
    url = "https://api.samsara.com/v1/sensors/temperature"

    payload = {"sensors": [widgetId]}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("sensors") and len(data["sensors"]) > 0:
            return data["sensors"][0]
        else:
            print(f"No temperature data found for sensor {widgetId}")
            return None
    except Exception as e:
        print(f"Error fetching current temperature: {e}")
        return None

# test = get_current_temperature(278018088211512)
# print(test)


def get_current_door_status(widgetId):
    """Get current door status for a specific sensor

    Args:
        sensor_id: The sensor ID (widgetId) to get door status for

    Returns:
        dict: Dictionary containing sensor info and current door status
        Example: {
            'id': 278018089917378,
            'name': '01 - Reefer Door (Mini fridge)',
            'doorClosed': True,
            'doorStatusTime': '2025-11-14T10:52:50Z',
            'vehicleId': 281474985231664
        }
    """
    url = "https://api.samsara.com/v1/sensors/door"

    payload = {"sensors": [widgetId]}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {SAMSARA_API}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("sensors") and len(data["sensors"]) > 0:
            return data["sensors"][0]
        else:
            print(f"No door status data found for sensor {widgetId}")
            return None
    except Exception as e:
        print(f"Error fetching current door status: {e}")
        return None

# test = get_current_door_status(278018089917378)
# print(test)