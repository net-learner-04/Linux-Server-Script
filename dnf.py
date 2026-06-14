import subprocess as sub
import os, syslog, time, sys

syslog.openlog(ident="dnf.py", logoption=syslog.LOG_PERROR, facility=syslog.LOG_AUTH)

DAYS = 3 * 24 * 60 * 60 # three days
NOW = time.time()

def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        syslog.syslog(syslog.LOG_ERR, "Run as root.")
        sys.exit(1)

def disk_check():
    space = os.statvfs("/")
    total = space.f_blocks * space.f_frsize
    avail = space.f_bavail * space.f_frsize
    
    free_gb = avail / (1024**3)
    free_percent = (avail / total) * 100
    
    syslog.syslog(syslog.LOG_INFO, f"Free: {free_gb:.2f} GB ({free_percent:.1f}%)")
    
    if free_gb < 2 or free_percent < 20:
        return True
    return False

def detect():
    content = sub.run(["dnf", "history", "list"], capture_output=True, text=True).stdout
    lines = content.splitlines()
    check = False

    result = []
    # lines[2:] -> skip 2 line
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        if line.endswith("*"):
            check = True
            id = line.split()[0]
            if id.isdigit():
                result.append(id)

    if check == False:
        syslog.syslog(syslog.LOG_DEBUG, "No packages requiring restoration were found.")
    else:
        if disk_check():
            cleaner()
        syslog.syslog(syslog.LOG_ERR, f"Failed transactions: {', '.join(result)}")

    return result

def cleaner():
    count = 0

    if not sub.run(["dnf", "clean", "all"], check=True):
        syslog.syslog(syslog.LOG_ERR, "Failed to dnf clean all")

    with os.scandir("/tmp") as tmp:
        for file in tmp:
            try:
                if file.is_file(follow_symlinks=False):
                    info = file.stat()
                    if (NOW - info.st_mtime) > DAYS:
                        os.remove(file.path)
                        count += 1
            except OSError as e:
                syslog.syslog(syslog.LOG_WARNING, f"Failed to remove {file.path}: {e}")

    syslog.syslog(syslog.LOG_INFO, f"Removed {count} old files from /tmp")

def reinstall(id_list):
    count = 0
    for id in id_list:
        if sub.run(["dnf", "history", "redo", f"{id}"], check=True):
            count += 1
    syslog.syslog(syslog.LOG_INFO, f"Successfully reinstalled {count} packages")

root_check()

reinstall(detect())

syslog.closelog()
