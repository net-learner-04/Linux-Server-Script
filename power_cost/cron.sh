#!/bin/bash
# Permission-granting commands that must be run before execution
# chmod +x cron.sh
# sudo ./cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ask for the account name to register the crontab under.
read -p "Enter the account name to register the cron job for: " TARGET_USER

# Verify the input is not empty.
if [ -z "$TARGET_USER" ]
then
    echo "Account name cannot be empty."
    exit 1
fi

# Verify that the account actually exists.
if ! id "$TARGET_USER" &>/dev/null
then
    echo "User does not exist: $TARGET_USER"
    exit 1
fi

# Verify root privileges (needed to write to another user's crontab).
if [ "$EUID" -ne 0 ]
then
    echo "This script must be run with root privileges (sudo)."
    exit 1
fi

CRON_JOB="*/10 * * * * cd $SCRIPT_DIR && /usr/bin/python3 main.py"

# Command to Prevent Duplicate Registrations.
(
    crontab -u "$TARGET_USER" -l 2>/dev/null | grep -Fxv "$CRON_JOB"
    echo "$CRON_JOB"
) | crontab -u "$TARGET_USER" -

echo "Cron job registered for user '$TARGET_USER': $CRON_JOB"
