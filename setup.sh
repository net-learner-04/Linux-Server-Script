#!/bin/bash

clear

PACKAGES_LIST=(
    "btop" "mdadm" "tmux" "vim" "git" "tree" "bash-completion"
    "curl" "wget" "tar" "unzip" "policycoreutils-python-utils"
    "smartmontools" "fail2ban" "net-tools" "nmap" "tcpdump" 
    "traceroute" "bind-utils" "iperf3" "socat" "sysstat" "iotop"
    "lsof" "strace" "rsync" "pciutils" 
)

# SCRIPT_DIR=$(dirname "$(realpath "$0")")


if [ -f "./setup_done" ]
then
    read -r -p "Already done. Continue? (y/n): " answer
    if [ "$answer" != "y" ]
    then
        echo "System exit"
        exit 1
    fi
fi


if [ "$EUID" -ne 0 ] || [ -n "$SUDO_USER" ]
then
    echo "You must log in directly as the root user."
    exit 1
fi

OS_NAME=$(awk -F'=' '$1=="ID" {print $2}' /etc/os-release | tr -d '"')

if [ "$OS_NAME" != "rocky" ]
then
    echo "Cannot run because the operating system is not Rocky Linux."
    exit 1
fi


if ping -c 1 -w 1 8.8.8.8 &> /dev/null
then
    echo "Internet connection is working properly."
else
    echo "Check Your Network Connection."
    exit 1
fi


echo "Set the hostname."

read -r -p "Enter the hostname (You can skip by pressing Enter.): " hostname

if [ -z "$hostname" ]
then
    echo "Hostname is empty. skipping."
else
    if hostnamectl set-hostname "$hostname"
    then
        echo "Hostname set to $hostname"
    else
        echo "Failed to set hostname."
    fi
fi


echo "set the timezone."

timedatectl set-timezone Asia/Seoul


echo "set the locale."

localectl set-locale LANG=en_US.UTF-8


read -r -p "Would you like to enable additional software package \
repositories for your Linux distribution? (y/n): " epel_answer

if [ "$epel_answer" == "y" ]
then
    echo "Enable the EPEL repository."
    dnf install epel-release -y
    dnf update -y
else
    dnf update -y
fi


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


echo "Create a Linux account."

read -r -p "Enter the name you want to use as your user account name: " username

useradd -m -d /home/"$username" "$username"

if id "$username" &>/dev/null
then
    echo "User already exists."
    exit 1
fi


echo "Set a password for your Linux account."

passwd "$username"

if ! passwd "$username"
then
    echo "Password setup failed."
    exit 1
fi

passwd -w 5 -n 3 -x 31 "$username"


echo "Grant 'sudo' privileges."

usermod -aG wheel "$username"


echo "Change the SSH remote connection settings."

SSH_CONF="/etc/ssh/sshd_config"

if grep -qwi "#PermitRootLogin no" "$SSH_CONF"
then
    sed -i '/#PermitRootLogin no/s/^[[:space:]]*#[[:space:]]*//' "$SSH_CONF"
elif grep -qwi "PermitRootLogin yes" "$SSH_CONF"
then
    sed -i '/PermitRootLogin yes/ c\PermitRootLogin no' "$SSH_CONF"
elif ! grep -qwi "#PermitRootLogin no" "$SSH_CONF" && ! grep -qwi "PermitRootLogin no" "$SSH_CONF"
then
cat << 'EOF' >> "$SSH_CONF"
PermitRootLogin no
EOF
fi


echo "Change the SSH 22 port to a random value."

while :
do
    RAND_NUMBER=$(shuf -i 1024-65535 -n 1)
    ss -tln | grep -q ":$RAND_NUMBER " || break
done

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


read -r -p "Would you like to set a bootloader password? (y/n): " boot_answer

GRUB_CONF="/boot/efi/EFI/rocky/grub.cfg"

