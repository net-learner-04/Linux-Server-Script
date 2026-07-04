import logging as log
import threading as thr
import psutil, os, time, re

from config import THRESHOLDS


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

    t1.join()
    t2.join()

    cpu_usage = psutil.cpu_percent(interval=3)
    memory_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    tx_mbytes, rx_mbytes = result["network"]
    hdd_read, hdd_write, ssd_read, ssd_write = result["disk"]
    zombie_count = count_zombie_process()
    fd_usage = file_descriptor_check()
    swap_usage = psutil.swap_memory().percent
    temps = temperatures_check()

    if cpu_usage > THRESHOLDS["cpu"]:
        warn_list.append(f"CPU_USAGE: {cpu_usage:.1f}")
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
    if zombie_count > THRESHOLDS["zombie"]:
        warn_list.append(f"ZOMBIE_PROCESS: {zombie_count}")
    if fd_usage > THRESHOLDS["file_descriptor"]:
        warn_list.append(f"FILE_DESCRIPTOR: {fd_usage}")
    if swap_usage > THRESHOLDS["swap"]:
        warn_list.append(f"SWAP: {swap_usage}")
    if temps is not None:
        max_sensor_name, max_temp = temps
        if max_temp > THRESHOLDS["temp"]:
            warn_list.append(f"TEMPERATURE ({max_sensor_name}): {max_temp}")
    
    return warn_list


def return_disks():
    disks = set()
    
    for disk in psutil.disk_partitions():
        device = os.path.basename(disk.device)
        match = re.match(r"(nvme\d+n\d+|[a-z]+)", device)
        if match:
            disks.add(match.group(1))
            
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


def file_descriptor_check():
    '''A function that returns the system-wide file descriptor usage rate as a percentage.'''
    path = "/proc/sys/fs/file-nr"
    with open(path, mode="r") as file:
        contents = file.read().split()
        usage = 0.0
        try:
            usage = int(contents[0]) / int(contents[2]) * 100
        except ZeroDivisionError as e:
            log.error(f"Error Calculating File Descriptor Usage: {e}")
    return usage 


def count_zombie_process():
    '''A function that returns the number of zombie processes on the server.'''
    count = 0
    for process in psutil.process_iter():
        try:
            if process.status() == "zombie":
                count += 1
        except psutil.NoSuchProcess:
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