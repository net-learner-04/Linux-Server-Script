#!/bin/bash

# path: /usr/local/bin/setup_ssh_notify.sh

# Ensure this script is run with root privileges (required to modify PAM config)
if [ "$(id -u)" -ne 0 ]
then
    echo "This script must be run as root."
    exit 1
fi

PAM_SSHD="/etc/pam.d/sshd"
NOTIFY_SCRIPT="/usr/local/bin/ssh_notify.sh"
PAM_LINE="session optional pam_exec.so $NOTIFY_SCRIPT"

# Check whether the $NOTIFY_SCRIPT file exists.
if [ ! -f "$NOTIFY_SCRIPT" ]
then
    echo "$NOTIFY_SCRIPT not found. Copy it first."
    exit 1
fi

# If there is an existing PAM line pointing to this script,
# remove it and register the new one.
if grep -qF "pam_exec.so" "$PAM_SSHD" && grep -qF "$NOTIFY_SCRIPT" "$PAM_SSHD"
then
    echo "Existing PAM entry found for this script. Replacing it."
    cp "$PAM_SSHD" "${PAM_SSHD}.bak.$(date +%Y%m%d%H%M%S)"
    sed -i "\|pam_exec.so.*$NOTIFY_SCRIPT|d" "$PAM_SSHD"
    echo "$PAM_LINE" >> "$PAM_SSHD"
    echo "Successfully updated PAM config."
else
    cp "$PAM_SSHD" "${PAM_SSHD}.bak.$(date +%Y%m%d%H%M%S)"
    echo "$PAM_LINE" >> "$PAM_SSHD"
    echo "Successfully registered in PAM config."
fi

# Grant execute permission to the notify script
chmod +x "$NOTIFY_SCRIPT"

# Restore correct SELinux context for the script
restorecon -v "$NOTIFY_SCRIPT"

echo "Setup complete. Please test with a new SSH session in a separate terminal."
