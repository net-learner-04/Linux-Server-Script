import os, csv, dotenv
from pathlib import Path
from display import render
from ascii_art import get_art, get_color
from system import get_uptime, get_dev_info, get_update_number, get_last_login


# Load environment variables from the .env file
dotenv.load_dotenv(Path(__file__).parent / ".env")

# Path to the cached weather log file
LOG_FILE = Path(__file__).parent / "log" / "weather_log.csv"


def get_cached_weather():
    """Reads the last row (latest data) from the cached CSV log file."""
    default_data = {"weather": "Unknown", "temp": "-", "feels_like": "-", "humidity": "-"}
    
    if not LOG_FILE.is_file():
        return default_data

    try:
        with open(LOG_FILE, mode="r", encoding="utf-8") as file:
            reader = list(csv.reader(file))
            if len(reader) > 1:  # Check if there is data beyond the header row
                last_row = reader[-1]  # Get the most recent row
                
                # Index starts from 1 because index 0 is the timestamp
                return {
                    "weather": last_row[1],
                    "temp": last_row[2],
                    "feels_like": last_row[3],
                    "humidity": last_row[4]
                }
    except Exception as e:
        print(f"Failed to read cached weather data: {e}")
        
    return default_data


# Fetch weather data from the local cache instead of making a direct API call
weather_data = get_cached_weather()

# Fetch current system information
uptime, _ = get_uptime()
cpu, memory, disk = get_dev_info()
update_status = get_update_number()
last_login = get_last_login()

system_data = {
    "uptime": uptime, "cpu": cpu, "memory": memory, "disk": disk,
    "update_status": update_status, "last_login": last_login,
}

# Setup visual assets and render the dashboard
art = get_art()
color = get_color()
city_name = os.getenv("WEATHER_CITY_NAME")

render(art, color, weather_data, system_data, city_name)
