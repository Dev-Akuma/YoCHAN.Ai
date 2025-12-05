#!/bin/bash
# yochan_startup.sh - Script to auto-run Yo-Chan listener in its virtual environment

set -e

# 1. Resolve project directory dynamically (folder containing this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

VENV_PYTHON_PATH="${PROJECT_DIR}/.venv/bin/python"
LISTENER_SCRIPT="yochan_listener.py"
LOG_FILE="${PROJECT_DIR}/yochan_startup.log"

# 2. Start logging
echo "--- $(date) ---" >> "$LOG_FILE"
echo "Starting Yo-Chan! Listener..." >> "$LOG_FILE"

# 3. Change to the project directory
cd "$PROJECT_DIR" 2>> "$LOG_FILE" || {
    echo "ERROR: Could not change directory to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# 4. Check for the venv Python path
if [ ! -f "$VENV_PYTHON_PATH" ]; then
    echo "FATAL ERROR: Venv Python executable not found at $VENV_PYTHON_PATH" >> "$LOG_FILE"
    exit 1
fi
echo "Venv path verified." >> "$LOG_FILE"

# 5. Run the listener script using the venv's Python interpreter in background
nohup "$VENV_PYTHON_PATH" "$LISTENER_SCRIPT" >> "$LOG_FILE" 2>&1 &

echo "Listener process detached to background." >> "$LOG_FILE"

exit 0
