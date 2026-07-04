#!/bin/bash

# Permission-granting commands that must be run before execution
# chmod +x cron.sh
# sudo ./cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_JOB="*/5 * * * * cd $SCRIPT_DIR && /usr/bin/python3 main.py"

# Command to Prevent Duplicate Registrations.

(crontab -l 2>/dev/null | grep -v "main.py"; echo "$CRON_JOB") | crontab -
echo "Cron job registered: $CRON_JOB"