if [ "$boot_answer" == 'y' ]
then
    echo "Set the bootloader password."
    GRUB_HASH_PASSWD=$(grub2-mkpasswd-pbkdf2 | awk '/grub.pbkdf2/ {print $NF}')
    
    cat << EOF >> "$GRUB_CONF"
password --encrypted "$GRUB_HASH_PASSWD"
EOF
else
    echo "Skip bootloader password."
fi


read -r -p "Apply recommended kernel/network security hardening (sysctl)? (y/n): " sysctl_answer

if [ "$sysctl_answer" == 'y' ]
then
    echo "Apply sysctl hardening settings."
    
    read -r -p "Do you want to change the local port range? (y/n): " port_change_answer
    
    if [ "$port_change_answer" == 'y' ]
    then
        read -r -p "Local port range (default: 32768 60999): " PORT_RANGE
        PORT_RANGE=${PORT_RANGE:-"32768 60999"}
    fi

    SYSCTL_CONF="/etc/sysctl.d/99-hardening.conf"
 
    cat << EOF > "$SYSCTL_CONF"
# Disable TCP timestamps (prevents remote uptime fingerprinting, etc.)
net.ipv4.tcp_timestamps = 0

# Enable SYN cookies to defend against SYN flood attacks
net.ipv4.tcp_syncookies = 1

# Ignore all ICMP echo (ping) requests
net.ipv4.icmp_echo_ignore_all = 1

# Ignore ICMP requests sent to broadcast addresses (prevents Smurf attacks)
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Timeout (seconds) for sockets in FIN-WAIT state - frees up resources faster
net.ipv4.tcp_fin_timeout = 30

# Idle time (seconds) before sending the first TCP keepalive probe
net.ipv4.tcp_keepalive_time = 600

# Range of local ports available for outgoing connections (adjust per environment)
net.ipv4.ip_local_port_range = $PORT_RANGE

# Disable packet forwarding unless this host is a router
net.ipv4.ip_forward = 0
EOF
    sysctl --system
else
    echo "Skip sysctl hardening."
fi


SE_STATUS=$(sestatus | grep "Current mode" | awk '{print $NF}')

if [ "$SE_STATUS" != "enforcing" ]
then
    echo "Change SELinux's enforcement mode to 'enforce'."
    setenforce enforcing
    sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config
fi


clear

SUMMARY="./summary.txt"

{
echo "========== Setup Summary =========="
echo

echo "Hostname"
echo "  $hostname"
echo

echo "User"
echo "  $username"
echo

echo "Timezone"
echo "  $(timedatectl show --property=Timezone --value)"
echo

echo "Locale"
echo "  $(localectl status | grep "System Locale")"
echo

echo "SSH Port"
echo "  $RAND_NUMBER"
echo

echo "SELinux"
echo "  $(getenforce)"
echo

echo "EPEL"
if [ "$epel_answer" = "y" ]
then
    echo "  Enabled"
else
    echo "  Disabled"
fi
echo

echo "Bootloader Password"
if [ "$boot_answer" = "y" ]
then
    echo "  Configured"
else
    echo "  Not Configured"
fi
echo

echo "Sysctl Hardening"
if [ "$sysctl_answer" = "y" ]
then
    echo "  Applied"
    echo "  Local Port Range : $PORT_RANGE"
else
    echo "  Not Applied"
fi
echo

echo "Installed Packages"

for PKG in "${PACKAGES_LIST[@]}"
do
    rpm -q "$PKG" &>/dev/null &&
        echo "  [OK] $PKG" ||
        echo "  [FAIL] $PKG"
done

echo

echo "Failed Packages"

if [ "${#SECOND_ERROR_PACKAGES_LIST[@]}" -eq 0 ]
then
    echo "  None"
else
    for PKG in "${SECOND_ERROR_PACKAGES_LIST[@]}"
    do
        echo "  $PKG"
    done
fi

echo
echo "=================================="

} | tee "$SUMMARY"
