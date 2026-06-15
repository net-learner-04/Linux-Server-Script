import subprocess as sub
import os, sys, pathlib, psutil, json

# =============================================================================
# LVM Automation Tool
# =============================================================================
# This tool automatically detects newly added disks and configures LVM.
#
# How it works:
#   1. Scans all block devices and filters out disks with no partitions,
#      no file system, and not part of LVM
#   2. Excludes disks currently mounted or in use by the OS
#   3. Initializes filtered disks as PV (Physical Volume)
#   4. Creates a new VG (Volume Group) or extends an existing one
#   5. Creates a new LV (Logical Volume) or extends an existing one
#   6. Formats the LV with XFS file system
#   7. Mounts the LV and registers it in /etc/fstab for persistence
#
# Benefits:
#   - Reduces manual LVM configuration steps to a single script execution
#   - Automatically detects and skips disks already in use
#   - Prevents duplicate fstab entries on repeated execution
#   - Supports both new LVM setup and extension of existing configuration
#
# Requirements:
#   - Must be run as root
#   - Rocky Linux / RHEL-based systems
#   - Python packages: psutil
#
# Usage:
#   sudo python3 lvm_auto.py
#
# Note:
#   To change the file system, modify the FILE_SYSTEM and COMMAND global variables.
# =============================================================================

FILE_SYSTEM = "xfs"
COMMAND = "xfs_growfs"

def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        print("Run as root")
        sys.exit(1)

def all_device_and_lvm_check():
    '''A function that checks the list of all device blocks in the current system and
      filters out disks that have no partitions,
        no file system signature, and are not part of LVM'''
    result = sub.run(["lsblk", "--json", "-o", "NAME,TYPE,FSTYPE,MOUNTPOINT"],
                      capture_output=True,
                        text=True)
    data = json.loads(result.stdout)
    
    target = [f"/dev/{device['name']}" for device in data["blockdevices"]
              if device["type"] == "disk"
              and device["children"] is None
              and device["fstype"] is None]
    
    return target

def mount_status_check(disk_list):
    '''A function that checks whether the disk is currently mounted
      or is a primary disk in use by the operating system'''
    if len(disk_list) < 1:
        print("No available disks found")
        sys.exit(1)

    mounted_devices = [partition.device for partition in psutil.disk_partitions()]

    none_mounted_devices = [disk for disk in disk_list if disk not in mounted_devices]

    return none_mounted_devices

def pv_reset(device_list):
    '''Function to initialize a PV (Physical Volume) for LVM configuration'''
    if len(device_list) < 1:
        print("Failure to execute the pv_reset() function")
        sys.exit(1)
    
    for device in device_list:
        try:
            sub.run(["pvcreate", device], check=True)
        except sub.CalledProcessError as e:
            print(f"Failed to pvcreate: {device}  {e}")
            sys.exit(1)

def vg_create_or_extend(device_list):
    '''Functions that generate or extend VG (Volume Group)'''
    result = sub.run(["vgs", "--json"], capture_output=True, text=True)
    data = json.loads(result.stdout)

    vg_list = data["report"][0]["vg"]
    
    if len(vg_list) == 0:
        sub.run(["vgcreate", "my_vg", *device_list])
        return "my_vg"
    else:
        for i, vg in enumerate(vg_list):
            print(f"[{i}.] {vg['vg_name']} ({vg['vg_size']})")
        index = int(input("Selecting the volume group to extend: "))
        vg_name = vg_list[index]["vg_name"]
        sub.run(["vgextend", f"{vg_name}", *device_list])
        return vg_name

def allocate_lv(vg_name):
    '''Functions that allocate LV (Logical Volume)'''
    result = sub.run(["lvs", "--json"], capture_output=True, text=True)
    data = json.loads(result.stdout)

    lv_list = data["report"][0]["lv"]
    vg_lv_list = [lv for lv in lv_list if lv["vg_name"] == vg_name]

    if len(vg_lv_list) == 0:
        sub.run(["lvcreate", "-l", "100%FREE", "-n", "lv_data", vg_name])
        return f"/dev/{vg_name}/lv_data", True
    else:
        lv_name = vg_lv_list[0]["lv_name"]
        sub.run(["lvextend", "-l", "+100%FREE", f"/dev/{vg_name}/{lv_name}"])
        return f"/dev/{vg_name}/{lv_name}", False

def create_file_system(lv_path, create):
    '''Function to create a file system (XFS) on a created LV (Logical Volume)'''
    # If you want to change the file system, modify the FILE_SYSTEM and COMMAND global variables.
    if create:
        sub.run([f"mkfs.{FILE_SYSTEM}", lv_path], check=True)
    else:
        sub.run([COMMAND, lv_path], check=True)

def mounting(lv_path, vg_name):
    '''A function that creates a mount point and 
    mounts an LV (Logical Volume) to that point and Auto-mount Settings'''
    mount_path = f"/mnt/{vg_name}"

    pathlib.Path(mount_path).mkdir(parents=True, exist_ok=True)

    sub.run(["mount", f"{lv_path}", f"{mount_path}"])

    # If you want to change the file system, modify the FILE_SYSTEM global variables.
    fstab_entry = f"{lv_path} {mount_path} {FILE_SYSTEM} defaults 0 0"
    fstab = pathlib.Path("/etc/fstab")

    if fstab_entry not in fstab.read_text():
        with pathlib.Path("/etc/fstab").open(mode="a", encoding="utf-8") as f:
            f.write(f"\n{fstab_entry}\n")

def start():
    root_check()
    AVAILABLE_DEVICE_LIST = mount_status_check(all_device_and_lvm_check())
    pv_reset(AVAILABLE_DEVICE_LIST)
    VG_NAME = vg_create_or_extend(AVAILABLE_DEVICE_LIST)
    LV_PATH, CREATE = allocate_lv(VG_NAME)
    create_file_system(LV_PATH, CREATE)
    mounting(LV_PATH, VG_NAME)

if __name__ == "__main__":
    start()
