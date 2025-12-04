#!/bin/bash
# yochan_startup.sh - Script to auto-run Yo-Chan listener in its virtual environment

# --- CONFIGURATION ---
PROJECT_DIR="/home/dev-akuma/Lnx-Flash Drive/Projects/YoCHAN"
VENV_PYTHON_PATH="${PROJECT_DIR}/.venv/bin/python"
LISTENER_SCRIPT="yochan_listener.py"
LOG_FILE="${PROJECT_DIR}/yochan_startup.log" # New log file

# 1. Start logging
echo "--- $(date) ---" >> "$LOG_FILE"
echo "Starting Yo-Chan! Listener..." >> "$LOG_FILE"

# 2. Change to the script's directory and log the change
cd "$PROJECT_DIR" 2>> "$LOG_FILE" || { echo "ERROR: Could not change directory to $PROJECT_DIR" >> "$LOG_FILE"; exit 1; }

# 3. Check for the VENV Python Path
if [ ! -f "$VENV_PYTHON_PATH" ]; then
    echo "FATAL ERROR: Venv Python executable not found at $VENV_PYTHON_PATH" >> "$LOG_FILE"
    exit 1
fi
echo "Venv Path verified." >> "$LOG_FILE"

# 4. Run the listener script using the VENV's Python interpreter
# Send stdout/stderr from the listener into the log file as well.
# This command runs in the background.
nohup "$VENV_PYTHON_PATH" "$LISTENER_SCRIPT" >> "$LOG_FILE" 2>&1 &

echo "Listener process detached to background." >> "$LOG_FILE"

exit 0