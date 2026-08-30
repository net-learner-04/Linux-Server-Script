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
WEBHOOK_DIR="/etc/ssh_notify"
WEBHOOK_PATH="$WEBHOOK_DIR/discord_webhook.conf"

# Check whether the $NOTIFY_SCRIPT file exists.
if [ ! -f "$NOTIFY_SCRIPT" ]
then
    echo "$NOTIFY_SCRIPT not found. Copy it first."
    exit 1
fi

# Prompt for the Discord webhook URL and validate its format before saving.
read -r -p "Enter your Discord webhook URL: " DISCORD_WEBHOOK_INPUT

if [[ "$DISCORD_WEBHOOK_INPUT" != https://discord.com/api/webhooks/* ]]
then
    echo "That doesn't look like a valid Discord webhook URL. Aborting."
    exit 1
fi

mkdir -p "$WEBHOOK_DIR"

cat << EOF > "$WEBHOOK_PATH"
DISCORD_WEBHOOK="$DISCORD_WEBHOOK_INPUT"
EOF

chmod 600 "$WEBHOOK_PATH"

chown root:root "$WEBHOOK_PATH"

echo "Webhook config written to $WEBHOOK_PATH"

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
