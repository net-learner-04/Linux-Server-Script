import os, pynvml

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
