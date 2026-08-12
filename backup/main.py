import subprocess as sub
import os, syslog, logging, tqdm, sys
import psutil as pt
import tomllib as tl
import datetime as dt
import pathlib as pl
import threading as th
import fcntl, shutil, hashlib


# Resolve all paths relative to the script's own location, not the
# current working directory. This makes the script safe to run from
# cron, systemd timers, or any other directory.
BASE_DIR = pl.Path(__file__).resolve().parent
CONF_PATH = BASE_DIR / "conf.toml"
LOG_PATH = BASE_DIR / "backup.log"
LOCK_PATH = BASE_DIR / "backup.lock"

# Kept open for the lifetime of the process so the OS-level lock
# (fcntl.flock) is held until the script exits or releases it explicitly.
_lock_file_handle = None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


syslog.openlog(ident="backup", logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)


def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.geteuid() != 0:
        logging.critical("Root privilege required to run this script.")
        syslog.syslog(syslog.LOG_ERR, "Run as root.")
        sys.exit(os.EX_NOPERM)


def acquire_lock():
    '''Prevents concurrent runs of the script by taking an exclusive,
    non-blocking lock on a dedicated lock file. If another instance is
    already running, this instance exits immediately instead of writing
    to the same destination in parallel.'''
    global _lock_file_handle
    _lock_file_handle = open(LOCK_PATH, "w")
    try:
        fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logging.critical("Another instance of the backup script is already running. Exiting.")
        syslog.syslog(syslog.LOG_ERR, "Backup already in progress. Exiting.")
        sys.exit(os.EX_TEMPFAIL)
    _lock_file_handle.write(str(os.getpid()))
    _lock_file_handle.flush()
    logging.info(f"Lock acquired ({LOCK_PATH}).")


def release_lock():
    '''Releases the lock file so subsequent runs are not blocked.'''
    global _lock_file_handle
    if _lock_file_handle is not None:
        try:
            fcntl.flock(_lock_file_handle, fcntl.LOCK_UN)
            _lock_file_handle.close()
        except OSError as e:
            logging.warning(f"Failed to release lock cleanly: {e}")
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except OSError:
            pass


def read_toml():
    '''Reads and parses the conf.toml file to load backup targets
      and destination, then triggers a disk space validation check.'''
    logging.info("Reading configuration file (conf.toml)...")
    try:
        with open(CONF_PATH, "rb") as toml:
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

    # Optional: number of days of backups to keep. If absent, no old
    # backups are ever deleted (same behavior as before).
    retention_days = config.get("destination", {}).get("retention_days")

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

    return (src_paths, dst_path, part_space, retention_days)


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


def get_compressor():
    '''Prefers pigz (parallel gzip) over gzip when available, since pigz
    uses all CPU cores and can drastically cut compression time for large
    backups. Falls back to plain gzip if pigz is not installed.'''
    pigz_path = shutil.which("pigz")
    if pigz_path:
        logging.info("Using pigz for parallel compression.")
        return ["pigz"]
    logging.info("pigz not found, falling back to single-threaded gzip.")
    return ["gzip"]


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


def drain_stderr(proc, name):
    '''Continuously drains a subprocess's stderr in the background.
    Without this, a chatty process (e.g. tar warning that a file changed
    while being read) can fill the OS pipe buffer and deadlock the whole
    pipeline once the buffer is full and nobody is reading it.'''
    try:
        for raw_line in iter(proc.stderr.readline, b""):
            line = raw_line.decode(errors="replace").rstrip()
            if line:
                logging.debug(f"[{name}] {line}")
    finally:
        proc.stderr.close()


