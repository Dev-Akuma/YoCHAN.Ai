#!/usr/bin/env python3
"""
Central configuration for YoChan.

- Loads `.env`
- Provides model / wake word settings
- Provides DE-aware power/logout commands
"""

import os
import sys
import shlex
from pathlib import Path
import re # NEW: For cleaning up the wake word name

from dotenv import load_dotenv  # make sure python-dotenv is installed


# ----------------- Paths & env loading -----------------

BASE_DIR = Path(__file__).resolve().parent

# Load .env from project root explicitly
DOTENV_PATH = BASE_DIR / ".env"
if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH)
else:
    print("[config] Warning: .env file not found in project root.",
          file=sys.stderr)

# ----------------- Vosk / Porcupine settings -----------------

def _autodetect_vosk_model():
    models_root = BASE_DIR / "models"
    if not models_root.is_dir():
        return None

    for child in models_root.iterdir():
        if child.is_dir():
            if "vosk" in child.name.lower():
                return str(child)
    return None


def _autodetect_ppn():
    ppn_root = BASE_DIR / "porcupine_models"
    if not ppn_root.is_dir():
        return None

    for root, dirs, files in os.walk(ppn_root):
        for f in files:
            if f.lower().endswith(".ppn"):
                return str(Path(root) / f)
    return None


MODEL_PATH = os.getenv("MODEL_PATH") or _autodetect_vosk_model()
LISTEN_DURATION = int(os.getenv("LISTEN_DURATION", "5"))
ACCESS_KEY = os.getenv("ACCESS_KEY")
WAKE_WORD_PATH = os.getenv("WAKE_WORD_PATH") or _autodetect_ppn()
FUZZY_THRESHOLD = float(os.getenv("FUZZY_THRESHOLD", "0.7")) # Import and set the new threshold

VOSK_SAMPLE_RATE = 16000  # keep constant for now


# NEW: DYNAMICALLY DETERMINE WAKE WORD NAME
def _get_wake_word_name():
    """Extracts a user-friendly name from the .ppn filename."""
    if not WAKE_WORD_PATH:
        return "Assistant"

    # Get filename (e.g., 'my_custom_name_linux.ppn')
    filename = Path(WAKE_WORD_PATH).name
    
    # Remove common suffixes (_linux, _mac, .ppn)
    name = re.sub(r'(_[a-z]{2,8}|\.ppn)', '', filename, flags=re.IGNORECASE)
    
    # Replace underscores with spaces and capitalize words (My Custom Name)
    return name.replace('_', ' ').strip().title()

# This is the dynamic name used in all notifications and alerts
WAKE_WORD_NAME = _get_wake_word_name()
# This is the user-facing assistant name.
# Priority:
# 1) ASSISTANT_NAME from .env (if set)
# 2) Derived from wake word filename (WAKE_WORD_NAME)
# 3) Plain "Assistant"
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME") or WAKE_WORD_NAME or "Assistant"


def _build_assistant_display_name():
    """
    Build a nice display string for notifications, e.g. "Luna! Assistant".
    """
    base = ASSISTANT_NAME.strip()
    if not base:
        return "Assistant"

    # Add "!" if user didn't already
    if not base.endswith("!"):
        base_exclam = base + "!"
    else:
        base_exclam = base

    return f"{base_exclam} Assistant"


ASSISTANT_DISPLAY_NAME = _build_assistant_display_name()


# --------------- Desktop / power command config ---------------

def _detect_desktop():
    de = os.getenv("XDG_CURRENT_DESKTOP", "") or os.getenv("DESKTOP_SESSION", "")
    return de.lower()


def _default_logout_cmd():
    de = _detect_desktop()

    if "xfce" in de:
        return "xfce4-session-logout --logout --fast"
    if "cinnamon" in de:
        return "cinnamon-session-quit --logout --no-prompt"
    if "gnome" in de:
        return "gnome-session-quit --logout --no-prompt"

    return ""


def _split_cmd(cmd_str, fallback):
    cmd_str = (cmd_str or "").strip()
    if not cmd_str:
        return fallback
    try:
        return shlex.split(cmd_str)
    except ValueError:
        return fallback


SHUTDOWN_CMD = _split_cmd(
    os.getenv("SHUTDOWN_COMMAND"),
    ["systemctl", "poweroff"],
)

REBOOT_CMD = _split_cmd(
    os.getenv("REBOOT_COMMAND"),
    ["systemctl", "reboot"],
)

SUSPEND_CMD = _split_cmd(
    os.getenv("SUSPEND_COMMAND"),
    ["systemctl", "suspend"],
)

LOGOUT_CMD = _split_cmd(
    os.getenv("LOGOUT_COMMAND", _default_logout_cmd()),
    [],
)