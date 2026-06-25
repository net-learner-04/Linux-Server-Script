#!/bin/bash

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