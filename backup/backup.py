import subprocess as sub
import os, syslog, logging, tqdm, sys
import psutil as pt
import tomllib as tl
import datetime as dt
import pathlib as pl
import threading as th


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
    except FileNotFoundError:
        logging.critical("Configuration file 'conf.toml' not found.")
        syslog.syslog(syslog.LOG_ERR, "Configuration file 'conf.toml' not found.")
        sys.exit(os.EX_CONFIG)
    except tl.TOMLDecodeError as e:
        logging.critical(f"Failed to parse conf.toml: {e}")
        syslog.syslog(syslog.LOG_ERR, f"Failed to parse conf.toml: {e}")
        sys.exit(os.EX_CONFIG)

    try:
        src_paths = list(config["source"]["target"])
        dst_path = config["destination"]["path"]
    except KeyError as e:
        logging.critical(f"Missing required key in conf.toml: {e}")
        syslog.syslog(syslog.LOG_ERR, f"Missing required key in conf.toml: {e}")
        sys.exit(os.EX_CONFIG)

    if len(src_paths) < 1:
        logging.error("No backup source directories specified in the configuration file.")
        syslog.syslog(syslog.LOG_ERR, "No backup source directories specified in the configuration file.")
        sys.exit(os.EX_CANTCREAT)

    try:
        pl.Path(dst_path).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logging.critical(f"Cannot access or create destination path {dst_path}: {e}")
        syslog.syslog(syslog.LOG_ERR, f"Cannot access or create destination path {dst_path}: {e}")
        sys.exit(os.EX_CANTCREAT)

    part_space = get_partition_space(src_paths)

    if not space_check(dst_path, part_space):
        sys.exit(os.EX_CANTCREAT)

    return (src_paths, dst_path, part_space)


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


def space_check(dst_path, part_space):
    '''Compares the total required size of the source files
      against the available free disk space of the destination path.'''
    try:
        usage = pt.disk_usage(dst_path).free
    except OSError as e:
        logging.error(f"Cannot read disk usage for {dst_path}: {e}")
        syslog.syslog(syslog.LOG_ERR, f"Cannot read disk usage for {dst_path}: {e}")
        return False

    if usage < part_space:
        logging.error(f"Not enough space at {dst_path}: free={usage}B, needed={part_space}B")
        syslog.syslog(syslog.LOG_ERR, f"Not enough space at {dst_path}: free={usage}, needed={part_space}")
        return False

    logging.info(f"Space check passed. Required: {part_space}B, Available: {usage}B")
    return True


def feed_gzip(p1, p2, pbar):
    '''Reads the output of tar (p1) in chunks,
      passes it to the standard input of gzip (p2), and updates the progress'''
    try:
        while True:
            chunk = p1.stdout.read(65536)
            if not chunk:
                break
            p2.stdin.write(chunk)
            pbar.update(len(chunk))
    finally:
        p2.stdin.close()
        p1.stdout.close()


def backup_process(src_list, dst_path, part_space):
    '''Executes a multi-process backup pipeline by streaming tar data 
    into gzip compression, while writing the output directly to the destination
      and tracking progress with a real-time progress bar.'''
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"backup_{timestamp}.tar.gz"

    backup_dir = pl.Path(dst_path) / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    full_path = backup_dir / backup_file_name

    command = ["tar", "-c", "-f", "-"] + src_list

    logging.info(f"Starting backup pipeline for targets: {src_list}")
    try:
        p1 = sub.Popen(command, stdout=sub.PIPE, stderr=sub.PIPE)
        logging.info(f"Tar process started. PID: {p1.pid}")

        p2 = sub.Popen(["gzip"], stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE)
        logging.info(f"Gzip process started. PID: {p2.pid}")

        with open(full_path, "wb") as out, \
             tqdm.tqdm(total=part_space, unit="B", unit_scale=True, desc="Backing up") as pbar:

            feeder = th.Thread(target=feed_gzip, args=(p1, p2, pbar))
            feeder.start()

            while True:
                out_chunk = p2.stdout.read(65536)
                if not out_chunk:
                    break
                out.write(out_chunk)

            feeder.join()

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
        syslog.syslog(syslog.LOG_ERR, f"Failed to run backup pipeline: {e}")
        sys.exit(os.EX_SOFTWARE)


def start():
    root_check()
    src_paths, dst_path, part_space = read_toml()
    backup_process(src_paths, dst_path, part_space)


if __name__ == "__main__":
    start()
    logging.info("Backup script finished safely.")
    print("Script completed successfully.")
    syslog.closelog()

