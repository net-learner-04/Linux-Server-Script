#!/bin/bash

SCRIPT_DIR=$(dirname "$(realpath "$0")")
LOG_FILE="$SCRIPT_DIR/setup.log"
SETUP_DONE="$SCRIPT_DIR/.setup_done"

SCRIPTS=(
    "scripts/precheck.sh"
    "scripts/system.sh"
    "scripts/packages.sh"
    "scripts/account.sh"
)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" >&2
}

run_script() {
    local script=$1
    local path="$SCRIPT_DIR/$script"

    if [ ! -f "$path" ]
    then
        log "ERROR: $script not found."
        return 1
    fi

    log "START: $script"
    bash "$path"
    local exit_code=$?

    if [ $exit_code -ne 0 ]
    then
        log "FAILED: $script (exit code: $exit_code)"
        return 1
    fi

    log "SUCCESS: $script"
    return 0
}

if [ -f "$SETUP_DONE" ]
then
    log "Setup already completed. Exiting."
    exit 0
fi

log "Setup started."

for SCRIPT in "${SCRIPTS[@]}"
do
    run_script "$SCRIPT"
    exit_code=$?

    if [ $exit_code -ne 0 ]
    then
        if [ "$SCRIPT" = "scripts/precheck.sh" ]
        then
            log "Precheck failed. Exiting."
            exit 1
        fi

        read -r -p "$SCRIPT failed. Continue? (y/n): " answer
        if [ "$answer" != "y" ]
        then
            log "Setup aborted by user."
            exit 1
        fi
    fi
done

touch "$SETUP_DONE"
log "Setup completed."
