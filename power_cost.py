# External Python modules (download required)
import psutil, pynvml
# Built-in Python Modules
import os, pathlib, time, glob, csv
from datetime import datetime

# Input your CPU's Idle Power
IDLE = 0

# Input your CPU's Maximum Load Power
LOAD = 0


def detect_cpu_vendor():
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
    file_path = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"

    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
        return True
    return False


def check_gpu():
    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        pynvml.nvmlShutdown()
        return count > 0
    except Exception:
        return False


def detect_power_method():
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
    return float(datetime.now().timestamp() - psutil.boot_time())


def get_rapl_power():
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
    cpu_percent = psutil.cpu_percent(interval=1)
    return IDLE + (LOAD - IDLE) * (cpu_percent / 100)


def get_instant_power(method):
    if method == "rapl":
        return get_rapl_power()
    elif method == "rapl_plus_gpu":
        rapl = get_rapl_power()
        return rapl + get_gpu_power() if rapl is not None else None
    elif method == "estimated":
        return get_estimated_power()
    elif method == "estimated_plus_gpu":
        return get_estimated_power() + get_gpu_power()
    

def create_daily_log():
    pass


def write_log():
    pass


def parse_logs():
    pass


def calculate_cost():
    pass
