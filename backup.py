import subprocess as sub
import os, syslog, logging, tqdm, sys
import psutil as pt
import tomllib as tl
import datetime as dt
import pathlib as pl

# =============================================================================
# Automated Backup Tool
# =============================================================================
# This tool automates the process of archiving and compressing system directories.
#
# How it works:
#   1. Validates root privileges to ensure access to system directories
#   2. Reads the backup source targets and destination path from 'conf.toml'
#   3. Recursively calculates the total size of source files, excluding symlinks
#   4. Checks the available disk space at the destination before running the backup
#   5. Executes a multi-process pipeline streaming 'tar' data into 'gzip'
#   6. Displays a real-time progress bar (tqdm) while writing to the final .tar.gz file
#   7. Records operational events to both a local log file and the OS syslog
#
# Benefits:
#   - Simplifies complex backup and compression steps into a single execution
#   - Uses a streaming pipeline to prevent high memory or disk buffer overhead
#   - Features dual-channel logging (logging + syslog) for robust troubleshooting
#   - Prevents accidental script failures with proactive disk space validation
#
# Requirements:
#   - Must be run as root
#   - Linux-based systems (with tar and gzip installed)
#   - Python packages: psutil, tqdm
#
# Usage:
#   sudo python3 backup.py
#
# Note:
#   To change the logging behavior, modify the basicConfig handlers.
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("backup.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)                 
    ]
)

syslog.openlog(ident="backup.py", logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.geteuid() != 0:
        logging.critical("Root privilege required to run this script.")
        syslog.syslog(syslog.LOG_ERR, "Run as root.")
        sys.exit(os.EX_NOPERM)

def read_toml():
    '''Reads and parses the conf.toml file to load backup targets
      and destination, then triggers a disk space validation check.'''
    logging.info("Reading configuration file (conf.toml)...")
    try:
        with open("conf.toml", "rb") as toml:
            config = tl.load(toml)
            src_paths = [line for line in config["source"]["target"]]
            dst_path = config["destination"]["path"]
    except FileNotFoundError:
        logging.critical("Configuration file 'conf.toml' not found.")
        sys.exit(os.EX_CONFIG)

    if len(src_paths) < 1:
        logging.error("The backup destination directory is not specified in the configuration file.")
        syslog.syslog(syslog.LOG_ERR, "The backup destination directory is not specified in the configuration file")
        sys.exit(os.EX_CANTCREAT)
    else:
        if not space_check(src_paths, dst_path):
            sys.exit(os.EX_CANTCREAT)

    return (src_paths, dst_path)

def get_partition_space(src_list):
    '''Recursively calculates the total size of all files 
    within the source directories, safely excluding symbolic links.'''
    partition_space = 0
    for src_path in src_list:
        for dirpath, dirnames, filenames in os.walk(src_path, topdown=False, followlinks=False):
            for filename in filenames:
                file_path = pl.Path(dirpath) / filename
                try:
                    if not file_path.is_symlink():
                        partition_space += file_path.stat().st_size
                except OSError as e:
                    logging.warning(f"Failed to calculate partition space for {file_path}: {e}")
                    syslog.syslog(syslog.LOG_WARNING, f"Failed to calculate partition space {file_path}: {e}")
    
    return partition_space

def space_check(src_paths, dst_path):
    '''Compares the total required size of the source files
      against the available free disk space of the destination path.'''
    usage = pt.disk_usage(dst_path).free
    part_space = get_partition_space(src_paths)

    if usage < part_space:
        logging.error(f"Not enough space at {dst_path}: free={usage}B, needed={part_space}B")
        syslog.syslog(syslog.LOG_ERR, f"Not enough space at {dst_path}: free={usage}, needed={part_space}")
        return False
    
    logging.info(f"Space check passed. Required: {part_space}B, Available: {usage}B")
    return True

def compress(src_list, dst_path):
    '''Executes a multi-process backup pipeline by streaming tar data 
    into gzip compression, while writing the output directly to the destination
      and tracking progress with a real-time progress bar.'''
    today = dt.date.today().isoformat()
    backup_file_name = f"backup_{today}.tar.gz"

    total_size = get_partition_space(src_list)

    backup_dir = pl.Path(dst_path) / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    full_path = backup_dir / backup_file_name
    
    command = ["tar", "-c"] + src_list

    logging.info(f"Starting backup pipeline for targets: {src_list}")
    try:
        p1 = sub.Popen(command, stdout=sub.PIPE, stderr=sub.PIPE)
        logging.info(f"Tar process started. PID: {p1.pid}")
        
        p2 = sub.Popen(["gzip"], stdin=p1.stdout, stdout=sub.PIPE, stderr=sub.PIPE)
        logging.info(f"Gzip process started. PID: {p2.pid}")

        if p1.stdout:
            p1.stdout.close()
        
        with open(full_path, "wb") as out:
            with tqdm.tqdm(total=total_size, unit="B", unit_scale=True, desc="Backing up") as pbar:
                while True:
                    chunk = p2.stdout.read(65536) if p2.stdout else b""
                    if not chunk:
                        break
                    out.write(chunk)
                    pbar.update(len(chunk))
                    
        p1.wait()
        p2.wait()

        if p1.returncode != 0 or p2.returncode != 0:
            tar_err = p1.stderr.read().decode().strip() if p1.stderr else ""
            gzip_err = p2.stderr.read().decode().strip() if p2.stderr else ""
            
            error_msg = f"Backup failed! tar_rc={p1.returncode} ({tar_err}), gzip_rc={p2.returncode} ({gzip_err})"
            logging.error(error_msg)
            syslog.syslog(syslog.LOG_ERR, error_msg)
            sys.exit(os.EX_SOFTWARE)
        else:
            success_msg = f"Backup successfully completed: {full_path}"
            logging.info(success_msg)
            syslog.syslog(syslog.LOG_INFO, success_msg)
            
    except Exception as e:
        logging.exception(f"Exception occurred during compression: {e}")
        syslog.syslog(syslog.LOG_ERR, f"Failed to start tar process: {e}")
        sys.exit(os.EX_SOFTWARE)

def start():
    root_check()
    src_paths, dst_path = read_toml()
    compress(src_paths, dst_path)

if __name__ == "__main__":
    start()
    syslog.closelog()
    logging.info("Backup script finished safely.")
