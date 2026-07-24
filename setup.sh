#!/bin/bash

clear

PACKAGES_LIST=(
    "btop" "mdadm" "tmux" "vim" "git" "tree" "bash-completion"
    "curl" "wget" "tar" "unzip" "policycoreutils-python-utils"
    "smartmontools" "fail2ban" "net-tools" "nmap" "tcpdump" 
    "traceroute" "bind-utils" "iperf3" "socat" "sysstat" "iotop"
    "lsof" "strace" "rsync" "pciutils"
)

SCRIPT_DIR=$(dirname "$(realpath "$0")")

ROOT=$EUID

OS_ID=$(awk -F'=' '$1=="ID" {print $2}' /etc/os-release | tr -d '"')

# OS_VER=$(awk -F'=' '$1=="VERSION_ID" {print $2}' /etc/os-release | tr -d '"')

GOOGLE_IP="8.8.8.8"

SSH_CONF="/etc/ssh/sshd_config"

RAND_NUMBER=$(shuf -i 1024-65535 -n 1)


if [ -f "./setup_done" ]
then
    read -r -p "Already done. Continue? (y/n): " answer
    if [ "$answer" != "y" ]
    then
        echo "System exit"
        exit 1
    fi
fi


if [ "$EUID" != "0" ]
then
    echo not root
    exit 1
fi

if [ "$OS_ID" != "rocky" ]
then
    echo Not Rocky Linux.
    exit 1
fi


if ping -c 1 -w 1 "$GOOGLE_IP" &> /dev/null
then
    echo Internet connection is working properly.
else
    echo Check Your Network Connection.
    exit 1
fi


echo "Set the hostname."

read -r -p "Enter the hostname: " hostname

if [ -z "$hostname" ]
then
    echo "Hostname is empty. skipping."
else
    hostnamectl set-hostname "$hostname"
    echo "Hostname set to $hostname"
fi


echo "set the timezone."

timedatectl set-timezone Asia/Seoul

echo "set the locale."

localectl set-locale LANG=en_US.UTF-8

read -r -p "If you want dnf update? (y/n): " answer

if [ "$answer" = "y" ]
then
    echo "Start dnf update."
    dnf update -y
fi


echo "Enable the EPEL repository."

# You can easily install useful utilities not found
# in the default repository using the dnf (yum) command.
dnf install epel-release -y

dnf update -y


ERROR_PACKAGES_LIST=()

SECOND_ERROR_PACKAGES_LIST=()

for PKG in "${PACKAGES_LIST[@]}"
do
    echo "Install $PKG"
    
    if ! dnf install -y "$PKG"
    then
        ERROR_PACKAGES_LIST+=("$PKG")
    fi
    
done

if [ "${#ERROR_PACKAGES_LIST[@]}" -gt 0 ]
then
    read -r -p "There is a failed package. Would you like to reinstall it? (y/n): " answer
    
    if [ "$answer" = "y" ]
    then
        for PKG in "${ERROR_PACKAGES_LIST[@]}"
        do
            if ! dnf install -y "$PKG"
            then
                SECOND_ERROR_PACKAGES_LIST+=("$PKG")
            fi
        done
    fi
fi

if [ "${#SECOND_ERROR_PACKAGES_LIST[@]}" -gt 0 ]
then
    echo "Final failed packages:"
    
    for PKG in "${SECOND_ERROR_PACKAGES_LIST[@]}"
    do
        echo "  - $PKG"
    done
fi


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

if grep -qwi "#PermitRootLogin no" "$SSH_CONF"
then
    sed -i '/#PermitRootLogin no/s/^[[:space:]]*#[[:space:]]*//' "$SSH_CONF"
elif grep -qwi "PermitRootLogin yes" "$SSH_CONF"
then
    sed -i '/PermitRootLogin yes/ c\PermitRootLogin no' "$SSH_CONF"
elif ! grep -qwi "#PermitRootLogin no" "$SSH_CONF" && ! grep -qwi "PermitRootLogin no" "$SSH_CONF"
then
cat << 'EOF' >> "$TARGET"
PermitRootLogin no
EOF
fi


echo "Change the SSH 22 port to a random value."

if grep -qwi "#Port 22" "$SSH_CONF"
then
    sed -i '/#Port 22/s/^[[:space:]]*#[[:space:]]*//' "$SSH_CONF"
    sed -i "/Port 22/ c\Port $RAND_NUMBER" "$SSH_CONF"
elif ! grep -qwi "#Port 22" "$SSH_CONF" && ! grep -qwi "Port 22" "$SSH_CONF"
then
    if [ -f "$SSH_CONF" ]
    then
    cat << EOF >> "$SSH_CONF"
Port $RAND_NUMBER
EOF
    fi
fi


echo "Register a new SSH port with SELinux."

semanage port -a -t ssh_port_t -p tcp "$RAND_NUMBER"


echo "Register a new SSH port with firewalld."

firewall-cmd --permanent --add-port="$RAND_NUMBER"/tcp

firewall-cmd --reload


echo "Restart the sshd service."

systemctl restart sshd


echo "=========================================================="
echo "Registering a Public Key on a Client PC (Not the Server)."
echo "=========================================================="
echo "1. Open a new terminal on your CLIENT PC (Windows/Mac/Linux)."
echo "2. Run the following command to copy your public key to the server:"
echo "   ssh-copy-id -p $RAND_NUMBER [$username]@[SERVER_IP]"
echo "3. Enter the user's password when prompted."
echo "4. Verify you can log in without a password: ssh -p [NEW_PORT] [$username]@[SERVER_IP]"
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
