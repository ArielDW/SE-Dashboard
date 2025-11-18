# Reefer Monitoring Solution

This is a Streamlit application designed to monitor temperatures and door statuses of reefers (refrigerated vehicles). It provides both current and historical data visualization.

## Features

- Real-time display of temperature and door status.
- Historical temperature charts with door event overlays.
- Customizable time ranges and temperature units.
- Threshold violation alerts for temperature.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dashboard-l8.streamlit.app/)

## How to Run

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure API Key:**
    Update the `SAMSARA_API` variable in the `functions.py` file with your Samsara API Token.

3.  **Run the Application:**
    ```bash
    streamlit run streamlit_app.py
    ```
