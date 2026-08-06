#!/bin/bash

clear; echo

# Verify Root Permissions.
if [ "$EUID" -ne 0 ]; then
    echo "Run as root."
    exit 1
fi

cat << "EOF"                                                   
 ____    __           __      __            __                
/\  _`\ /\ \__       /\ \  __/\ \          /\ \               
\ \ \L\ \ \ ,_\   ___\ \ \/\ \ \ \     __  \ \ \/'\      __   
 \ \ ,  /\ \ \/  /'___\ \ \ \ \ \ \  /'__`\ \ \ , <    /'__`\ 
  \ \ \\ \\ \ \_/\ \__/\ \ \_/ \_\ \/\ \L\.\_\ \ \\`\ /\  __/ 
   \ \_\ \_\ \__\ \____\\ `\___x___/\ \__/.\_\\ \_\ \_\ \____\
    \/_/\/ /\/__/\/____/ '\/__//__/  \/__/\/_/ \/_/\/_/\/____/
                                                                                                                                         
EOF

CURRENT_DATE=$(date +"%Y-%m-%d %H:%M:%S")

echo "Current date: $CURRENT_DATE"; echo

echo "When should the computer shut down?"
read -r -p "Type 'now' or an exact time later today, format -> HH:MM:SS: " OFF_TIME; echo

if [ "$OFF_TIME" != "now" ]; then
    # Check the shutdown time format matches HH:MM:SS
    if ! [[ "$OFF_TIME" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
        echo "Invalid time format. Please use HH:MM:SS."
        exit 1
    fi

    # Check the shutdown time isn't already in the past/
    NOW_EPOCH=$(date +%s)

    OFF_EPOCH=$(date -d "$CURRENT_DATE $OFF_TIME" +%s 2>/dev/null)

    if [ -z "$OFF_EPOCH" ]; then
        echo "Invalid time value. Please check and try again."
        exit 1
    fi

    if [ "$OFF_EPOCH" -lt "$NOW_EPOCH" ]; then
        echo "The shutdown time can't be in the past."
        exit 1
    fi
fi

echo "Enter the date the computer should wake up."
read -r -p "format -> YYYY-MM-DD: " ON_DATE; echo

# Check the format matches YYYY-MM-DD
if ! [[ "$ON_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Invalid date format. Please use YYYY-MM-DD."
    exit 1
fi

# Check that it's an actual, real calendar date.
if ! date -d "$ON_DATE" >/dev/null 2>&1; then
    echo "That date doesn't exist. Please check and try again."
    exit 1
fi

# Check that it's not in the past.
TODAY_EPOCH=$(date -d "$CURRENT_DATE" +%s)

ON_DATE_EPOCH=$(date -d "$ON_DATE" +%s)

if [ "$ON_DATE_EPOCH" -lt "$TODAY_EPOCH" ]; then
    echo "The wake-up date can't be earlier than today ($CURRENT_DATE)."
    exit 1
fi

echo "Enter the time the computer should wake up"
read -r -p "format -> HH:MM:SS, (ex: 09:00:00): " ON_TIME; echo

# Check the time format matches HH:MM:SS
if ! [[ "$ON_TIME" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
    echo "Invalid time format. Please use HH:MM:SS."
    exit 1
fi

# Check the full wake-up datetime isn't in the past
NOW_EPOCH=$(date +%s)

WAKE_EPOCH=$(date -d "$ON_DATE $ON_TIME" +%s 2>/dev/null)

if [ -z "$WAKE_EPOCH" ]; then
    echo "Invalid time value. Please check and try again."
    exit 1
fi

if [ "$WAKE_EPOCH" -lt "$NOW_EPOCH" ]; then
    echo "The wake-up time can't be in the past."
    exit 1
fi

# The actual logic behind the execution of the rtcwake command.
if [ "$OFF_TIME" = "now" ]; then
    rtcwake -m off --date "$ON_DATE $ON_TIME"
else
    # Check if the atd service is running; if it's not, start it.
    if ! systemctl is-active --quiet atd; then
        echo "atd daemon is not running. Starting atd service."
        
        systemctl start atd
        systemctl enable atd >/dev/null 2>&1
    fi
    
    # The -M option prevents emails from being sent.
    echo "rtcwake -m off --date '$ON_DATE $ON_TIME'" | at -M "$OFF_TIME"
fi

echo "Shutdown and wake-up schedule set successfully."; echo
