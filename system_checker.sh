#!/bin/bash

clear

# Verify Root Permissions.
if [ "$EUID" -ne 0 ]; then
    echo "Run as root."
    exit 1
fi

# Iterate over all NVMe/SATA disks detected by smartctl and check their SMART health attributes.
#!/bin/bash

for dev in $(smartctl --scan | grep -o "^/dev/[a-zA-Z0-9]*"); do
    echo "=== $dev ==="
    info=$(smartctl -A "$dev")

    # Extract key SMART attributes from the output
    critical_warning=$(echo "$info" | grep -oP 'Critical Warning:\s*\K\S+')
    percentage_used=$(echo "$info" | grep -oP 'Percentage Used:\s*\K[0-9]+')
    spare=$(echo "$info" | grep -oP 'Available Spare:\s*\K[0-9]+')
    spare_threshold=$(echo "$info" | grep -oP 'Available Spare Threshold:\s*\K[0-9]+')
    integrity_errors=$(echo "$info" | grep -oP 'Media and Data Integrity Errors:\s*\K[0-9,]+' | tr -d ',')
    error_log=$(echo "$info" | grep -oP 'Error Information Log Entries:\s*\K[0-9,]+' | tr -d ',')

    # Critical Warning should be 0x00; any other value indicates a problem.
    if [ "$critical_warning" != "0x00" ]; then
        echo "Critical Warning: $critical_warning"
    fi

    # Percentage Used close to 100% means the drive is nearing end of life.
    if [ -n "$percentage_used" ] && [ "$percentage_used" -ge 80 ]; then
        echo "Percentage Used is high: ${percentage_used}%"
    fi

    # If Available Spare has dropped to or below the threshold, replacement may be needed soon.
    if [ -n "$spare" ] && [ -n "$spare_threshold" ] && [ "$spare" -le "$spare_threshold" ]; then
        echo "Available Spare is below the threshold: ${spare}% <= ${spare_threshold}%"
    fi

    # Any non-zero value here means actual data corruption/integrity issues have occurred.
    if [ -n "$integrity_errors" ] && [ "$integrity_errors" -gt 0 ]; then
        echo "Data Integrity Errors Occur: $integrity_errors"
    fi

    echo "Percentage Used: ${percentage_used}%"
    
    echo "Error Log Entries: $error_log"
done

# Stored variables for the number of root-privileged UIDs.
ROOT_UID_COUNT=$(cat /etc/passwd | awk -F':' '{print $3}' | grep -w "0" | wc -l)
