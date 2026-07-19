# Built-in Python Modules
import csv
from datetime import datetime
from config import DIR_PATH
from power import get_uptime, get_instant_power


def create_daily_log_file():
    """Create today's CSV log file with headers if it doesn't already exist, and return its path."""
    file_path = DIR_PATH / f"{datetime.now().strftime('%Y-%m-%d')}.csv"

    if not DIR_PATH.is_dir():
        DIR_PATH.mkdir(parents=True, exist_ok=True)

    if not file_path.is_file():
        file_path.touch()
        with open(file_path, mode="w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "uptime", "electrical_energy", "method"])

    return file_path


def write_log(file_path, method):
    """Append a single timestamped power/uptime reading to the given log file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    uptime = get_uptime()
    electrical_energy = get_instant_power(method)

    with open(file_path, mode="a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, uptime, electrical_energy, method])
