import logging as log
import threading as thr
import subprocess as sub
import datetime as dt
import ssl, socket
import psutil, os, time, re, shutil

from config import (
    THRESHOLDS, SERVICES, TOP_PROCESS_COUNT,
    SSL_DOMAINS, SSL_EXPIRY_WARNING_DAYS,
    DISK_TREND_WINDOW_DAYS, DISK_TREND_ALERT_DAYS,
    LOAD_AVG_THRESHOLDS, LISTENING_PORTS, SECURITY_UPDATE_WARNING_COUNT,
)
import db


SYSTEMCTL_BIN = shutil.which("systemctl") or "/usr/bin/systemctl"


def classify_severity(value, thresholds):
    '''Function that returns "critical", "warning", or None for a value against a threshold dict.'''
    if value > thresholds["critical"]:
        return "critical"
    if value > thresholds["warning"]:
        return "warning"
    return None


def top_processes(sort_by="cpu", n=TOP_PROCESS_COUNT):
    '''Function that returns the top N processes sorted by CPU or memory usage.
    Note: this samples each process with a short blocking interval for an accurate
    CPU reading, so it should only be called when an alert is about to fire.'''
    procs = []
    for process in psutil.process_iter(["pid", "name"]):
        try:
            cpu = process.cpu_percent(interval=0.05)
            mem = process.memory_percent()
            procs.append({"pid": process.pid, "name": process.info["name"], "cpu": cpu, "mem": mem})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    key = "cpu" if sort_by == "cpu" else "mem"
    procs.sort(key=lambda p: p[key], reverse=True)
    return procs[:n]


def format_top_processes(sort_by="cpu"):
    '''Function that formats the top processes into a short human-readable block.'''
    lines = [
        f"  {p['name']} (pid {p['pid']}): cpu {p['cpu']:.1f}% / mem {p['mem']:.1f}%"
        for p in top_processes(sort_by)
    ]
    return "\n".join(lines) if lines else "  (no process data)"


def server_status_check():
    '''Use `psutil` to check CPU, memory, and disk usage
    and determine whether they exceed a threshold (e.g., 85%)'''
    warn_list = []
    result = {}

    def wrapper_network():
        try:
            result["network"] = network_traffic_check()
        except Exception as e:
            log.error(f"Network check failed: {e}")
            result["network"] = (0.0, 0.0)

    def wrapper_disk():
        try:
            result["disk"] = disk_io_check()
        except Exception as e:
            log.error(f"Disk IO check failed: {e}")
            result["disk"] = (0.0, 0.0, 0.0, 0.0)

    t1 = thr.Thread(target=wrapper_network)
    t2 = thr.Thread(target=wrapper_disk)

    t1.start()
    t2.start()

    cpu_usage = psutil.cpu_percent(interval=3)

    t1.join()
    t2.join()

    memory_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    tx_mbytes, rx_mbytes = result["network"]
    hdd_read, hdd_write, ssd_read, ssd_write = result["disk"]
    zombie_count = count_zombie_process()
    fd_usage = file_descriptor_check()
    swap_usage = psutil.swap_memory().percent
    temps = temperatures_check()

    def add_warning(key, value, thresholds, unit="", extra=""):
        severity = classify_severity(value, thresholds)
        if severity:
            formatted = f"{value:.1f}" if isinstance(value, float) else f"{value}"
            message = f"{key}: {formatted}{unit}"
            if extra:
                message += f"\n{extra}"
            warn_list.append({"key": key, "message": message, "severity": severity})

    add_warning("CPU_USAGE", cpu_usage, THRESHOLDS["cpu"], "%",
                extra=format_top_processes("cpu") if classify_severity(cpu_usage, THRESHOLDS["cpu"]) == "critical" else "")
    add_warning("MEMORY_USAGE", memory_usage, THRESHOLDS["memory"], "%",
                extra=format_top_processes("mem") if classify_severity(memory_usage, THRESHOLDS["memory"]) == "critical" else "")
    add_warning("DISK_USAGE", disk_usage, THRESHOLDS["disk"], "%")
    add_warning("TX_MBYTES", tx_mbytes, THRESHOLDS["tx"], " MB/s")
    add_warning("RX_MBYTES", rx_mbytes, THRESHOLDS["rx"], " MB/s")
    add_warning("HDD_READ", hdd_read, THRESHOLDS["hdd_read"], " MB/s")
    add_warning("HDD_WRITE", hdd_write, THRESHOLDS["hdd_write"], " MB/s")
    add_warning("SSD_READ", ssd_read, THRESHOLDS["ssd_read"], " MB/s")
    add_warning("SSD_WRITE", ssd_write, THRESHOLDS["ssd_write"], " MB/s")
    add_warning("ZOMBIE_PROCESS", zombie_count, THRESHOLDS["zombie"])
    add_warning("FILE_DESCRIPTOR", fd_usage, THRESHOLDS["file_descriptor"], "%")
    add_warning("SWAP", swap_usage, THRESHOLDS["swap"], "%")

    if temps is not None:
        max_sensor_name, max_temp = temps
        severity = classify_severity(max_temp, THRESHOLDS["temp"])
        if severity:
            warn_list.append({
                "key": f"TEMPERATURE_{max_sensor_name}",
                "message": f"TEMPERATURE ({max_sensor_name}): {max_temp}",
                "severity": severity,
            })

    return warn_list


