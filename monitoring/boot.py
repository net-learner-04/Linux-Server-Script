import datetime as dt
import psutil, os

from config import BOOTFILE


def boot_time_check():
    '''A function that detects whether the current boot time has changed
    from the reboot time stored in a file.'''
    boot_time = dt.datetime.fromtimestamp(psutil.boot_time())

    if not os.path.exists(BOOTFILE):
        return True
    
    with open(BOOTFILE, mode="r") as file:
        last_boot = dt.datetime.fromisoformat(file.read().strip())
        
    return last_boot != boot_time


def update_boot_time():
    '''A function that saves the current boot time to the '.last_boot' file.'''
    with open(BOOTFILE, mode="w") as file:
        file.write(f"{dt.datetime.fromtimestamp(psutil.boot_time()).isoformat()}\n")
