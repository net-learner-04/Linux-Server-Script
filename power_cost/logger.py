import csv
from datetime import datetime
from pathlib import Path
import config
import power

def create_daily_log_file():
    """Create today's CSV log file with headers if it doesn't already exist, and return its path."""
    file_path = Path(f"{config.DIR_PATH}/{datetime.now().strftime('%Y-%m-%d')}.csv")

    if not config.DIR_PATH.is_dir():
        config.DIR_PATH.mkdir(parents=True, exist_ok=True)
    
    if not file_path.is_file():
        file_path.touch()
        with open(file_path, mode="w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "uptime", "electrical_energy", "method"])
    
    return file_path


def write_log(file_path, method):
    """Append a single timestamped power/uptime reading to the given log file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    uptime = power.get_uptime()
    electrical_energy = power.get_instant_power(method)
    
    with open(file_path, mode="a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, uptime, electrical_energy, method])