def service_status_check():
    '''Function to check the status of essential services (httpd, nginx, sshd, etc.)'''
    warn_list = []

    for service in SERVICES:
        try:
            # sub.DEVNULL : Hide Terminal std Output
            is_active = sub.run(
                [SYSTEMCTL_BIN, "is-active", service],
                stdout=sub.DEVNULL, stderr=sub.DEVNULL
            )
            if is_active.returncode != 0:
                log.warning(f"The {service} is currently disabled. Attempting to restart...")
                restart = sub.run(
                    [SYSTEMCTL_BIN, "restart", service],
                    stdout=sub.DEVNULL, stderr=sub.DEVNULL, timeout=15
                )
                if restart.returncode == 0:
                    log.info(f"The {service} restart success.")
                    warn_list.append({
                        "key": f"SERVICE_{service}",
                        "message": f"SERVICE: {service} -> Automatic restart successful.",
                        "severity": "warning",
                    })
                else:
                    log.error(f"The {service} restart failed.")
                    warn_list.append({
                        "key": f"SERVICE_{service}",
                        "message": f"SERVICE: {service} -> Automatic restart failed.",
                        "severity": "critical",
                    })
        except sub.TimeoutExpired:
            log.error(f"systemctl restart timed out for {service}.")
            warn_list.append({
                "key": f"SERVICE_{service}",
                "message": f"SERVICE: {service} -> Restart command timed out.",
                "severity": "critical",
            })
        except FileNotFoundError as e:
            log.error(f"systemctl not found while checking {service}: {e}")
            warn_list.append({
                "key": f"SERVICE_{service}",
                "message": f"SERVICE: {service} -> systemctl not found (check PATH).",
                "severity": "critical",
            })
        except PermissionError as e:
            log.error(f"Permission denied while restarting {service}: {e}")
            warn_list.append({
                "key": f"SERVICE_{service}",
                "message": f"SERVICE: {service} -> Permission denied (needs root/sudo).",
                "severity": "critical",
            })

    return warn_list


def ssl_expiry_check():
    '''Function that checks TLS certificate expiry for the domains listed in SSL_DOMAINS
    and returns alert items for certificates expiring within SSL_EXPIRY_WARNING_DAYS.'''
    warn_list = []
    ctx = ssl.create_default_context()

    for domain in SSL_DOMAINS:
        try:
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

            expires = dt.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
            days_left = (expires - dt.datetime.utcnow()).days

            if days_left <= 0:
                warn_list.append({
                    "key": f"SSL_{domain}",
                    "message": f"SSL_EXPIRED: {domain} certificate has expired.",
                    "severity": "critical",
                })
            elif days_left <= SSL_EXPIRY_WARNING_DAYS:
                warn_list.append({
                    "key": f"SSL_{domain}",
                    "message": f"SSL_EXPIRING: {domain} expires in {days_left} day(s).",
                    "severity": "warning",
                })
        except Exception as e:
            log.error(f"SSL check failed for {domain}: {e}")
            warn_list.append({
                "key": f"SSL_{domain}_ERROR",
                "message": f"SSL_CHECK_FAILED: {domain} -> {e}",
                "severity": "warning",
            })

    return warn_list


