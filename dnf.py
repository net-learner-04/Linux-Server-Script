import subprocess as sub
import os, syslog, time, sys

# =============================================================================
# DNF Failed Transaction Recovery Tool
# =============================================================================
# This tool detects incomplete or failed DNF transactions and attempts
# to automatically recover them.
#
# How it works:
#   1. Runs "dnf history list" and parses for transactions marked with "*"
#      (incomplete/failed transactions)
#   2. If no failed transactions are found, logs a debug message and exits
#   3. If failed transactions exist, checks disk space (statvfs)
#   4. If disk space is low (<2GB or <20% free), runs cleaner:
#        - "dnf clean all" to clear cached packages/metadata
#        - Deletes files in /tmp older than 10 days
#        - Removes resulting empty directories under /tmp
#   5. Attempts to redo each failed transaction via
#      "dnf history redo <id>" (single retry, no further retries)
#   6. Classifies failures by error type (disk space / permission-auth /
#      other) based on returncode and stderr, and logs accordingly
#
# Logging:
#   - All events are logged via syslog (facility: DAEMON, ident: dnf.py)
#   - Includes detection results, disk usage, cleanup results, and
#     per-transaction retry outcomes
#
# Benefits:
#   - Automatically resolves common causes of failed DNF transactions
#     (e.g., insufficient disk space)
#   - Avoids repeated retries; failures are simply logged for review
#   - Designed to run unattended via cron/systemd timer
#
# Requirements:
#   - Must be run as root
#   - Rocky Linux / RHEL-based systems
#
# Usage:
#   sudo python3 dnf.py
#
# Note:
#   To change the "old file" threshold for /tmp cleanup, modify the
#   DAYS global variable. To change disk space thresholds, modify the
#   conditions inside disk_check().
# =============================================================================

syslog.openlog(ident="dnf.py", logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

DAYS = ((10 * 60) * 60) * 24 # ten days
NOW = time.time()

def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        syslog.syslog(syslog.LOG_ERR, "Run as root.")
        sys.exit(os.EX_NOPERM)

def disk_check():
    '''Function to check disk space'''
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
    '''A function that checks for any pending or failed transactions
      and returns their IDs'''
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
            t_id = line.split()[0]
            if t_id.isdigit():
                result.append(t_id)

    if check == False:
        syslog.syslog(syslog.LOG_DEBUG, "No packages requiring restoration were found.")
    else:
        if disk_check():
            syslog.syslog(syslog.LOG_WARNING, "Low disk space detected, running cleaner")
            cleaner()
        syslog.syslog(syslog.LOG_ERR, f"Failed transactions: {', '.join(result)}")

    return result

def cleaner():
    '''A function to clear DNF cache and free up space by deleting files
      older than 10 days in the /tmp folder'''
    count = 0

    result = sub.run(["dnf", "clean", "all"], capture_output=True, text=True)
    if result.returncode != 0:
        syslog.syslog(syslog.LOG_ERR, f"Failed to dnf clean all: {result.stderr.strip()}")

    # dirpath = current directory / dirnames = subdirectory / filenames = files
    for dirpath, dirnames, filenames in os.walk("/tmp", topdown=False):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            try:
                mtime = os.stat(path).st_mtime
                if NOW - mtime > DAYS:
                    os.remove(path)
                    count += 1
            except OSError as e:
                syslog.syslog(syslog.LOG_WARNING, f"Failed to remove {path}: {e}")

        if not os.listdir(dirpath) and dirpath != "/tmp":
            os.rmdir(dirpath)

    syslog.syslog(syslog.LOG_INFO, f"Removed {count} old files from /tmp")
    disk_check()

def reinstaller(id_list):
    '''Function to redownload transactions where errors were detected'''
    count = 0
    for id in id_list:
        result = sub.run(["dnf", "history", "redo", id], capture_output=True, text=True)
        if result.returncode == 0:
            count += 1
        else:
            err = result.stderr.lower()
            if "no space left" in err or "disk" in err:
                syslog.syslog(syslog.LOG_ERR, f"Transaction {id} failed: disk space issue")
            elif "permission denied" in err or "forbidden" in err or "gpg" in err:
                syslog.syslog(syslog.LOG_ERR, f"Transaction {id} failed: permission/auth issue")
            else:
                syslog.syslog(syslog.LOG_ERR, f"Transaction {id} failed: {result.stderr.strip()}")

    syslog.syslog(syslog.LOG_INFO, f"Successfully reinstalled {count} packages")

root_check()

reinstaller(detect())

syslog.closelog()
