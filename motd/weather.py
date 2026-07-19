import requests, dotenv, os, csv
from pathlib import Path
from datetime import datetime

dotenv.load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.getenv("WEATHER_API_KEY")
CITY_NAME = os.getenv("WEATHER_CITY_NAME")
LANGUAGE = "en"
UNITS = "metric"
URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={API_KEY}&lang={LANGUAGE}&units={UNITS}"

DIR_PATH = Path(__file__).parent / "log"
FILE_PATH = DIR_PATH / "weather_log.csv" 


def create_log_file():
    if not DIR_PATH.is_dir():
        DIR_PATH.mkdir(parents=True, exist_ok=True)
    
    if not FILE_PATH.is_file():
        with open(FILE_PATH, mode="w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            # Added timestamp to track when the data was captured
            writer.writerow(["timestamp", "weather", "temp", "feels_like", "humidity"])
    
    return FILE_PATH


def write_log(file_path):
    """Append a single timestamped power/uptime reading to the given log file."""
    weather, temp, feels_like, humidity = get_weather()

    # Skip writing if the API call failed to prevent corrupted cache
    if weather is None:
        print("Skipping log update due to API failure.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Kept as mode="a" to continuously accumulate historical log via cron
    with open(file_path, mode="a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, weather, temp, feels_like, humidity])


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


if __name__ == "__main__":
    log_path = create_log_file()
    write_log(log_path)