def disk_trend_check():
    '''Function that records the current disk usage sample and, using recent history,
    predicts whether the disk will fill up within DISK_TREND_ALERT_DAYS.'''
    current = psutil.disk_usage('/').percent
    db.record_metric("disk_usage", current)

    history = db.get_metric_history("disk_usage", DISK_TREND_WINDOW_DAYS)
    if len(history) < 2:
        return []

    first_time = dt.datetime.fromisoformat(history[0][0])
    last_time = dt.datetime.fromisoformat(history[-1][0])
    elapsed_days = (last_time - first_time).total_seconds() / 86400
    if elapsed_days <= 0:
        return []

    growth_per_day = (history[-1][1] - history[0][1]) / elapsed_days
    if growth_per_day <= 0:
        return []

    days_until_full = (100.0 - current) / growth_per_day
    if days_until_full <= DISK_TREND_ALERT_DAYS:
        return [{
            "key": "DISK_TREND",
            "message": f"DISK_TREND: usage growing {growth_per_day:.2f}%/day, "
                       f"projected to fill in ~{days_until_full:.1f} day(s).",
            "severity": "warning",
        }]

    return []


def load_average_check():
    '''Function that checks the 1-minute load average against a multiple of CPU core count.
    A normalized value > 1.0 means the system has more runnable processes than cores.'''
    warn_list = []
    try:
        load1, _, _ = psutil.getloadavg()
    except (AttributeError, OSError) as e:
        log.warning(f"Load average not available on this platform: {e}")
        return warn_list

    core_count = psutil.cpu_count() or 1
    normalized = load1 / core_count

    severity = classify_severity(normalized, LOAD_AVG_THRESHOLDS)
    if severity:
        warn_list.append({
            "key": "LOAD_AVERAGE",
            "message": f"LOAD_AVERAGE: {load1:.2f} (1min) / {core_count} cores = {normalized:.2f}x",
            "severity": severity,
        })

    return warn_list


def inode_usage():
    '''A function that returns the root filesystem inode usage rate as a percentage.'''
    stats = os.statvfs('/')
    total_inodes = stats.f_files
    free_inodes = stats.f_ffree

    if total_inodes == 0:
        log.warning("Filesystem reports zero total inodes, skipping inode check.")
        return 0.0

    return (total_inodes - free_inodes) / total_inodes * 100


def listening_port_check():
    '''Function that checks whether the expected ports (config.LISTENING_PORTS)
    are currently in LISTEN state. Catches cases where a service is running
    but failed to bind, or a firewall/config change closed the port.'''
    warn_list = []

    try:
        connections = psutil.net_connections(kind="inet")
    except psutil.AccessDenied as e:
        log.warning(f"Cannot read network connections (needs root?): {e}")
        return warn_list

    listening_ports = {c.laddr.port for c in connections if c.status == psutil.CONN_LISTEN}

    for port in LISTENING_PORTS:
        if port not in listening_ports:
            warn_list.append({
                "key": f"PORT_{port}",
                "message": f"PORT_NOT_LISTENING: expected port {port} is not open.",
                "severity": "critical",
            })

    return warn_list


