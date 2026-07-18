# External Python modules (download required)
import psutil, pynvml, dotenv
# Built-in Python Modules
import os, time, csv, calendar, requests, sys
from datetime import datetime, date
from pathlib import Path


dotenv.load_dotenv(Path(__file__).parent / ".env")

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

if WEBHOOK_URL is None:
    print("DISCORD_WEBHOOK is not configured in .env")
    sys.exit(os.EX_NOINPUT)

# Input your CPU's Idle Power (ex: Intel N150)
IDLE = 2.2

#  Input your CPU's Maximum Load Power (100% sustained) (ex: Intel N150)
LOAD = 6.1

# directory path
DIR_PATH = Path(__file__).parent / "power_cost_logs"

# Use the actual average unit price 
# from your most recent electricity bill.
# based on Korean standards
RATE_PER_KWH = 250


def detect_cpu_vendor():
    """Return 'intel', 'amd', or None based on /proc/cpuinfo vendor_id."""
    dev_info = dict()

    with open("/proc/cpuinfo", mode="r", encoding="utf-8") as file:
        for line in file:
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            dev_info[key.strip()] = value.strip()

    if dev_info.get("vendor_id") == "GenuineIntel":
        return "intel"
    elif dev_info.get("vendor_id") == "AuthenticAMD":
        return "amd"
    else:
        return None


def check_rapl():
   """Check whether the Intel RAPL energy_uj file exists and is readable."""
    file_path = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"

    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
        return True
    return False


def check_gpu():
    """Check whether an NVIDIA GPU is present and accessible via NVML."""
    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        pynvml.nvmlShutdown()
        return count > 0
    except Exception:
        return False


def detect_power_method():
    """Determine the best available power measurement method for this system."""
    vendor = detect_cpu_vendor()
    gpu_available = check_gpu()

    if vendor == "intel" and check_rapl():
        base_method = "rapl"
    else:
        base_method = "estimated"

    if gpu_available:
        return base_method + "_plus_gpu"
    else:
        return base_method


def get_uptime():
    """Return system uptime in seconds since boot."""
    return float(datetime.now().timestamp() - psutil.boot_time())


def get_rapl_power():
    """Measure average CPU package power (W) over a 1-second interval using RAPL."""
    file_path = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"

    try:
        with open(file_path, mode="r", encoding="utf-8") as file:
            time_1 = time.monotonic()
            aec_1 = int(file.read())

        time.sleep(1)

        with open(file_path, mode="r", encoding="utf-8") as file:
            time_2 = time.monotonic()
            aec_2 = int(file.read())

        diff = aec_2 - aec_1
        if diff < 0:
            # If the counter overflows and resets, the current measurement value is discarded.
            return None

        return diff / 1_000_000 / (time_2 - time_1)

    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"Failed to Read RAPL: {e}")
        return None


def get_gpu_power():
    """Return the current GPU power draw in watts via NVML."""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mw = pynvml.nvmlDeviceGetPowerUsage(handle)
        pynvml.nvmlShutdown()
        # mW -> W
        return mw / 1000
    except Exception as e:
        print(f"Failed to read GPU power: {e}")
        return 0


def get_estimated_power():
    """Estimate instantaneous power (W) by interpolating between IDLE and LOAD based on CPU usage."""
    cpu_percent = psutil.cpu_percent(interval=1)
    return IDLE + (LOAD - IDLE) * (cpu_percent / 100)


def get_instant_power(method):
    """Return the current instantaneous power draw (W) using the given measurement method."""
    if method == "rapl":
        return get_rapl_power()
    elif method == "rapl_plus_gpu":
        rapl = get_rapl_power()
        return rapl + get_gpu_power() if rapl is not None else None
    elif method == "estimated":
        return get_estimated_power()
    elif method == "estimated_plus_gpu":
        return get_estimated_power() + get_gpu_power()
    

def create_daily_log_file():
    """Create today's CSV log file with headers if it doesn't already exist, and return its path."""
    file_path = Path(f"{DIR_PATH}/{datetime.now().strftime('%Y-%m-%d')}.csv")

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
        

def parse_logs():
    """Aggregate this month's logs into total uptime (s) and total energy consumption (Wh)."""
    csv_files = DIR_PATH.glob("*.csv")
    total_uptime = 0.0
    total_wh = 0.0
    today = date.today()

    for file_path in csv_files:
        try:
            file_date_obj = datetime.strptime(file_path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue

        if file_date_obj.year != today.year or file_date_obj.month != today.month:
            continue

        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Header Skip
            next(reader)

            rows = list(reader)
            if not rows:
                continue

            day_uptimes = [float(row[1]) for row in rows]
            total_uptime += max(day_uptimes)

            prev_ts = None
            for row in rows:
                ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                power = row[2]

                if prev_ts is not None and power != "":
                    hours = (ts - prev_ts).total_seconds() / 3600
                    total_wh += float(power) * hours

                prev_ts = ts

    return total_uptime, total_wh
        

def calculate_cost(total_wh):
    """Convert total watt-hours into kWh and estimated cost based on RATE_PER_KWH."""
    total_kwh = total_wh / 1000
    cost = total_kwh * RATE_PER_KWH

    return total_kwh, cost


def is_last_day_of_month():
    """Return True if today is the last calendar day of the current month."""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]

    return today.day == last_day


def send_to_discord(total_uptime, total_kwh, cost):
    """Send a monthly usage/cost summary message to the configured Discord webhook."""
    message = (
        f"{date.today().month} Electricity Usage Report\n"
        f"Total Uptime: {total_uptime / 3600:.2f}\n"
        f"Estimated Electricity Consumption: {total_kwh:.3f} kWh\n"
        f"Estimated Electricity Bill: {cost:,.0f} ₩"
    )

    payload = {"content": message}

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Discord Transfer Failed: {e}")


def start():
    method = detect_power_method()
    log_path = create_daily_log_file()
    write_log(log_path, method)

    if is_last_day_of_month():
        total_uptime, total_wh = parse_logs()
        total_kwh, cost = calculate_cost(total_wh)
        send_to_discord(total_uptime, total_kwh, cost)


if __name__ == "__main__":
    print("Start Power Calculation...")
    start()
