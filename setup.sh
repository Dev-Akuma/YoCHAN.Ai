#!/bin/bash
# =========================================================================
# YO-CHAN! FULL SETUP (For Debian/Ubuntu/Mint Systems)
# =========================================================================

set -e  # stop on first error

echo ""
echo "=============================================="
echo "        Yo-Chan! Full Setup Wizard            "
echo "=============================================="
echo ""

# --- Sanity check: must be in project root ---
if [ ! -f "yochan_listener.py" ]; then
    echo "ERROR: Please run this script from the Yo-Chan project root."
    echo "(The folder containing yochan_listener.py)"
    exit 1
fi

PROJECT_DIR="$(pwd)"

# -----------------------------------------------------
# Helper: ask yes/no
# -----------------------------------------------------
ask_yes_no() {
    local prompt="$1"
    local default="$2"  # y or n
    local answer

    while true; do
        if [ "$default" = "y" ]; then
            read -r -p "$prompt [Y/n]: " answer
            answer="${answer:-Y}"
        else
            read -r -p "$prompt [y/N]: " answer
            answer="${answer:-N}"
        fi

        case "$answer" in
            [Yy]*) return 0 ;;
            [Nn]*) return 1 ;;
        esac
    done
}

# -----------------------------------------------------
# Helper: update or append key=value in .env
# -----------------------------------------------------
update_env_var() {
    local key="$1"
    local value="$2"

    if grep -q "^${key}=" .env 2>/dev/null; then
        # Replace existing line
        sed -i "s|^${key}=.*|${key}=${value}|" .env
    else
        # Append new line
        echo "${key}=${value}" >> .env
    fi
}

# =====================================================
# 1) SYSTEM DEPENDENCIES
# =====================================================
echo ""
echo "1) Installing system dependencies (sudo required)..."
echo ""

sudo apt update

sudo apt install -y \
    python3 \
    python3-venv \
    git \
    libportaudio2 \
    python3-dev \
    libnotify-bin \
    wget \
    unzip \
    alsa-utils \
    xclip

# Try installing xbacklight (optional, for brightness control)
if ! dpkg -s xbacklight >/dev/null 2>&1; then
    sudo apt install -y xbacklight || true
fi

echo ""
echo "[OK] System dependencies installed."
echo ""

# =====================================================
# 2) PYTHON VIRTUAL ENV
# =====================================================
VENV_DIR=".venv"

if [ -d "$VENV_DIR" ]; then
    echo "2) Python virtual environment already exists at $VENV_DIR"
else
    echo "2) Creating Python virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
echo "[OK] Virtual environment activated."
echo ""

# =====================================================
# 3) PYTHON PACKAGES
# =====================================================
echo "3) Installing Python packages in the venv..."
pip install --upgrade pip >/dev/null 2>&1 || true
pip install pvporcupine pvrecorder vosk python-dotenv numpy sounddevice

echo "[OK] Python packages installed."
echo ""

# =====================================================
# 4) DOWNLOAD VOSK MODEL
# =====================================================
echo "4) Checking Vosk model..."

MODEL_DIR="vosk_models"
MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_UNZIPPED_DIR="vosk-model-small-en-us-0.15"
ZIP_FILE="$MODEL_DIR/model.zip"

mkdir -p "$MODEL_DIR"

if [ -d "$MODEL_DIR/$MODEL_UNZIPPED_DIR" ]; then
    echo "[SKIP] Vosk model already present at:"
    echo "       $MODEL_DIR/$MODEL_UNZIPPED_DIR"
else
    echo "Downloading small English Vosk model (~50MB)..."
    # Simple connectivity check
    if ! wget -q --spider https://google.com; then
        echo ""
        echo "ERROR: Internet connection appears unavailable."
        echo "Cannot download the Vosk model automatically."
        echo "You can manually download and extract it into:"
        echo "  $MODEL_DIR/"
        deactivate || true
        exit 1
    fi

    wget -O "$ZIP_FILE" "$MODEL_URL"
    unzip "$ZIP_FILE" -d "$MODEL_DIR"
    rm "$ZIP_FILE"

    echo "[OK] Vosk model installed at:"
    echo "     $MODEL_DIR/$MODEL_UNZIPPED_DIR"
fi

echo ""

# =====================================================
# 5) PREPARE PORCUPINE DIRECTORY
# =====================================================
echo "5) Preparing Porcupine wake-word directory..."

PORCUPINE_DIR="porcupine_models"
mkdir -p "$PORCUPINE_DIR"

echo "[OK] Wake-word directory ready at: $PORCUPINE_DIR/"
echo ""

# =====================================================
# 6) CREATE .env (IF NEEDED)
# =====================================================
if [ -f ".env" ]; then
    echo "6) .env already exists – we will update relevant keys."
else
    echo "6) Creating .env from config.template.env..."
    if [ ! -f "config.template.env" ]; then
        echo "ERROR: config.template.env not found. Cannot create .env."
        deactivate || true
        exit 1
    fi
    cp config.template.env .env
fi

# Set sane default for MODEL_PATH
DEFAULT_MODEL_PATH="$MODEL_DIR/$MODEL_UNZIPPED_DIR"
update_env_var "MODEL_PATH" "$DEFAULT_MODEL_PATH"

# We'll fill WAKE_WORD_PATH after we ask for the .ppn path.

# =====================================================
# 6.5) CREATE yochan_apps.user.json (IF MISSING)
# =====================================================
APPS_FILE="yochan_apps.user.json"