def security_updates_check():
    '''Function that counts pending security updates on RHEL-family systems.
    Returns None if dnf/yum is not available (e.g. non-RHEL-family distro), so callers can
    distinguish "not applicable" from "zero updates".'''
    pkg_bin = shutil.which("dnf") or shutil.which("yum")
    if not pkg_bin:
        return None

    try:
        result = sub.run(
            [pkg_bin, "check-update", "--security", "--quiet"],
            stdout=sub.PIPE, stderr=sub.DEVNULL, timeout=60, text=True
        )
        # dnf/yum exit codes: 0 = no updates, 100 = updates available, 1 = error
        if result.returncode not in (0, 100):
            log.error(f"{pkg_bin} check-update exited with unexpected code {result.returncode}")
            return None

        # Each upgradable package is listed on its own line as "name  version  repo"
        lines = [line for line in result.stdout.splitlines() if line.strip() and not line.startswith(("Last metadata", "Security:"))]
        return len(lines)
    except sub.TimeoutExpired as e:
        log.error(f"Security update check timed out: {e}")
        return None
    except Exception as e:
        log.error(f"Security update check failed: {e}")
        return None


def security_updates_alert_check():
    '''Function that wraps security_updates_check() into an alert item
    when the pending count exceeds the configured warning threshold.'''
    warn_list = []
    count = security_updates_check()

    if count is None:
        return warn_list

    if count >= SECURITY_UPDATE_WARNING_COUNT:
        warn_list.append({
            "key": "SECURITY_UPDATES",
            "message": f"SECURITY_UPDATES: {count} pending security update(s).",
            "severity": "warning",
        })

    return warn_list


def return_disks():
    '''Return the names of physical disk devices with mounted partitions.'''
    disks = set()

    for disk in psutil.disk_partitions():
        device = os.path.basename(disk.device)
        match = re.match(r"(nvme\d+n\d+|[a-z]+)", device)
        if not match:
            continue

        base = match.group(1)

        if not os.path.exists(f"/sys/block/{base}/device"):
            continue

        disks.add(base)

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
        rotational_path = f"/sys/block/{disk}/queue/rotational"
        if not os.path.exists(rotational_path):
            continue
        with open(rotational_path, mode="r") as file:
            rotational = file.read().strip()
            if rotational == "0":
                disk_type[disk] = "ssd"
            elif rotational == "1":
                disk_type[disk] = "hdd"

    before = psutil.disk_io_counters(perdisk=True)
    time.sleep(wait_time)
    after = psutil.disk_io_counters(perdisk=True)

    for disk, dtype in disk_type.items():
        if disk not in before or disk not in after:
            log.warning(f"Disk '{disk}' not found in disk_io_counters, skipping.")
            continue

        read = (max(0, (after[disk].read_bytes - before[disk].read_bytes)) / wait_time) / (1024 ** 2)
        write = (max(0, (after[disk].write_bytes - before[disk].write_bytes)) / wait_time) / (1024 ** 2)

        if dtype == "hdd":
            hdd_read += read
            hdd_write += write
        elif dtype == "ssd":
            ssd_read += read
            ssd_write += write

    return hdd_read, hdd_write, ssd_read, ssd_write


def file_descriptor_check():
    '''A function that returns the system-wide file descriptor usage rate as a percentage.'''
    path = "/proc/sys/fs/file-nr"
    usage = 0.0
    with open(path, mode="r") as file:
        contents = file.read().split()
        try:
            usage = int(contents[0]) / int(contents[2]) * 100
        except (ZeroDivisionError, IndexError, ValueError) as e:
            log.error(f"Error Calculating File Descriptor Usage: {e}")
    return usage


def count_zombie_process():
    '''A function that returns the number of zombie processes on the server.'''
    count = 0
    for process in psutil.process_iter():
        try:
            if process.status() == "zombie":
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return count


def temperatures_check():
    '''A function that checks the temperatures of the sensors and returns the highest temperature.'''
    if not hasattr(psutil, "sensors_temperatures"):
        log.warning("Temperature sensors are not supported on this system.")
        return None

    temps = psutil.sensors_temperatures()

    if not temps:
        log.warning("No temperature sensors found.")
        return None

    max_sensor_name, max_temp = max(
        ((name, entry.current)
        for name, entries in temps.items()
        for entry in entries),
        key=lambda x: x[1]
    )

    return max_sensor_name, max_temp


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
