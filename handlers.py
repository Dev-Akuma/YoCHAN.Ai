"""
handlers.py
Common OS-level helpers for Yochan project:
- safe subprocess runners
- app launch / close
- volume/brightness helpers (best-effort)
- screenshot helper
- notifications
This module is intentionally dependency-light and defensive.
"""

from __future__ import annotations
import os
import shlex
import subprocess
import sys
import time
from typing import List, Optional, Tuple

# Import APP_COMMANDS from apps.py if available
try:
    from apps import APP_COMMANDS  # should be a dict mapping names->command strings
except Exception:
    APP_COMMANDS = {}

# Notification helper (uses notify-send if available)
def show_notification(summary: str, body: str = "") -> None:
    """Show desktop notification if notify-send is available; otherwise print."""
    try:
        if subprocess.getstatusoutput("which notify-send")[0] == 0:
            subprocess.Popen(["notify-send", summary, body])
        else:
            # fallback to printing so logs still show the message
            print(f"[NOTIFY] {summary} - {body}")
    except Exception as e:
        print(f"[NOTIFY-ERR] {e}", file=sys.stderr)


# Safe run_command wrapper
def run_command(cmd: List[str], capture_output: bool = False, check: bool = True, **kwargs) -> Tuple[int, str, str]:
    """
    Run command safely.
    cmd: list of tokens (no shell=True).
    Returns: (returncode, stdout, stderr). stdout/stderr are text strings.
    """
    if not cmd:
        return 1, "", "empty command"
    try:
        if capture_output:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=check, **kwargs)
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        else:
            proc = subprocess.run(cmd, check=check, **kwargs)
            return proc.returncode, "", ""
    except subprocess.CalledProcessError as e:
        # CalledProcessError has returncode; stdout/stderr available only when captured
        stdout = getattr(e, "stdout", "") or ""
        stderr = getattr(e, "stderr", "") or ""
        return getattr(e, "returncode", 1), stdout, stderr
    except Exception as e:
        return 1, "", str(e)


# Generic execute_command that returns a string (no side effects)
def execute_command(command_tokens: List[str]) -> str:
    """
    Execute a command (list form) and return a user-friendly string result.
    This function doesn't call notifications itself.
    """
    if not command_tokens:
        return "No command provided."
    code, out, err = run_command(command_tokens, capture_output=True, check=False)
    if code == 0:
        out = out.strip()
        return out if out else "Command executed successfully."
    else:
        err_text = (err.strip() or out.strip() or f"Exit code {code}")
        return f"Command failed: {err_text}"


# App launch helper (safe; uses shlex.split and Popen(list))
def handle_app_launch(app_name: str) -> str:
    """
    Launches an app based on APP_COMMANDS mapping.
    APP_COMMANDS values may be a single executable or a full command string.
    """
    if not app_name:
        return "No application specified."
    cmd_str = APP_COMMANDS.get(app_name) or APP_COMMANDS.get(app_name.lower())
    if not cmd_str:
        return f"Application '{app_name}' not found in mappings."

    # Use shlex.split so quoted tokens are preserved; do NOT use shell=True
    try:
        cmd = shlex.split(cmd_str)
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return f"Opening {app_name}."
    except FileNotFoundError:
        return f"Executable not found for '{app_name}'."
    except Exception as e:
        return f"Failed to open {app_name}: {e}"


def handle_app_closure(app_name: str) -> str:
    """
    Try to close an app. Uses pkill -f against the base executable or given command.
    """
    if not app_name:
        return "No application specified."
    cmd_str = APP_COMMANDS.get(app_name) or APP_COMMANDS.get(app_name.lower())
    if not cmd_str:
        return f"Application '{app_name}' not found in mappings."

    # Determine a process-match token: prefer a basename
    token = shlex.split(cmd_str)[0]
    try:
        # pkill may require sudo on some systems; keep simple and rely on user permissions
        rc, _, err = run_command(["pkill", "-f", token], capture_output=True, check=False)
        if rc == 0:
            return f"Closed {app_name}."
        else:
            return f"Could not close {app_name} (it may not be running)."
    except Exception as e:
        return f"Failed to close {app_name}: {e}"


def handle_close_all() -> str:
    """
    Attempt to close all apps listed in APP_COMMANDS by calling pkill on each token.
    """
    results = []
    for name, cmd in APP_COMMANDS.items():
        token = shlex.split(cmd)[0] if cmd else name
        rc, _, _ = run_command(["pkill", "-f", token], capture_output=True, check=False)
        results.append((name, rc == 0))
    succeeded = [n for n, ok in results if ok]
    failed = [n for n, ok in results if not ok]
    return f"Closed: {', '.join(succeeded)}. Not running: {', '.join(failed)}." if results else "No apps configured."


