#!/bin/bash

if [ -f "./setup_done" ]
then
    read -r -p "Already done. Continue? (y/n): " answer
    if [ "$answer" != "y" ]
    then
        echo "System exit"
        exit 1
    fi
fi

ROOT=$EUID

if [ "$ROOT" != "0" ]
then
    echo not root
    exit 1
fi

OS_ID=$(awk -F'=' '$1=="ID" {print $2}' /etc/os-release | tr -d '"')
OS_VER=$(awk -F'=' '$1=="VERSION_ID" {print $2}' /etc/os-release | tr -d '"')

if [ "$OS_ID" != "rocky" ]
then
    echo Not Rocky Linux.
    exit 1
fi

TARGET="8.8.8.8"

if ping -c 1 -w 1 "$TARGET" &> /dev/null
then
    echo Internet connection is working properly.
else
    echo Check Your Network Connection.
    exit 1
fi