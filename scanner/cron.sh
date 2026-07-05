#!/bin/bash

# Enter the absolute path to the project.
PROJECT_PATH=""

CRON_SCHEDULE="*/10 * * * *"
LOG_FILE="${PROJECT_PATH}/cron.log"
MAIN_SCRIPT="${PROJECT_PATH}/main.py"

# Verify the PROJECT_PATH input.
if [ -z "$PROJECT_PATH" ]; then
    echo "Please enter the PROJECT_PATH variable at the top of the script."
    exit 1
fi

# Check for the existence of main.py.
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "Cannot find main.py: $MAIN_SCRIPT"
    exit 1
fi

# Verify root privileges.
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with root privileges."
    exit 1
fi

# Checking the Python 3 Path.
PYTHON_BIN=$(which python3)
if [ -z "$PYTHON_BIN" ]; then
    echo "python3 cannot be found."
    exit 1
fi

# Check if the item has already been registered. (to prevent duplicate entries)
CRON_JOB="${CRON_SCHEDULE} ${PYTHON_BIN} ${MAIN_SCRIPT} >> ${LOG_FILE} 2>&1"

if crontab -l 2>/dev/null | grep -Fq "$MAIN_SCRIPT"; then
    echo "It is already registered in crontab. Skipping registration."
    echo "Currently Registered:"
    crontab -l | grep -F "$MAIN_SCRIPT"
    exit 0
fi

# Add a new task to the existing crontab.
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

# View Results.
echo "Crontab setup complete."
echo "Registered Tasks:"
crontab -l | grep -F "$MAIN_SCRIPT"
echo ""
echo "Logs are stored in the following directory: $LOG_FILE"
