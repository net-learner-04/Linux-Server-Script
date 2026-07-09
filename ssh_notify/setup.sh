#!/bin/bash

# path: /usr/local/bin/setup_ssh_notify.sh

# Ensure this script is run with root privileges (required to modify PAM config)
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 1
fi

PAM_SSHD="/etc/pam.d/sshd"
NOTIFY_SCRIPT="/usr/local/bin/ssh_notify.sh"
PAM_LINE="session optional pam_exec.so seteuid $NOTIFY_SCRIPT"

# Check if the PAM hook is already registered to avoid duplicate entries
if grep -qF "$PAM_LINE" "$PAM_SSHD"; then
    echo "Already registered in PAM config. Skipping."
else
    # Back up the original file with a timestamp before modifying it
    cp "$PAM_SSHD" "${PAM_SSHD}.bak.$(date +%Y%m%d%H%M%S)"

    # Append the PAM hook line
    echo "$PAM_LINE" >> "$PAM_SSHD"
    echo "Successfully registered in PAM config."
fi

# Grant execute permission to the notify script
chmod +x "$NOTIFY_SCRIPT"

# Restore correct SELinux context for the script
restorecon -v "$NOTIFY_SCRIPT"

echo "Setup complete. Please test with a new SSH session in a separate terminal."
