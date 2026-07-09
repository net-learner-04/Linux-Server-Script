#!/bin/bash

# path: /usr/local/bin/ssh_notify.sh


WEBHOOK_PATH="/etc/ssh_notify/discord_webhook.conf"

LOG_DIR="/var/log"
LOG_PATH="$LOG_DIR/ssh_notify.log"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Ensure log directory exists before writing logs
if [ ! -d "$LOG_DIR" ]
then
    mkdir -p "$LOG_DIR"
fi

# Verify curl is installed for sending HTTP requests
if ! command -v curl &> /dev/null
then
    echo "$TIMESTAMP The curl package is not installed." \
    >> "$LOG_PATH"
    exit 0
fi

# Verify jq is installed for JSON construction
if ! command -v jq &> /dev/null
then
    echo "$TIMESTAMP The jq package is not installed." >> "$LOG_PATH"
    exit 0
fi

# Check if webhook configuration file exists
if [ ! -e "$WEBHOOK_PATH" ]
then
    echo "$TIMESTAMP The Discord webhook file cannot be found." \
    >> "$LOG_PATH"
    exit 0
fi

# Ensure log file exists before writing
if [ ! -f "$LOG_PATH" ]
then
    echo "$TIMESTAMP The log file cannot be found. The file will be created." \
    >> "$LOG_PATH"
fi

# Load Discord webhook URL from external config file
source "$WEBHOOK_PATH"

# Validate that webhook URL is not empty after sourcing
if [ -z "$DISCORD_WEBHOOK" ]
then
    echo "$TIMESTAMP DISCORD_WEBHOOK is missing or empty." >> "$LOG_PATH"
    exit 0
fi

# Validate webhook URL format to avoid invalid requests
if [[ "$DISCORD_WEBHOOK" != https://discord.com/api/webhooks/* ]]
then
    echo "$TIMESTAMP DISCORD_WEBHOOK format looks invalid." >> "$LOG_PATH"
    exit 0
fi

# Ensure script runs only for SSH sessions
if [ "$PAM_SERVICE" != "sshd" ]
then
    exit 0
fi

# Determine event type (login or logout)
if [ "$PAM_TYPE" == "open_session" ]
then
    TITLE="New SSH Login Detected"
    COLOR="3066993"
elif [ "$PAM_TYPE" == "close_session" ]
then
    TITLE="SSH Session Closed"
    COLOR="9807270"
else
    exit 0
fi

# Fallback for missing SSH username
if [ "$PAM_USER" == "" ]
then
    USERNAME="UNKNOWN USER NAME"
else
    USERNAME=$PAM_USER
fi

# Fallback for missing remote IP address
if [ "$PAM_RHOST" == "" ]
then
    IP_ADDR="UNKNOWN IP ADDRESS"
else
    IP_ADDR=$PAM_RHOST
fi

SERVER_HOSTNAME=$(hostname)
ISO_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build Discord embed JSON payload using jq
EMBEDS=$(
jq -n \
  --arg title "$TITLE" \
  --argjson color "$COLOR" \
  --arg username "$USERNAME" \
  --arg ip "$IP_ADDR" \
  --arg server "$SERVER_HOSTNAME" \
  --arg time "$TIMESTAMP" \
  --arg timestamp "$ISO_TIME" \
'{
  embeds: [
    {
      title: $title,
      color: $color,
      fields: [
        {
          name: "User",
          value: $username,
          inline: true
        },
        {
          name: "IP Address",
          value: $ip,
          inline: true
        },
        {
          name: "Server",
          value: $server,
          inline: true
        },
        {
          name: "Time",
          value: $time,
          inline: false
        }
      ],
      footer: {
        text: "ssh_notify script"
      },
      timestamp: $timestamp
    }
  ]
}')

# Send payload to Discord webhook and capture HTTP response code
# --max-time limits how long curl can block, so a slow/unreachable
# Discord endpoint never delays the SSH login/logout itself
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 5 \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$EMBEDS" \
    "$DISCORD_WEBHOOK")

# Log result based on HTTP response status
if [[ "$STATUS" -eq 200 || "$STATUS" -eq 204 ]]
then
    echo "$TIMESTAMP Discord notification sent successfully." >> "$LOG_PATH"
else
    echo "$TIMESTAMP Failed to send Discord notification (status: $STATUS)." >> "$LOG_PATH"
fi
