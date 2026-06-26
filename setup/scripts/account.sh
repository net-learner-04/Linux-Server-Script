#!/bin/bash

echo "Create a user."
read -r -p "Please enter your username: " username
useradd -m -d /home/"$username" "$username"

echo "Set a password for your user account."
passwd "$username"
passwd -w 5 -n 3 -x 31 "$username"

echo "Grant 'sudo' privileges."
usermod -aG wheel "$username"

echo "Verify your newly created user account."
su - "$username" -c "sudo whoami"

echo "Change the SSH remote connection settings."
TARGET="/etc/ssh/sshd_config"

if grep -qwi "#PermitRootLogin no" "$TARGET"
then
    sed -i '/#PermitRootLogin no/s/^[[:space:]]*#[[:space:]]*//' "$TARGET"
elif grep -qwi "PermitRootLogin yes" "$TARGET"
then
    sed -i '/PermitRootLogin yes/ c\PermitRootLogin no' "$TARGET"
elif ! grep -qwi "#PermitRootLogin no" "$TARGET" && ! grep -qwi "PermitRootLogin no" "$TARGET"
then
cat << 'EOF' >> "$TARGET"
PermitRootLogin no
EOF
fi

echo "Change the SSH 22 port to a random value."

NUMBER=$(shuf -i 1024-65535 -n 1)

if grep -qwi "#Port 22" "$TARGET"
then
    sed -i '/#Port 22/s/^[[:space:]]*#[[:space:]]*//' "$TARGET"
    sed -i "/Port 22/ c\Port $NUMBER" "$TARGET"
elif ! grep -qwi "#Port 22" "$TARGET" && ! grep -qwi "Port 22" "$TARGET"
then
    if [ -f "$TARGET" ]
    then
    cat << EOF >> "$TARGET"
Port $NUMBER
EOF
    fi
fi

echo "Register a new SSH port with SELinux."
semanage port -a -t ssh_port_t -p tcp "$NUMBER"

echo "Register a new SSH port with firewalld."
firewall-cmd --permanent --add-port="$NUMBER"/tcp
firewall-cmd --reload

echo "Restart the sshd service."
systemctl restart sshd

echo "=========================================================="
echo "Registering a Public Key on a Client PC (Not the Server)."
echo "=========================================================="
echo "1. Open a new terminal on your CLIENT PC (Windows/Mac/Linux)."
echo "2. Run the following command to copy your public key to the server:"
echo "   ssh-copy-id -p $NUMBER $username@[SERVER_IP]"
echo "3. Enter the user's password when prompted."
echo "4. Verify you can log in without a password: ssh -p [NEW_PORT] [USERNAME]@[SERVER_IP]"
echo "=========================================================="

read -r -p "Have you successfully registered and verified your public key? (y/n): " CONFIRM1

if [ "$CONFIRM1" = "y" ]
then
    read -r -p "Did you actually verify that the connection using the public key was successful? (y/n): " CONFIRM2
    if [ "$CONFIRM2" = "y" ]
    then
        if grep -qwi "#PasswordAuthentication no" "$TARGET"
        then
            sed -i '/#PasswordAuthentication no/s/^[[:space:]]*#[[:space:]]*//' "$TARGET"
        elif grep -qwi "PasswordAuthentication yes" "$TARGET"
        then
            sed -i '/PasswordAuthentication yes/ c\PasswordAuthentication no' "$TARGET"
        elif ! grep -qwi "#PasswordAuthentication no" "$TARGET" && ! grep -qwi "PasswordAuthentication no" "$TARGET"
        then
        cat << 'EOF' >> "$TARGET"
PasswordAuthentication no
EOF
        fi
        echo "Restart the sshd service."
        systemctl restart sshd
    fi
fi
