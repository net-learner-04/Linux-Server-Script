import subprocess as sub
import logging as log
import datetime as dt
import psutil, requests, os, dotenv, sys, time


dotenv.load_dotenv()

NOWDATE = dt.datetime.now().strftime("%Y-%m-%d")

# List of Thresholds 
THRESHOLDS = {
    "cpu": 85.0,
    "memory": 80.0,
    "disk": 75.0,
    "tx": 30.0,
    "rx": 50.0,
    "hdd_read": 60.0,
    "hdd_write": 40.0,
    "ssd_read": 200.0,
    "ssd_write": 150.0,
}

# Adjust according to your server environment.
SERVICES = ["nginx", "sshd", "httpd"]

# minutes
COOLDOWN = 15

ALERTFILE = ".last_alert"

log.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "log", f"{NOWDATE}_server.log"),
    level=log.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.geteuid() != 0:
        log.critical("Root privilege required to run this script.")
        print("Run as root.")
        sys.exit(os.EX_NOPERM)


def mkdir_log():
    '''A function that creates a log directory.'''
    os.makedirs(os.path.join(os.path.dirname(__file__), "log"), exist_ok=True)


def sever_status_check():
    '''Use `psutil` to check CPU, memory, and disk usage 
    and determine whether they exceed a threshold (e.g., 85%)'''
    warn_list = []

    cpu_usage = psutil.cpu_percent(interval=3)
    memory_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    tx_mbytes, rx_mbytes = network_traffic_check()
    hdd_read, hdd_write, ssd_read, ssd_write = disk_io_check()

    if cpu_usage > THRESHOLDS["cpu"]:
        warn_list.append(f"CPU_USAGE: {cpu_usage}")
    if memory_usage > THRESHOLDS["memory"]:
        warn_list.append(f"MEMORY_USAGE: {memory_usage}")
    if disk_usage > THRESHOLDS["disk"]:
        warn_list.append(f"DISK_USAGE: {disk_usage}")
    if tx_mbytes > THRESHOLDS["tx"]:
        warn_list.append(f"TX_MBYTES: {tx_mbytes}")
    if rx_mbytes > THRESHOLDS["rx"]:
        warn_list.append(f"RX_MBYTES: {rx_mbytes}")
    if hdd_read > THRESHOLDS["hdd_read"]:
        warn_list.append(f"HDD_READ: {hdd_read}")
    if hdd_write > THRESHOLDS["hdd_write"]:
        warn_list.append(f"HDD_WRITE: {hdd_write}")
    if ssd_read > THRESHOLDS["ssd_read"]:
        warn_list.append(f"SSD_READ: {ssd_read}")
    if ssd_write > THRESHOLDS["ssd_write"]:
        warn_list.append(f"SSD_WRITE: {ssd_write}")

    return warn_list


def service_status_check():
    '''Function to check the status of essential services (httpd, nginx, sshd, etc.).'''
    warn_list = []

    for service in SERVICES:
        # sub.DEVNULL : Hide Terminal std Output
        if sub.run(["systemctl", "is-active", service], stdout=sub.DEVNULL, stderr=sub.DEVNULL).returncode != 0:
            log.warning(f"The {service} is currently disabled. Attempting to restart...")
            if sub.run(["systemctl", "restart", service], stdout=sub.DEVNULL, stderr=sub.DEVNULL).returncode == 0:
                log.info(f"The {service} restart success.")
                warn_list.append(f"Detected that the {service} service is down -> Automatic restart successful.")
            else:
                log.error(f"The {service} restart failed.")
                warn_list.append(f"Detected that the {service} service is down -> Automatic restart failed.")

    return warn_list


def return_disks():
    '''A function that returns only the disk names from the disk list.'''
    # Data Structures Without Duplicates
    disks = set()

    for disk in psutil.disk_partitions():
        device = os.path.basename(disk.device).rstrip("0123456789")
        if "nvme" in device:
            nvme = device.rstrip("p")
            disks.add(nvme)
        else:
            disks.add(device)

    return disks


