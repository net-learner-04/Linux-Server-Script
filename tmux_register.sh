#!/bin/bash

# If you continue to encounter errors even though the parameters you entered are correct, 
# you need to modify the SELinux label for the tmux binary.
# [ The command below is used to edit a label. ]
# sudo semanage fcontext -a -t bin_t /usr/bin/tmux
# sudo restorecon -v /usr/bin/tmux

clear
echo

if [ "$EUID" -ne 0 ]; then
    echo "Run as root."
    exit 1
fi

read -r -p "Enter the absolute path of the script to be executed: " FILE_PATH
echo

read -r -p "Does the command you want to run require root privileges? (y/n): " USER_CHECK
echo

if [ "$USER_CHECK" = "y" ]; then
    LOGIN_USER="root"
else
    LOGIN_USER=${SUDO_USER:-$LOGNAME}
fi

# If the file the user wants to run does not exist, terminate the process.
if [ ! -f "$FILE_PATH" ]; then
    echo "File not found. Please check the path."
    exit 1
fi

read -r -p "Please enter the name of the program to run the file (example -> python3): " COMMAND_NAME
echo

TMUX_PATH=$(which tmux 2>/dev/null)

if [ -n "$TMUX_PATH" ]; then
    TMUX_PATH=$(realpath "$TMUX_PATH")
fi

if [ -z "$TMUX_PATH" ] || [ ! -x "$TMUX_PATH" ]; then
    echo "tmux is not installed."
    exit 1
fi

if [[ "$COMMAND_NAME" != /* ]]; then
    if [ -x "/usr/bin/$COMMAND_NAME" ]; then
        COMMAND_NAME="/usr/bin/$COMMAND_NAME"
    else
        RESOLVED_CMD=$(which "$COMMAND_NAME" 2>/dev/null)
        if [ -n "$RESOLVED_CMD" ]; then
            COMMAND_NAME=$(realpath "$RESOLVED_CMD")
        fi
    fi
else
    COMMAND_NAME=$(realpath "$COMMAND_NAME")
fi

read -r -p "Enter a tmux session name: " SESSION_NAME
echo

SYSTEMD_FILE_PATH="/etc/systemd/system/${SESSION_NAME}.service"

cat << EOF > "$SYSTEMD_FILE_PATH"
[Unit]
Description=Auto Start Tmux Session on Boot
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$LOGIN_USER
ExecStart=$TMUX_PATH new-session -d -s "$SESSION_NAME" "$COMMAND_NAME $FILE_PATH"
ExecStop=$TMUX_PATH kill-session -t "$SESSION_NAME"

[Install]
WantedBy=multi-user.target
EOF

echo "Restart the systemd daemon to save the settings."
systemctl daemon-reload

echo "The service you created will be applied permanently."
systemctl enable --now "${SESSION_NAME}.service"

if [ $? -eq 0 ]; then
    echo "Service registration is complete."
    exit 0
else
    echo "Service registration failed."
    
    read -r -p "Would you like to delete the .service file you created? (y/n): " SELECT

    if [ "$SELECT" = "y" ]; then
        echo "Delete the .service file."
        rm -f "$SYSTEMD_FILE_PATH"
        exit 1
    else
        exit 1
    fi
fi
