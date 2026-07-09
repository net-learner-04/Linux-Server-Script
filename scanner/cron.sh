#!/bin/bash

# Enter the absolute path to the project.
PROJECT_PATH=""
CRON_SCHEDULE="*/10 * * * *"
LOG_FILE="${PROJECT_PATH}/cron.log"
MAIN_SCRIPT="${PROJECT_PATH}/main.py"

read -r -p "Enter the account name to register the crontab under: " TARGET_USER

# Verify the PROJECT_PATH input.
if [ -z "$PROJECT_PATH" ]
then
    echo "Please enter the PROJECT_PATH variable at the top of the script."
    exit 1
fi

# Verify the TARGET_USER input.
if [ -z "$TARGET_USER" ]
then
    echo "Please enter the TARGET_USER variable at the top of the script."
    exit 1
fi

# Verify that the TARGET_USER actually exists.
if ! id "$TARGET_USER" &>/dev/null
then
    echo "User does not exist: $TARGET_USER"
    exit 1
fi

# Check for the existence of main.py.
if [ ! -f "$MAIN_SCRIPT" ]
then
    echo "Cannot find main.py: $MAIN_SCRIPT"
    exit 1
fi

# Verify root privileges.
if [ "$EUID" -ne 0 ]
then
    echo "This script must be run with root privileges."
    exit 1
fi

# Checking the Python 3 Path.
# Note: 'which python3' here reflects root's PATH, not TARGET_USER's.
# If TARGET_USER uses pyenv or a user-local python, set PYTHON_BIN manually below.
PYTHON_BIN=$(which python3)
if [ -z "$PYTHON_BIN" ]
then
    echo "python3 cannot be found."
    exit 1
fi

# Check if the item has already been registered. (to prevent duplicate entries)
CRON_JOB="${CRON_SCHEDULE} ${PYTHON_BIN} ${MAIN_SCRIPT} >> ${LOG_FILE} 2>&1"
if crontab -u "$TARGET_USER" -l 2>/dev/null | grep -Fq "$MAIN_SCRIPT"
then
    echo "It is already registered in crontab for user: $TARGET_USER. Skipping registration."
    echo "Currently Registered:"
    crontab -u "$TARGET_USER" -l | grep -F "$MAIN_SCRIPT"
    exit 0
fi

# Add a new task to the existing crontab for TARGET_USER.
(crontab -u "$TARGET_USER" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$TARGET_USER" -

# View Results.
echo "Crontab setup complete for user: $TARGET_USER"
echo "Registered Tasks:"
crontab -u "$TARGET_USER" -l | grep -F "$MAIN_SCRIPT"
echo ""
echo "Logs are stored in the following directory: $LOG_FILE"
