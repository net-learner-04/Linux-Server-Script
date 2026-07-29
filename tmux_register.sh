#!/bin/bash

clear

if [ "$EUID" -ne 0 ]; then
    echo "Error: Run as root."
    exit 1
fi

read -r -p "Enter the absolute path of the script to be executed: " FILE_PATH

# If the file the user wants to run does not exist, terminate the process.
if [ ! -f "$FILE_PATH" ]; then
    echo "File not found. Please check the path."
    exit 1
fi

read -r -p "Please enter the name of the program to run the file (example -> python3): " COMMAND_NAME

read -r -p "Enter a tmux session name: " SESSION_NAME

SYSTEMD_FILE_PATH="/etc/systemd/system/${SESSION_NAME}.service"

cat << EOF > "$SYSTEMD_FILE_PATH"
[Unit]
Description=Auto Start Tmux Session on Boot
After=network.target

[Service]
Type=forking
User=$LOGNAME
ExecStart=/usr/bin/tmux new-session -d -s "$SESSION_NAME" "$COMMAND_NAME" "$FILE_PATH"
ExecStop=/usr/bin/tmux kill-session -t "$SESSION_NAME"

[Install]
WantedBy=multi-user.target
EOF

echo "Restart the systemd daemon to save the settings."
systemctl daemon-reload

echo "The service you created will be applied permanently."
systemctl enable --now "${SESSION_NAME}.service"
