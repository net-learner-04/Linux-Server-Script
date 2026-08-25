#!/bin/bash

# MAC Address of the Target Desktop.
TARGET_MAC=""

# The IP address of the target desktop or the broadcast IP address.
TARGET_IP=""

# Log File Path.
LOG_FILE="/var/log/wol_auto.log"

# Time of Execution.
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Check if wakeonlan is installed.
if ! command -v wakeonlan &> /dev/null; then
    echo "[$TIMESTAMP] The 'wakeonlan' command cannot be found." >> "$LOG_FILE"
    exit 1
fi

# Sending WOL Packets and Logging.
wakeonlan -i "$TARGET_IP" "$TARGET_MAC" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] WOL packet sent successfully. (MAC: $TARGET_MAC)" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] Failed to send WOL packet. (MAC: $TARGET_MAC)" >> "$LOG_FILE"
fi
