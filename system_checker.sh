#!/bin/bash

clear

# Verify Root Permissions.
if [ "$EUID" -ne 0 ]; then
    echo "Run as root."
    exit 1
fi

# Iterate over all NVMe/SATA disks detected by smartctl and check their SMART health attributes.
for dev in $(smartctl --scan | grep -o "^/dev/[a-zA-Z0-9]*"); do
    echo "===== $dev ====="
    echo
    INFO=$(smartctl -A "$dev")

    # Extract key SMART attributes from the output
    CRITICAL_WARNING=$(echo "$INFO" | grep -oP 'Critical Warning:\s*\K\S+')
    PERCENTAGE_USED=$(echo "$INFO" | grep -oP 'Percentage Used:\s*\K[0-9]+')
    SPARE=$(echo "$INFO" | grep -oP 'Available Spare:\s*\K[0-9]+')
    SPARE_THRESHOLD=$(echo "$INFO" | grep -oP 'Available Spare Threshold:\s*\K[0-9]+')
    INTEGRITY_ERRORS=$(echo "$INFO" | grep -oP 'Media and Data Integrity Errors:\s*\K[0-9,]+' | tr -d ',')
    ERROR_LOG=$(echo "$INFO" | grep -oP 'Error Information Log Entries:\s*\K[0-9,]+' | tr -d ',')

    # Critical Warning should be 0x00; any other value indicates a problem.
    if [ "$CRITICAL_WARNING" != "0x00" ]; then
        echo "Critical Warning: $CRITICAL_WARNING"
        echo
    fi

    # Percentage Used close to 100% means the drive is nearing end of life.
    if [ -n "$PERCENTAGE_USED" ] && [ "$PERCENTAGE_USED" -ge 80 ]; then
        echo "Percentage Used is high: ${PERCENTAGE_USED}%"
        echo
    fi

    # If Available Spare has dropped to or below the threshold, replacement may be needed soon.
    if [ -n "$SPARE" ] && [ -n "$SPARE_THRESHOLD" ] && [ "$SPARE" -le "$SPARE_THRESHOLD" ]; then
        echo "Available Spare is below the threshold: ${SPARE}% <= ${SPARE_THRESHOLD}%"
        echo
    fi

    # Any non-zero value here means actual data corruption/integrity issues have occurred.
    if [ -n "$INTEGRITY_ERRORS" ] && [ "$INTEGRITY_ERRORS" -gt 0 ]; then
        echo "Data Integrity Errors Occur: $INTEGRITY_ERRORS"
        echo
    fi

    echo "Percentage Used: ${PERCENTAGE_USED}%"
    echo
    echo "Error Log Entries: $ERROR_LOG"
    echo
done

# Stored variables for the number of root-privileged UIDs.
ROOT_UID_COUNT=$(cat /etc/passwd | awk -F':' '{print $3}' | grep -w "0" | wc -l)

if [ "$ROOT_UID_COUNT" -gt 1 ]; then
    echo "In addition to the root account, there is another user with root privileges."
    echo "Please check the /etc/passwd file."
fi
