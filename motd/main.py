from display import render
from ascii_art import get_weather_art
from weather import get_weather
from system import get_uptime, get_dev_info, get_update_number, get_last_login
import os

weather, temp, feels_like, humidity = get_weather()
weather_data = {"weather": weather, "temp": temp, "feels_like": feels_like, "humidity": humidity}

uptime, _ = get_uptime()
cpu, memory, disk = get_dev_info()
update_status = get_update_number()
last_login = get_last_login()

system_data = {
    "uptime": uptime, "cpu": cpu, "memory": memory, "disk": disk,
    "update_status": update_status, "last_login": last_login,
}

art = get_weather_art(weather)
city_name = os.getenv("WEATHER_CITY_NAME")

render(art, weather_data, system_data, city_name)
