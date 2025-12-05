#!/bin/bash
# =========================================================================
# YO-CHAN! SETUP SCRIPT (For Debian/Ubuntu/Mint Systems)
# =========================================================================

# Exit immediately if a command exits with a non-zero status
set -e

echo "--- Yo-Chan! Universal Setup Starting ---"

# --- 1. INSTALL SYSTEM DEPENDENCIES ---
echo "1. Installing core system dependencies (sudo required)..."
sudo apt update
# libportaudio2: Required by PvRecorder/sounddevice
# python3-dev: Required to compile Python packages that use C extensions
# libnotify-bin: Required for desktop notifications (notify-send)
sudo apt install -y libportaudio2 python3-dev libnotify-bin wget unzip

# --- 2. PYTHON VIRTUAL ENVIRONMENT ---
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "2. Creating Python virtual environment ($VENV_DIR)..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# --- 3. PYTHON PACKAGE INSTALLATION ---
echo "3. Installing Python packages into the virtual environment..."
pip install pvporcupine pvrecorder vosk python-dotenv numpy sounddevice

# --- 4. VOSK MODEL DOWNLOAD ---
MODEL_URL="http://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_UNZIPPED_DIR="vosk-model-small-en-us-0.15"
MODEL_DIR="vosk_models"
ZIP_FILE="$MODEL_DIR/model.zip"

mkdir -p "$MODEL_DIR"

if [ ! -d "$MODEL_DIR/$MODEL_UNZIPPED_DIR" ]; then
    echo "4. Downloading and unzipping Vosk model (~50MB)..."
    wget -O "$ZIP_FILE" "$MODEL_URL"
    unzip "$ZIP_FILE" -d "$MODEL_DIR"
    rm "$ZIP_FILE"
    echo "Vosk model successfully installed in $MODEL_DIR/$MODEL_UNZIPPED_DIR."
else
    echo "Vosk model already exists. Skipping download."
fi

# --- 5. CLEANUP AND FINAL INSTRUCTIONS ---
echo "5. Creating configuration file template..."
if [ ! -f ".env" ]; then
    cp config.template.env .env
    echo "Copied config.template.env to .env. Please edit it!"
fi

echo "--- Setup Complete! ---"
echo "NEXT STEPS:"
echo "1. Put your Yo-Chan!.ppn file into a folder named 'porcupine_models'."
echo "2. Edit the generated .env file with your Access Key and the correct paths."
echo "3. Run the autostart command manually to test (./run_listener.sh)."

deactivate # Deactivate venv after script finishes

# Make the run listener script executable
chmod +x ./run_listener.sh