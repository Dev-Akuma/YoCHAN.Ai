#!/bin/bash
# run_listener.sh - Executes the main listener script using the virtual environment.

# Exit immediately if anything fails
set -e

# Path to the virtual environment's Python binary
VENV_PYTHON="./.venv/bin/python"

# Check if the virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "FATAL ERROR: Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

# Execute the main Python script using the venv's Python
# The '&' is usually added by the autostart manager, but we include it here for manual testing.
"$VENV_PYTHON" yochan_listener.py &