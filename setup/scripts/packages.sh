#!/bin/bash

echo "Enable the EPEL repository."
# You can easily install useful utilities not found
# in the default repository using the dnf (yum) command.
dnf install epel-release -y
dnf update -y

PACKAGES_LIST=(
    "btop"
    "tmux"
    "vim"
    "git"
    "bash-completion"
    "tree"
    "tcpdump"
    "bind-utils"
    "curl"
    "wget"
    "tar"
    "unzip"
    "fail2ban"
    "net-tools"
    "nmap"
    "traceroute"
)

ERROR_PACKAGES_LIST=()
SECOND_ERROR_PACKAGES_LIST=()

for PKG in "${PACKAGES_LIST[@]}"
do
    echo "Install $PACKAGE"
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