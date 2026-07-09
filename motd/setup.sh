#!/bin/bash

# Exit immediately if any command fails
set -e

# Verify Root Permissions.
if [ "$EUID" -ne 0 ]
then
    echo "Error: Run as root."
    exit 1
fi

MOTD_PATH="/opt/motd-dashboard"

# Create the deployment directory (no error if it already exists)
mkdir -p "$MOTD_PATH"

# Copy project files and env config to the deployment directory
cp -f main.py weather.py system.py ascii_art.py display.py .env "$MOTD_PATH"

# Restrict .env permissions since it contains the API key
chmod 600 "$MOTD_PATH/.env"

# The hook below runs as the logging-in user, not root,
# so a dedicated group is needed for read access to .env
GROUP_NAME="motd-dashboard"

# Create the group if it does not already exist
if ! getent group "$GROUP_NAME" > /dev/null 2>&1; then
    groupadd "$GROUP_NAME"
fi

# Add every regular login user (UID >= 1000) to the group
for user in $(awk -F: '$3 >= 1000 && $3 < 60000 {print $1}' /etc/passwd); do
    usermod -aG "$GROUP_NAME" "$user"
done

# Hand .env over to the group and allow group-read only
chown root:"$GROUP_NAME" "$MOTD_PATH/.env"
chmod 640 "$MOTD_PATH/.env"

# Deployment directory must be traversable by the group as well
chgrp "$GROUP_NAME" "$MOTD_PATH"
chmod 750 "$MOTD_PATH"

# Create an isolated virtual environment inside the deployment directory
python3 -m venv "$MOTD_PATH"/venv

# Install required Python packages into the virtual environment
"$MOTD_PATH/venv/bin/pip" install rich requests python-dotenv psutil

# Create a login-shell hook that runs main.py on every SSH/local login
cat <<EOF > /etc/profile.d/motd.sh
#!/bin/bash

$MOTD_PATH/venv/bin/python3 $MOTD_PATH/main.py
EOF

# Make the hook script executable
chmod +x /etc/profile.d/motd.sh

# Run once immediately to verify everything works
echo "Testing installation..."
"$MOTD_PATH/venv/bin/python3" "$MOTD_PATH/main.py"

# New group membership only takes effect after re-login
echo "Note: users added to '$GROUP_NAME' must log out and back in for group changes to apply."
