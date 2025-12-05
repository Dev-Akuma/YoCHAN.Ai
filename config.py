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

from dotenv import load_dotenv  # make sure python-dotenv is installed


# ----------------- Paths & env loading -----------------

BASE_DIR = Path(__file__).resolve().parent

# Load .env from project root explicitly
DOTENV_PATH = BASE_DIR / ".env"
if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH)
else:
    # We don't hard-fail if .env is missing – but some features will.
    print("[Yo-Chan][config] Warning: .env file not found in project root.",
          file=sys.stderr)


# ----------------- Vosk / Porcupine settings -----------------

def _autodetect_vosk_model():
    """
    If MODEL_PATH is not set, try to discover a Vosk model directory under ./models/.
    """
    models_root = BASE_DIR / "models"
    if not models_root.is_dir():
        return None

    # Return first directory that contains 'vosk' in name or has 'am' subdir etc.
    for child in models_root.iterdir():
        if child.is_dir():
            # Very simple heuristic – you can make this smarter later
            if "vosk" in child.name.lower():
                return str(child)
    return None


def _autodetect_ppn():
    """
    If WAKE_WORD_PATH is not set, try to find any .ppn under ./porcupine_models/.
    """
    ppn_root = BASE_DIR / "porcupine_models"
    if not ppn_root.is_dir():
        return None

    for root, dirs, files in os.walk(ppn_root):
        for f in files:
            if f.lower().endswith(".ppn"):
                return str(Path(root) / f)
    return None


MODEL_PATH = os.getenv("MODEL_PATH") or _autodetect_vosk_model()
LISTEN_DURATION = int(os.getenv("LISTEN_DURATION", "3"))
ACCESS_KEY = os.getenv("ACCESS_KEY")
WAKE_WORD_PATH = os.getenv("WAKE_WORD_PATH") or _autodetect_ppn()

VOSK_SAMPLE_RATE = 16000  # keep constant for now


# --------------- Desktop / power command config ---------------

def _detect_desktop():
    """
    Return lowercased desktop name from XDG_CURRENT_DESKTOP, e.g. 'xfce', 'gnome'.
    """
    de = os.getenv("XDG_CURRENT_DESKTOP", "") or os.getenv("DESKTOP_SESSION", "")
    return de.lower()


def _default_logout_cmd():
    de = _detect_desktop()

    # naive mapping – can be extended later
    if "xfce" in de:
        return "xfce4-session-logout --logout --fast"
    if "cinnamon" in de:
        return "cinnamon-session-quit --logout --no-prompt"
    if "gnome" in de:
        # --no-prompt to avoid confirmation dialog
        return "gnome-session-quit --logout --no-prompt"

    # Fallback – no-op; you can change this to something else later
    return ""


def _split_cmd(cmd_str, fallback):
    """
    Parse a shell-like command string into a list for subprocess.
    """
    cmd_str = (cmd_str or "").strip()
    if not cmd_str:
        return fallback
    try:
        return shlex.split(cmd_str)
    except ValueError:
        return fallback


# Allow overriding via .env – but give sensible defaults
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
    [],  # empty fallback = effectively "no logout"
)
