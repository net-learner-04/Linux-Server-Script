#!/bin/bash

# Permission-granting commands that must be run before execution
chmod +x cron.sh
sudo ./cron.sh

SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/main.py"
CRON_JOB="*/5 * * * * /usr/bin/python3 $SCRIPT_PATH"

# Command to Prevent Duplicate Registrations.
(crontab -l 2>/dev/null | grep -v "monitor.py"; echo "$CRON_JOB") | crontab -

echo "Cron job registered: $CRON_JOB"
