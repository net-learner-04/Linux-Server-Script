import time, os, psutil, pynvml
from datetime import datetime
import config
import hardware

def detect_power_method():
    """Determine the best available power measurement method for this system."""
    vendor = hardware.detect_cpu_vendor()
    gpu_available = hardware.check_gpu()

    if vendor == "intel" and hardware.check_rapl():
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
    return config.IDLE + (config.LOAD - config.IDLE) * (cpu_percent / 100)


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


def calculate_cost(total_wh):
    """Convert total watt-hours into kWh and estimated cost based on RATE_PER_KWH."""
    total_kwh = total_wh / 1000
    cost = total_kwh * config.RATE_PER_KWH

    return total_kwh, cost
