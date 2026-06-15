import subprocess as sub
import os, syslog, logging, tqdm, sys
import psutil as pt
import tomllib as tl
import datetime as dt
import pathlib as pl

syslog.openlog(ident="backup.py", logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.geteuid() != 0:
        syslog.syslog(syslog.LOG_ERR, "Run as root.")
        sys.exit(os.EX_NOPERM)

def read_toml():
    with open("conf.toml", "rb") as toml:
        config = tl.load(toml)
        src_paths = [line for line in config["source"]["target"]]
        dst_path = config["destination"]["path"]

    if len(src_paths) < 1:
        syslog.syslog(syslog.LOG_ERR, "The backup destination directory is not specified in the configuration file")
        sys.exit(os.EX_CANTCREAT)
    else:
        if not space_check(src_paths, dst_path):
            sys.exit(os.EX_CANTCREAT)

    return (src_paths, dst_path)

def space_check(src_list, dst_path):
    partition_space = 0
    for src_path in src_list:
        # dirpath = current directory / dirnames = subdirectory / filenames = files
        for dirpath, dirnames, filenames in os.walk(src_path, topdown=False, followlinks=False):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    if not os.path.islink(file_path):
                        partition_space += os.path.getsize(file_path)
                except OSError as e:
                    syslog.syslog(syslog.LOG_WARNING, f"Failed to calculate partition space {file_path}: {e}")

    usage = pt.disk_usage(dst_path).free
    if usage < partition_space:
        syslog.syslog(syslog.LOG_ERR, f"Not enough space at {dst_path}: free={usage}, needed={partition_space}")
        return False
    return True


def start():
    # root_check()
    
    read_toml()

start()

syslog.closelog()
