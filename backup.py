# =============================================================================
# Automated Backup Tool
# =============================================================================
# This tool automates the process of archiving and compressing system directories.
#
# How it works:
#   1. Validates root privileges to ensure access to system directories
#   2. Reads the backup source targets and destination path from 'conf.toml',
#      validating the TOML syntax and required keys
#   3. Creates the destination directory automatically if it does not exist
#   4. Recursively calculates the total size of source files, excluding symlinks
#   5. Checks the available disk space at the destination before running the backup
#   6. Executes a multi-process pipeline streaming 'tar' data into 'gzip', using a
#      background thread to feed data between the two processes and avoid deadlocks
#   7. Displays a real-time, byte-accurate progress bar (tqdm) by tracking the
#      uncompressed 'tar' output as it streams into the final .tar.gz file
#   8. Records operational events to both a local log file and the OS syslog
#
# Benefits:
#   - Simplifies complex backup and compression steps into a single execution
#   - Uses a streaming pipeline to prevent high memory or disk buffer overhead
#   - Features dual-channel logging (logging + syslog) for robust troubleshooting
#   - Prevents accidental script failures with proactive disk space validation
#   - Generates a uniquely timestamped archive per run, avoiding overwrites
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
