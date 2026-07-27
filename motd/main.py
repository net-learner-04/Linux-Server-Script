import os, dotenv
from pathlib import Path
from display import render, get_ascii_art_color, get_ascii_art
from system import get_uptime, get_dev_info, get_update_number, get_last_login, get_device_info
from weather import get_weather

# Load environment variables from the .env file
dotenv.load_dotenv(Path(__file__).parent / ".env")


def fetch_weather():
    """Fetches current weather data directly from the OpenWeatherMap API."""
    weather, temp, feels_like, humidity = get_weather()
    if weather is None:
        return {"weather": "Unknown", "temp": "-", "feels_like": "-", "humidity": "-"}
    return {
        "weather": weather,
        "temp": temp,
        "feels_like": feels_like,
        "humidity": humidity,
    }


# Fetch weather data directly from the API
weather_data = fetch_weather()

# Fetch current system information
uptime, _ = get_uptime()
cpu, memory, disk = get_dev_info()
update_status = get_update_number()
last_login = get_last_login()
kernel, os_name, hostname, username = get_device_info()

system_data = {
    "uptime": uptime, "cpu": cpu, "memory": memory, "disk": disk,
    "update_status": update_status, "last_login": last_login,
    "kernel": kernel, "os_name": os_name, "hostname": hostname,
    "username": username,
}

# Setup visual assets and render the dashboard
art = get_ascii_art()
color = get_ascii_art_color()
city_name = os.getenv("WEATHER_CITY_NAME")

render(art, color, weather_data, system_data, city_name)
