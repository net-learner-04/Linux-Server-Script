import subprocess as sub
import json, psutil, os, pathlib, syslog, sys


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
            dev, info = line.split(":", 1)
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


def raid_name(raid_level):
    '''Function to create a RAID device name.'''
    count = 0
    name = ""
    while True:
        if os.path.exists(f"/dev/md{raid_level}{count}"):
            count += 1
        else:
            name = f"/dev/md{raid_level}{count}"
            break
    
    return name


def input_raid_level():
    '''A function that retrieves the desired RAID level from the user.'''
    raid_level = input("Choose your raid level (0, 1, 5, 6, 10): ")
    return raid_level


def raid_level_select(device_list, device_name, raid_level):
    '''A function that creates a RAID array using the `mdadm` command 
    after verifying the minimum number of disks required 
    for each RAID level (RAID 0, 1, 5, 6, 10).'''
    raid_disks = {"0": 2, "1": 2, "5": 3, "6": 4, "10": 4}

    if raid_level not in raid_disks.keys():
        syslog.syslog(syslog.LOG_WARNING, f"{raid_level} is an invalid value.")
        sys.exit(os.EX_NOINPUT)

    if raid_disks[raid_level] > len(device_list):
        syslog.syslog(syslog.LOG_WARNING, f"Insufficient number of disks required for RAID Level {raid_level}")
        sys.exit(os.EX_UNAVAILABLE)
    
    dev_list = [f"/dev/{d}" for d in device_list]
    disks = dev_list

    try:
        sub.run(["mdadm", "--create", device_name, f"--level={raid_level}", f"--raid-devices={len(device_list)}", *disks],input="yes\n" ,check=True)
    except sub.CalledProcessError as e:
        syslog.syslog(syslog.LOG_WARNING, f"The device is currently in use, or there is a permission issue. Return code: {e}")
        sys.exit(os.EX_NOPERM)


def create_file_system(device_name):
    '''A function to create an XFS file system on a created RAID device.'''
    try:
        sub.run(["mkfs.xfs", "-f", device_name], check=True)
    except sub.CalledProcessError as e:
        syslog.syslog(syslog.LOG_WARNING, f"The device is not ready yet, or there is a permission issue. Return code: {e}")
        sys.exit(os.EX_NOPERM)


def create_mount_point(device_name):
    '''A function that creates a mount path, 
    creates a directory, and then mounts it using the `mount` command.'''
    dev_name = os.path.basename(device_name)
    mount_path = f"/mnt/{dev_name}"
    os.makedirs(mount_path, exist_ok=True)
    
    try:
        sub.run(["mount", device_name, mount_path], check=True)
    except sub.CalledProcessError as e:
        syslog.syslog(syslog.LOG_WARNING, f"Mount failed. The path may be invalid or permission denied. Return code: {e}")
        sys.exit(os.EX_NOPERM)


def save_raid_info():
    '''A function that saves RAID configuration information 
    and writes the resulting values directly to the mdadm.conf file.'''
    result = sub.run(["mdadm", "--detail", "--scan"], capture_output=True, text=True)

    conf_path = pathlib.Path("/etc/mdadm.conf") 
    with open(conf_path, mode="a") as f:
        f.write(result.stdout)
    syslog.syslog(syslog.LOG_INFO, f"Created and registered {str(conf_path)} successfully.")


def write_fstab(device_name, mount_path):
    '''A function that uses the `blkid` command to retrieve the UUID 
    and adds it to the `/etc/fstab` file so that it persists after a reboot.'''
    fstab_path = pathlib.Path("/etc/fstab")
    fstab_content = fstab_path.read_text()
    
    uuid = sub.run(["blkid", "-s" ,"UUID", "-o", "value" , device_name], capture_output=True, text=True).stdout.strip()

    if not any(line.startswith(f"UUID={uuid}") for line in fstab_content.splitlines()):
        with open(fstab_path, mode="a") as f:
            f.write(f"\nUUID={uuid} {mount_path} xfs defaults 0 0\n")
    syslog.syslog(syslog.LOG_INFO, f"Created and registered {str(fstab_path)} successfully.")


def start():
    root_check()
    available_disks = status_check(check_device())
    mdadm_check()
    raid_level = input_raid_level()
    device_name = raid_name(raid_level)
    mount_path = f"/mnt/{os.path.basename(device_name)}"
    raid_level_select(available_disks, device_name, raid_level)
    create_file_system(device_name)
    create_mount_point(device_name)
    save_raid_info()
    write_fstab(device_name, mount_path)


if __name__ == "__main__":
    start()
    syslog.syslog(syslog.LOG_INFO, "Script completed successfully.")
    print("Script completed successfully.")
    syslog.closelog()