def disk_io_check():
    '''A function that classifies all disks on the server as HDD or SSD 
    and returns their respective read and write speeds in MB/s.'''
    wait_time = 2.0
    disks = return_disks()
    disk_type = {}
    hdd_read = 0
    hdd_write = 0
    ssd_read = 0
    ssd_write = 0

    for disk in disks:
        with open(f"/sys/block/{disk}/queue/rotational", mode="r") as file:
            rotational = file.read().strip()
            if rotational == "0":
                disk_type[disk] = "ssd"
            elif rotational == "1":
                disk_type[disk] = "hdd"

    before = psutil.disk_io_counters(perdisk=True)
    time.sleep(wait_time)
    after = psutil.disk_io_counters(perdisk=True)

    for disk, dtype in disk_type.items():
        read = (max(0, (after[disk].read_bytes - before[disk].read_bytes)) / wait_time) / (1024 ** 2)
        write = (max(0, (after[disk].write_bytes - before[disk].write_bytes)) / wait_time) / (1024 ** 2)

        if dtype == "hdd":
            hdd_read += read
            hdd_write += write
        elif dtype == "ssd":
            ssd_read += read
            ssd_write += write

    return hdd_read, hdd_write, ssd_read, ssd_write


def network_traffic_check():
    '''A function that compares the transmitted and received bytes, 
    converts the result to MB/s, and returns it.'''
    wait_time = 2.0

    before = psutil.net_io_counters()
    time.sleep(wait_time)
    after = psutil.net_io_counters()
    
    tx = (max(0, (after.bytes_sent - before.bytes_sent)) / wait_time) / (1024 ** 2)
    rx = (max(0, (after.bytes_recv - before.bytes_recv)) / wait_time) / (1024 ** 2)

    return tx, rx


def last_alert_check():
    '''A function to check the last time a Discord notification was sent.'''
    if not os.path.exists(ALERTFILE):
        return True
    
    with open(ALERTFILE) as file:
        last = dt.datetime.fromisoformat(file.read().strip())
    return (dt.datetime.now() - last).total_seconds() / 60 >= COOLDOWN


def update_last_alert():
    '''Function to update the last transmission time.'''
    with open(ALERTFILE, mode="w") as file:
        file.write(f"{dt.datetime.now().isoformat()}\n") 


def discord_format(warn_list):
    '''A function that defines the Discord transmission format.'''
    fields = [{"name": item.split(":")[0], "value": f"`{item}`", "inline": False} for item in warn_list]
    
    embed = {
        "title": "SERVER MONITORING REPORT",
        "description": f"Detected **{len(warn_list)}** issue(s) requiring attention.",
        "color": 0xC0392B,
        "fields": fields,
        "footer": {
            "text": f"Reported at {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }

    return {"embeds": [embed]}


def send_message(message):
    '''A function that sends messages to a Discord server based on a defined format.'''
    web_hook = os.getenv("DISCORD_WEBHOOK")

    if not web_hook:
        print("There is no 'DISCORD_WEBHOOK' setting in the .env file.")
        sys.exit(os.EX_NOINPUT)

    try:
        req = requests.post(web_hook, json=message, timeout=10)
        if req.status_code in (200, 204):
            log.info("Discord notification sent successfully.")
        else:
            log.error(f"Discord notification send failed  (status code: {req.status_code})")
    except requests.exceptions.RequestException as e:
        log.error(f"Discord request exception occurred: {e}")


def start():
    root_check()
    mkdir_log()
    system_warn_list = sever_status_check()
    service_warn_list = service_status_check()
    errors = system_warn_list + service_warn_list
    if len(errors) > 0:
        if last_alert_check():
            format_message = discord_format(errors)
            send_message(format_message)
            update_last_alert()


if __name__ == "__main__":
    log.info("Start the system monitoring process.")
    start()