# Volume helpers (best-effort using amixer - works on many systems)
def handle_volume(relative: Optional[int] = None, absolute: Optional[int] = None) -> str:
    """
    Adjust or set volume.
    relative: +10 or -5 percentages
    absolute: set to 0..100
    """
    # Prefer pactl if available (works with pulseaudio & pipewire), fallback to amixer
    if subprocess.getstatusoutput("which pactl")[0] == 0:
        if relative is not None:
            op = f"{relative:+d}%"
            rc, out, err = run_command(["pactl", "set-sink-volume", "@DEFAULT_SINK@", op], capture_output=True, check=False)
            return "Volume adjusted." if rc == 0 else f"Volume adjust failed: {err or out}"
        if absolute is not None:
            rc, out, err = run_command(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{absolute}%"], capture_output=True, check=False)
            return "Volume set." if rc == 0 else f"Volume set failed: {err or out}"
    else:
        # fallback to amixer
        if relative is not None:
            sign = "+" if relative >= 0 else "-"
            rc, out, err = run_command(["amixer", "set", "Master", f"{abs(relative)}%{sign}"], capture_output=True, check=False)
            return "Volume adjusted." if rc == 0 else f"Volume adjust failed: {err or out}"
        if absolute is not None:
            rc, out, err = run_command(["amixer", "set", "Master", f"{absolute}%"], capture_output=True, check=False)
            return "Volume set." if rc == 0 else f"Volume set failed: {err or out}"
    return "No supported volume control found."


def handle_brightness(relative: Optional[int] = None, absolute: Optional[int] = None) -> str:
    """
    Adjust or set brightness. Best-effort:
    - try xbacklight
    - try /sys/class/backlight
    """
    # Try xbacklight
    if subprocess.getstatusoutput("which xbacklight")[0] == 0:
        if relative is not None:
            sign = "+" if relative >= 0 else "-"
            rc, out, err = run_command(["xbacklight", "-inc" if relative > 0 else "-dec", str(abs(relative))], capture_output=True, check=False)
            return "Brightness adjusted." if rc == 0 else f"Brightness adjust failed: {err or out}"
        if absolute is not None:
            rc, out, err = run_command(["xbacklight", "-set", str(absolute)], capture_output=True, check=False)
            return "Brightness set." if rc == 0 else f"Brightness set failed: {err or out}"

    # Fallback to sysfs
    try:
        base = "/sys/class/backlight"
        entries = os.listdir(base)
        if entries:
            # choose the first controller
            controller = os.path.join(base, entries[0])
            max_b = int(open(os.path.join(controller, "max_brightness")).read().strip())
            cur_b = int(open(os.path.join(controller, "brightness")).read().strip())
            if absolute is not None:
                val = int((absolute / 100.0) * max_b)
                with open(os.path.join(controller, "brightness"), "w") as fh:
                    fh.write(str(val))
                return "Brightness set via sysfs."
            if relative is not None:
                delta = int((relative / 100.0) * max_b)
                val = max(0, min(max_b, cur_b + delta))
                with open(os.path.join(controller, "brightness"), "w") as fh:
                    fh.write(str(val))
                return "Brightness adjusted via sysfs."
    except Exception:
        pass

    return "No supported brightness control found."


# Clipboard read (xclip/xsel)
def handle_clipboard_read() -> str:
    if subprocess.getstatusoutput("which xclip")[0] == 0:
        rc, out, err = run_command(["xclip", "-selection", "clipboard", "-o"], capture_output=True, check=False)
        return out.strip() if rc == 0 else "Clipboard read failed."
    if subprocess.getstatusoutput("which xsel")[0] == 0:
        rc, out, err = run_command(["xsel", "--clipboard", "--output"], capture_output=True, check=False)
        return out.strip() if rc == 0 else "Clipboard read failed."
    return "No clipboard utility found."


# Screenshot helper (tries several utilities)
def handle_screenshot(save_dir: Optional[str] = None) -> str:
    if save_dir is None:
        save_dir = os.path.expanduser("~/Pictures")
    os.makedirs(save_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d%H%M%S")
    out_path = os.path.join(save_dir, f"Screenshot-{timestamp}.png")

    # prefer gnome-screenshot, xfce4-screenshooter, scrot
    if subprocess.getstatusoutput("which gnome-screenshot")[0] == 0:
        cmd = ["gnome-screenshot", "-f", out_path]
        rc, _, err = run_command(cmd, capture_output=True, check=False)
        return out_path if rc == 0 else f"Screenshot failed: {err}"
    if subprocess.getstatusoutput("which xfce4-screenshooter")[0] == 0:
        cmd = ["xfce4-screenshooter", "-f", "-o", out_path]
        rc, _, err = run_command(cmd, capture_output=True, check=False)
        return out_path if rc == 0 else f"Screenshot failed: {err}"
    if subprocess.getstatusoutput("which scrot")[0] == 0:
        cmd = ["scrot", "-q", "100", out_path]
        rc, _, err = run_command(cmd, capture_output=True, check=False)
        return out_path if rc == 0 else f"Screenshot failed: {err}"

    return "No screenshot tool found (gnome-screenshot, xfce4-screenshooter, or scrot)."


# Timer/alarm helpers — basic implementations
def handle_set_timer(seconds: int) -> str:
    if seconds <= 0:
        return "Invalid timer length."
    # Spawn non-blocking threadless sleep via subprocess (nohup sleep ...)
    try:
        # Use sh -c to background sleep & notify after completion; keep simple
        notify_cmd = f"sh -c 'sleep {int(seconds)} && notify-send \"Timer\" \"{seconds} seconds elapsed\" &'"
        subprocess.Popen(notify_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return f"Timer set for {seconds} seconds."
    except Exception as e:
        return f"Failed to set timer: {e}"


def handle_set_alarm(time_str: str) -> str:
    """
    time_str: human time representation - this is kept simple.
    Real implementation would parse time_str and compute delta.
    """
    # Quick attempt: if time_str like "in 10 minutes" -> parse "10"
    try:
        if "minute" in time_str:
            num = int("".join([ch for ch in time_str if ch.isdigit()]) or 0)
            return handle_set_timer(num * 60)
    except Exception:
        pass
    return "Alarm scheduling not fully implemented. Please set timer instead."


# small helper to list configured apps
def list_configured_apps() -> List[str]:
    return list(APP_COMMANDS.keys())