def verify_backup(full_path):
    '''Verifies the integrity of the produced archive by listing its
    contents (tar -tzf) and computing a SHA-256 checksum alongside it.
    A backup that cannot even be listed is not a usable backup.'''
    logging.info(f"Verifying archive integrity: {full_path}")
    result = sub.run(["tar", "-tzf", str(full_path)], stdout=sub.DEVNULL, stderr=sub.PIPE)
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace").strip()
        logging.error(f"Integrity check failed for {full_path}: {err}")
        syslog.syslog(syslog.LOG_ERR, f"Integrity check failed for {full_path}: {err}")
        return False

    sha256 = hashlib.sha256()
    with open(full_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    checksum_path = pl.Path(str(full_path) + ".sha256")
    checksum_path.write_text(f"{sha256.hexdigest()}  {full_path.name}\n")

    logging.info(f"Integrity check passed. SHA-256: {sha256.hexdigest()}")
    return True


def cleanup_old_backups(backup_dir, retention_days):
    '''Deletes backup archives (and their checksum files) older than
    retention_days. Does nothing if retention_days is not configured, to
    preserve the previous behavior for anyone who hasn't opted in.'''
    if retention_days is None:
        return

    cutoff = dt.datetime.now() - dt.timedelta(days=retention_days)
    removed = 0
    for entry in pl.Path(backup_dir).glob("backup_*.tar.gz*"):
        try:
            mtime = dt.datetime.fromtimestamp(entry.stat().st_mtime)
            if mtime < cutoff:
                entry.unlink()
                removed += 1
                logging.info(f"Removed old backup file: {entry}")
        except OSError as e:
            logging.warning(f"Failed to remove old backup {entry}: {e}")

    if removed:
        logging.info(f"Retention cleanup complete. Removed {removed} file(s) older than {retention_days} day(s).")


def backup_process(src_list, dst_path, part_space, retention_days):
    '''Executes a multi-process backup pipeline by streaming tar data 
    into gzip compression, while writing the output directly to the destination
      and tracking progress with a real-time progress bar.'''
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"backup_{timestamp}.tar.gz"

    backup_dir = pl.Path(dst_path) / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    full_path = backup_dir / backup_file_name

    # Never let the destination directory be swallowed into its own backup.
    command = ["tar", "-c", "-f", "-", f"--exclude={backup_dir}"] + src_list
    compressor_cmd = get_compressor()

    p1 = None
    p2 = None
    logging.info(f"Starting backup pipeline for targets: {src_list}")
    try:
        p1 = sub.Popen(command, stdout=sub.PIPE, stderr=sub.PIPE)
        logging.info(f"Tar process started. PID: {p1.pid}")

        p2 = sub.Popen(compressor_cmd, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE)
        logging.info(f"{compressor_cmd[0]} process started. PID: {p2.pid}")

        # Drain both stderr streams in the background so a verbose tar/gzip
        # process can never fill the pipe buffer and deadlock the pipeline.
        p1_stderr_thread = th.Thread(target=drain_stderr, args=(p1, "tar"))
        p2_stderr_thread = th.Thread(target=drain_stderr, args=(p2, compressor_cmd[0]))
        p1_stderr_thread.start()
        p2_stderr_thread.start()

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
        p1_stderr_thread.join()
        p2_stderr_thread.join()

        # tar exits with 1 for non-fatal warnings (e.g. "file changed as we
        # read it"), which is common and expected when backing up a live
        # system. Only treat 2+ as an actual failure.
        tar_failed = p1.returncode not in (0, 1)
        gzip_failed = p2.returncode != 0

        if tar_failed or gzip_failed:
            error_msg = f"Backup failed! tar_rc={p1.returncode}, {compressor_cmd[0]}_rc={p2.returncode}"
            logging.error(error_msg)
            syslog.syslog(syslog.LOG_ERR, error_msg)
            sys.exit(os.EX_SOFTWARE)

        if p1.returncode == 1:
            logging.warning("tar reported non-fatal warnings (e.g. files changed during read). Continuing.")

        if not verify_backup(full_path):
            sys.exit(os.EX_SOFTWARE)

        success_msg = f"Backup successfully completed and verified: {full_path}"
        logging.info(success_msg)
        syslog.syslog(syslog.LOG_INFO, success_msg)

        cleanup_old_backups(backup_dir, retention_days)

    except Exception as e:
        logging.exception(f"Exception occurred during compression: {e}")
        syslog.syslog(syslog.LOG_ERR, f"Failed to run backup pipeline: {e}")
        sys.exit(os.EX_SOFTWARE)
    finally:
        # Make sure no orphaned tar/gzip processes are left behind if we
        # exited early due to an exception.
        for proc, name in ((p1, "tar"), (p2, compressor_cmd[0] if p2 else "compressor")):
            if proc is not None and proc.poll() is None:
                logging.warning(f"Terminating leftover {name} process (PID: {proc.pid}).")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except sub.TimeoutExpired:
                    proc.kill()


def start():
    root_check()
    acquire_lock()
    try:
        src_paths, dst_path, part_space, retention_days = read_toml()
        backup_process(src_paths, dst_path, part_space, retention_days)
    finally:
        release_lock()


if __name__ == "__main__":
    start()
    logging.info("Backup script finished safely.")
    print("Script completed successfully.")
    syslog.closelog()
