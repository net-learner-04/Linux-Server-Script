#!/bin/bash

echo "Enable the EPEL repository."
# You can easily install useful utilities not found
# in the default repository using the dnf (yum) command.
dnf install epel-release -y
dnf update -y

PACKAGES_LIST=(
    # [Core Tools & Utilities]
    "btop" "mdadm" "tmux" "vim" "git" "tree" "bash-completion"
    "curl" "wget" "tar" "unzip" "policycoreutils-python-utils"
    "smartmontools"

    # [Security & Access Control]
    "fail2ban"

    # [Networking & Troubleshooting]
    "net-tools" "nmap" "tcpdump" "traceroute" "bind-utils"
    "wireshark-cli"       # tshark: Advanced packet and protocol parsing via CLI
    "iperf3"              # Network bandwidth and segment performance measurement
    "socat"               # Multipurpose relay tool for bidirectional data streams

    # [System Performance & Diagnosis]
    "sysstat"             # iostat, sar: Disk and system performance statistics
    "iotop"               # Monitor and display real-time disk I/O usage by processes
    "lsof"                # List open files and associated network sockets
    "strace"              # Trace system calls (POSIX APIs) and signals of a process

    # [Data Backup & Hardware Detection]
    "rsync"               # Fast and incremental file transfer/backup utility
    "pciutils"            # lspci: Verify hardware devices recognized by the kernel
)

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
