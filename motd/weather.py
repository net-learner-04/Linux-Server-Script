import requests, dotenv, os
from pathlib import Path

dotenv.load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.getenv("WEATHER_API_KEY")
CITY_NAME = os.getenv("WEATHER_CITY_NAME")
LANGUAGE = "en"
UNITS = "metric"

URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={API_KEY}&lang={LANGUAGE}&units={UNITS}"


def get_weather():
    '''Calls the OpenWeatherMap API to fetch current weather data.
    Returns (weather, temp, feels_like, humidity) on success, or (None, None, None, None) on failure.'''
    try:
        response = requests.get(url=URL, timeout=3)

        if response.status_code == 200:
            data = response.json()

            weather = data["weather"][0]["main"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]

            return weather, temp, feels_like, humidity
        else:
            print(f"An error occurred. Status code: {response.status_code}")
            print(f"Please check that the API key is correct and that the city name is correct.")

            return None, None, None, None
    except requests.exceptions.ConnectionError as e:
        print(f"Network Connection Error: {e}")
        return None, None, None, None
    except requests.exceptions.Timeout as e:
        print(f"The server is too busy, or the network connection is poor: {e}")
        return None, None, None, None