if [ -f "$APPS_FILE" ]; then
    echo "[OK] $APPS_FILE already exists."
else
    echo "[INFO] Creating default $APPS_FILE..."
    echo "{}" > "$APPS_FILE"
    echo "[OK] User app override file created."
fi

# =====================================================
# 7) ASK FOR PICOVOICE ACCESS KEY
# =====================================================
echo ""
echo "7) Picovoice ACCESS_KEY"
echo "You need a Picovoice Console account to get this (for Porcupine)."
echo "If you don't have it yet, you can leave this blank and fill it later."
echo "   Console: https://console.picovoice.ai/"

read -r -p "Enter your Picovoice ACCESS_KEY (or leave blank to skip): " ACCESS_KEY_INPUT

if [ -n "$ACCESS_KEY_INPUT" ]; then
    update_env_var "ACCESS_KEY" "$ACCESS_KEY_INPUT"
    echo "[OK] ACCESS_KEY saved into .env"
else
    echo "[SKIP] ACCESS_KEY not set. You must edit .env before running Yo-Chan."
fi

# =====================================================
# 8) ASK FOR WAKE WORD .PPN PATH
# =====================================================
echo ""
echo "8) Wake-word .ppn file"
echo "If you already downloaded a Porcupine wake-word .ppn file for Yo-Chan,"
echo "enter its full path now and we'll copy it into: $PORCUPINE_DIR/"
echo "If you don't have one yet, just press Enter and you can add it later."

read -r -p "Path to your .ppn file (or leave blank): " PPN_PATH

if [ -n "$PPN_PATH" ]; then
    if [ ! -f "$PPN_PATH" ]; then
        echo "WARNING: File not found: $PPN_PATH"
        echo "Skipping automatic copy. You can manually place the file in $PORCUPINE_DIR/ and edit .env later."
    else
        PPN_BASENAME="$(basename "$PPN_PATH")"
        cp "$PPN_PATH" "$PORCUPINE_DIR/$PPN_BASENAME"
        echo "[OK] Copied wake-word to: $PORCUPINE_DIR/$PPN_BASENAME"
        update_env_var "WAKE_WORD_PATH" "$PORCUPINE_DIR/$PPN_BASENAME"
        echo "[OK] WAKE_WORD_PATH updated in .env"
    fi
else
    echo "[SKIP] No .ppn path provided."
    echo "       Place your .ppn into $PORCUPINE_DIR/ and update WAKE_WORD_PATH in .env later."
fi

# =====================================================
# 9) OPTIONAL: AUTOSTART ON LOGIN
# =====================================================
echo ""
echo "9) Autostart on login (XFCE/Mint/Cinnamon, etc.)"
echo "We can create a desktop autostart entry so Yo-Chan runs automatically"
echo "on login using yochan_startup.sh."

chmod +x "$PROJECT_DIR/yochan_startup.sh" 2>/dev/null || true
chmod +x "$PROJECT_DIR/run_listener.sh" 2>/dev/null || true

if ask_yes_no "Do you want Yo-Chan to start automatically when you log in?" "y"; then
    AUTOSTART_DIR="$HOME/.config/autostart"
    mkdir -p "$AUTOSTART_DIR"

    DESKTOP_FILE="$AUTOSTART_DIR/yochan.desktop"

    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Yo-Chan Assistant
Comment=Local voice assistant for Linux
Exec="$PROJECT_DIR/yochan_startup.sh"
X-GNOME-Autostart-enabled=true
EOF

    echo "[OK] Autostart file created at:"
    echo "     $DESKTOP_FILE"
else
    echo "[SKIP] Autostart not enabled."
fi

# =====================================================
# 10) START YO-CHAN & OPEN CONFIGURATOR
# =====================================================
echo ""
echo "10) Start Yo-Chan now and open the configuration GUI?"

if ask_yes_no "Do you want to start the listener now and open YoChan Configurator?" "y"; then
    echo ""
    echo "[INFO] Starting Yo-Chan listener in the background..."
    # run_listener.sh should already know how to activate venv / run yochan_listener.py
    ./run_listener.sh &

    echo "[INFO] Opening YoChan Configurator (yochan_configurator.py)..."
    if [ -f "yochan_configurator.py" ]; then
        python3 yochan_configurator.py || {
            echo "WARNING: Failed to open configurator. You can run it later with:"
            echo "  source $VENV_DIR/bin/activate && python3 yochan_configurator.py"
        }
    else
        echo "WARNING: yochan_configurator.py not found. You can skip this or add it later."
    fi
else
    echo "[SKIP] Not starting Yo-Chan or configurator automatically."
fi

# =====================================================
# 11) FINALIZE
# =====================================================
deactivate || true

echo ""
echo "=============================================="
echo "          Yo-Chan Setup Complete              "
echo "=============================================="
echo ""
echo "Summary:"
echo " - Venv:            $VENV_DIR"
echo " - Vosk model:      $DEFAULT_MODEL_PATH"
echo " - Wake-word dir:   $PORCUPINE_DIR/"
echo " - .env:            $(readlink -f .env 2>/dev/null || echo "$PROJECT_DIR/.env")"
echo ""
echo "If you didn't set ACCESS_KEY / WAKE_WORD_PATH during setup,"
echo "edit .env now before relying on the assistant."
echo ""
echo "To run Yo-Chan later manually:"
echo "  ./run_listener.sh"
echo ""
echo "To open the GUI configurator manually:"
echo "  source $VENV_DIR/bin/activate"
echo "  python3 yochan_configurator.py"
echo ""
echo "Enjoy Yo-Chan!"