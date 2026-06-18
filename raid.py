import subprocess as sub
import json, psutil, os, shutil, syslog, sys

def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        syslog.syslog(syslog.LOG_ERR, "Run as root.")
        sys.exit(os.EX_NOPERM)

def check_device():
    '''A function that selects a RAID target by checking the list of device blocks
    in the current system and filtering out disks that 
    do not have partitions or file systems'''
    lsblk_list = sub.run(["lsblk", "-J", "-O"], capture_output=True, text=True).stdout
    lsblk_json = json.loads(lsblk_list)
    blkid_list = sub.run(["blkid"], capture_output=True, text=True).stdout

    device_names = []
    return_list = []

    for value in lsblk_json["blockdevices"]:
        if (value.get("children") == None) and (value.get("fstype") == None) and (value.get("type") == "disk"):
            device_names.append(value["name"])
    
    for i in range(len(device_names)):
        found = False
        for line in blkid_list.splitlines():
            dev, info = line.split(":")
            if device_names[i] in dev:
                found = True
                break
        if found == False:
            return_list.append(device_names[i])

    return return_list


def status_check(device_list):
    '''A function that checks whether the disk is currently mounted'''
    partition_list = psutil.disk_partitions(all=True)
    return_list = []

    for i in range(len(device_list)):
        found = False
        for part_dev in partition_list:
            if device_list[i] in part_dev.device:
                found = True
                break
        if found == False:
            return_list.append(device_list[i])
        
    return return_list


def mdadm_check():
    '''Function to check if the mdadm package is installed'''
    result = sub.run(["rpm", "-q", "mdadm"]).returncode
    if result != 0:
        try:
            sub.run(["dnf", "install", "-y", "mdadm"], check=True)
        except sub.CalledProcessError as e:
            syslog.syslog(syslog.LOG_ERR, f"An error occurred during installation. Return code: {e.returncode}")


def start():
    status_check(check_device)
    mdadm_check()


if __name__ == "__main__":
    start()
    syslog.closelog()
