from __future__ import annotations
import subprocess
import shlex
import sys
import os

from apps import APP_COMMANDS

DEBUG = True

def notify(stage: str, message: str, critical: bool = False):
    print(f"[{stage}] {message}")
    if critical:
        try:
            subprocess.Popen(["notify-send", "YoChan", f"[{stage}] {message}"])
        except Exception:
            pass

def run(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Done."
    except Exception as e:
        return str(e)

# ---------------- Volume ----------------

def handle_volume(relative=None):
    if subprocess.getstatusoutput("which pactl")[0] == 0:
        return run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{relative:+d}%"])
    return "Volume control unavailable."

def handle_mute_toggle():
    return run(["amixer", "set", "Master", "toggle"])

# ---------------- Brightness ----------------

def handle_brightness(relative=None):
    if subprocess.getstatusoutput("which brightnessctl")[0] == 0:
        return run(["brightnessctl", "set", f"{relative:+d}%"])
    return "Brightness control unavailable."

# ---------------- WiFi ----------------

def handle_wifi(on: bool):
    return run(["nmcli", "radio", "wifi", "on" if on else "off"])

# ---------------- Battery ----------------

def handle_battery_status():
    rc, out = subprocess.getstatusoutput("upower -i $(upower -e | grep battery)")
    return out if rc == 0 else "Battery info unavailable."

# ---------------- Media ----------------

def handle_media(action: str):
    return run(["playerctl", action])

# ---------------- Apps ----------------

def handle_app_launch(name: str):
    cmd = APP_COMMANDS.get(name) or APP_COMMANDS.get(name.lower())
    if not cmd:
        return f"App '{name}' not found."
    return run(shlex.split(cmd))
