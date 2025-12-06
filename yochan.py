#!/usr/bin/env python3
"""
yochan.py - top-level command routing and fallback handlers.

This module routes text commands to OS-level handlers. It delegates
subprocess, notification and app management to handlers.py for safety and
testability.
"""

import re
import os
import sys
import signal
import difflib
import shlex
import shutil
import subprocess
from typing import Optional

# --- IMPORT CONFIGURATION ---
from config import (
    SHUTDOWN_CMD,
    REBOOT_CMD,
    SUSPEND_CMD,
    LOGOUT_CMD,
    FUZZY_THRESHOLD,
    ASSISTANT_NAME,
    ASSISTANT_DISPLAY_NAME,
)
from apps import APP_COMMANDS
# ----------------------------

# Import shared handlers (centralized, safer implementations)
from handlers import (
    show_notification,
    run_command,               # returns (rc, stdout, stderr)
    handle_app_launch as _handler_app_launch,
    handle_app_closure as _handler_app_closure,
    handle_close_all as _handler_close_all,
    handle_volume as _handler_volume,           # (relative=None, absolute=None)
    handle_brightness as _handler_brightness,   # (relative=None, absolute=None)
    handle_clipboard_read as _handler_clipboard_read,
    handle_screenshot as _handler_screenshot,
    handle_set_timer as _handler_set_timer,
    handle_set_alarm as _handler_set_alarm,
)

# ------------- CONFIG -------------
USE_SUDO = True
TERMINAL_APP = "xfce4-terminal"
# ----------------------------------


# --- FUZZY MATCHING HELPER ---
def _match_app_fuzzy(cleaned_command: str) -> Optional[str]:
    if not cleaned_command:
        return None
    candidates = list(APP_COMMANDS.keys())
    matches = difflib.get_close_matches(cleaned_command, candidates, n=1, cutoff=FUZZY_THRESHOLD)
    if matches:
        return matches[0]
    return None


# --- GRACEFUL CLEANUP HANDLER ---
def cleanup_old_listeners() -> None:
    """Finds and terminates any running yochan listener processes (best-effort)."""
    try:
        pids_output = subprocess.check_output(
            ["pgrep", "-f", "python.*yochan_listener.py"],
            text=True,
        ).strip().splitlines()
        pids = [int(p) for p in pids_output if p.isdigit() and int(p) != os.getpid()]
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                continue
    except subprocess.CalledProcessError:
        # pgrep returned non-zero -> no processes found
        pass
    except Exception as e:
        print(f"[{ASSISTANT_NAME}] cleanup_old_listeners error: {e}", file=sys.stderr)


# --- DISPLAY HANDLER (Notifications) ---
def show_result(message: str) -> str:
    """
    Show a desktop notification and print to stderr. Return the same message.
    """
    try:
        show_notification(ASSISTANT_DISPLAY_NAME, message)
    except Exception:
        print(f"[{ASSISTANT_NAME}] {message}", file=sys.stderr)
    print(f"\n[{ASSISTANT_NAME}]: {message}", file=sys.stderr)
    return message


# --- SYSTEM POWER HANDLERS ---
def handle_shutdown() -> str:
    cleanup_old_listeners()
    # run_command expects token lists; convert if caller gave a string command
    if LOGOUT_CMD:
        run_command(shlex.split(LOGOUT_CMD), check=False)
    if SHUTDOWN_CMD:
        run_command(shlex.split(SHUTDOWN_CMD), check=False)
    return "Shutting down system."


def handle_restart() -> str:
    cleanup_old_listeners()
    if REBOOT_CMD:
        run_command(shlex.split(REBOOT_CMD), check=False)
    return "Restarting system."


def handle_sleep() -> str:
    cleanup_old_listeners()
    if SUSPEND_CMD:
        run_command(shlex.split(SUSPEND_CMD), check=False)
    return "Suspending system."


def handle_logout() -> str:
    if LOGOUT_CMD:
        run_command(shlex.split(LOGOUT_CMD), check=False)
        return "Logging out of session."
    else:
        return "Logout command is not configured for this desktop."


# --- APPLICATION / GENERIC LAUNCHERS ---
def handle_app_launch(app_name: str) -> str:
    """
    Wrapper that calls handlers.handle_app_launch. Accepts either canonical app key
    from APP_COMMANDS or user-provided name that maps to APP_COMMANDS entries.
    """
    if not app_name:
        return "No application specified."

    # Exact key or fuzzy match
    key = app_name if app_name in APP_COMMANDS else (_match_app_fuzzy(app_name) or app_name)
    return _handler_app_launch(key)


def handle_generic_launch(cleaned_command: str) -> Optional[str]:
    """
    Try to execute an arbitrary executable from cleaned_command (best-effort).
    Avoids shell=True for safety.
    """
    if not cleaned_command:
        return None
    try:
        tokens = shlex.split(cleaned_command)
    except Exception:
        tokens = cleaned_command.split()
    if not tokens:
        return None

    exe = tokens[0].lower()
    if exe in ("the", "a", "an", "it", "this"):
        return None

    try:
        subprocess.Popen(tokens, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return f"Trying to open {exe}."
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[{ASSISTANT_NAME}] generic launch failed: {e}", file=sys.stderr)
        return None


def handle_app_closure(command_text: str) -> str:
    """
    Attempt to close an application using the canonical mapping in APP_COMMANDS.
    Delegates to handlers' closure helper if available.
    """
    CLOSE_PHRASES = r'^(close|quit|terminate|end)\s*'
    app_target = re.sub(CLOSE_PHRASES, '', command_text).strip()

    app_name = None
    if app_target in APP_COMMANDS:
        app_name = app_target
    else:
        for key in APP_COMMANDS.keys():
            if app_target in key or key in app_target:
                app_name = key
                break

    if app_name:
        return _handler_app_closure(app_name)

    return "Error: Application name was not recognized for closure."


def handle_close_all() -> str:
    return _handler_close_all()


# --- VOLUME/BRIGHTNESS HANDLER WRAPPERS (avoid name collision with imports) ---
def _get_percentage(command_text: str) -> Optional[int]:
    m = re.search(r'\d+', command_text)
    if m:
        percent = int(m.group(0))
        return min(100, max(0, percent))
    return None


def volume_cmd(command_text: str) -> str:
    """
    Top-level wrapper for volume commands. Calls handler or uses relative/absolute modes.
    """
    percent = _get_percentage(command_text)
    if percent is not None and any(word in command_text for word in ["set", "to"]):
        # absolute set
        return _handler_volume(absolute=percent)
    if any(word in command_text for word in ["up", "increase", "raise", "louder"]):
        step = percent or 5
        return _handler_volume(relative=step)
    if any(word in command_text for word in ["down", "decrease", "lower", "quieter"]):
        step = percent or 5
        return _handler_volume(relative=-step)
    return "Volume command failed. Specify a percentage (e.g., 'set volume to 50') or say 'increase volume'."


def brightness_cmd(command_text: str) -> str:
    """
    Top-level wrapper for brightness commands.
    """
    percent = _get_percentage(command_text)
    if percent is not None and any(word in command_text for word in ["set", "to"]):
        return _handler_brightness(absolute=percent)
    if any(word in command_text for word in ["up", "increase", "raise", "brighter"]):
        step = percent or 10
        return _handler_brightness(relative=step)
    if any(word in command_text for word in ["down", "decrease", "lower", "darker", "dim"]):
        step = percent or 10
        return _handler_brightness(relative=-step)
    return "Brightness command failed. Specify a percentage or say 'increase brightness'."


# --- CLIPBOARD / SCREENSHOT / TIMER WRAPPERS (avoid name collisions) ---
def clipboard_read_cmd() -> str:
    try:
        return _handler_clipboard_read()
    except Exception:
        # fallback to xclip
        try:
            result = subprocess.run(['xclip', '-o', '-selection', 'clipboard'], capture_output=True, text=True, check=True)
            content = result.stdout.strip()
            if content:
                show_notification("Clipboard Content", content[:50] + ("..." if len(content) > 50 else ""))
                return "Clipboard content shown."
            else:
                return "Clipboard is empty."
        except Exception:
            return "Failed to read clipboard content."


def screenshot_cmd() -> str:
    try:
        out = _handler_screenshot()
        # handlers returns path or error string; show notification if path returned
        if isinstance(out, str) and out.endswith(".png"):
            show_notification("Screenshot", f"Saved to {out}")
            return f"Screenshot saved: {out}"
        return out
    except Exception as e:
        return f"Screenshot failed: {e}"


def set_timer_cmd(duration_s: int, time_str: Optional[str]) -> str:
    try:
        return _handler_set_timer(duration_s)
    except Exception:
        # fallback: background sleep + notify
        try:
            notify = shutil.which("notify-send") or "notify-send"
            shell_command = f"nohup sh -c 'sleep {int(duration_s)} && {notify} \"⏰ YoChan Timer\" \"Time is up!\"' >/dev/null 2>&1 &"
            subprocess.Popen(shell_command, shell=True, start_new_session=True)
            return f"Timer started for {time_str or f'{duration_s} seconds'}."
        except Exception:
            return "Failed to set timer."


def set_alarm_cmd(time_str: str) -> str:
    try:
        return _handler_set_alarm(time_str)
    except Exception:
        # best-effort: open clock apps as hint
        handle_generic_launch("gnome-clocks")
        handle_generic_launch("xfce4-datetime-settings")
        return (
            f"I heard you want an alarm for {time_str}. "
            "Please use your desktop clock application for reliable scheduling."
        )


# --- MASTER EXECUTION FUNCTION ---
def execute_command(command_text: str) -> str:
    """
    Top-level routing for command text. Returns user-facing message.
    """
    if not command_text:
        return show_result("No command provided.")

    original = command_text.strip().lower()
    command_text = original

    CLEANUP_PATTERN = r"^(open|launch|start|run|the|a|i)\s*"
    CLOSE_PHRASES = ["close", "quit", "exit", "terminate", "end"]

    # --- 1. QUIT LISTENER COMMAND ---
    if "die" in command_text or "stop listening" in command_text:
        return "QUIT_LISTENER"

    # --- 2. POWER COMMANDS ---
    if "shutdown" in command_text or "turn off" in command_text:
        return show_result(handle_shutdown())
    elif "restart" in command_text or "reboot" in command_text:
        return show_result(handle_restart())
    elif "sleep" in command_text or "suspend" in command_text:
        return show_result(handle_sleep())
    elif any(word in command_text for word in ["logout", "log out", "log off"]):
        return show_result(handle_logout())

    # --- 3. CONTROL COMMANDS ---
    if "volume" in command_text:
        return show_result(volume_cmd(command_text))

    if "brightness" in command_text:
        return show_result(brightness_cmd(command_text))

    # --- 4. CLIPBOARD COMMANDS ---
    if "clipboard" in command_text and ("show" in command_text or "read" in command_text or "what is" in command_text):
        return show_result(clipboard_read_cmd())

    # --- 5. CLOSE ALL APPS COMMAND ---
    if "close all" in command_text or "kill all" in command_text:
        return show_result(handle_close_all())

    # --- 6. APPLICATION LAUNCH/CLOSE COMMANDS (Fallback Logic) ---
    if any(phrase in command_text for phrase in CLOSE_PHRASES):
        return show_result(handle_app_closure(command_text))

    cleaned_command = re.sub(CLEANUP_PATTERN, "", command_text).strip()

    # 6a. Exact match in APP_COMMANDS
    if cleaned_command in APP_COMMANDS:
        return show_result(handle_app_launch(cleaned_command))

    # 6b. Substring/inclusion match in APP_COMMANDS
    for app_name_key in APP_COMMANDS.keys():
        if app_name_key in cleaned_command or cleaned_command in app_name_key:
            return show_result(handle_app_launch(app_name_key))

    # 6c. Fuzzy fallback on app names
    fuzzy_key = _match_app_fuzzy(cleaned_command)
    if fuzzy_key:
        return show_result(handle_app_launch(fuzzy_key))

    # --- 7. GENERIC EXECUTABLE FALLBACK ---
    if any(w in command_text for w in ["brightness", "volume", "sleep", "shutdown", "reboot", "logout", "die"]):
        return show_result("Control command failed during execution. Check terminal logs for detailed error.")

    generic_result = handle_generic_launch(cleaned_command)
    if generic_result:
        return show_result(generic_result)

    # --- Alarm hint fallback ---
    if "alarm" in command_text:
        handle_generic_launch("gnome-clocks")
        handle_generic_launch("xfce4-datetime-settings")
        return show_result(
            "I heard a request for an alarm but cannot schedule it reliably; "
            "I tried to open your desktop clock app."
        )

    return show_result(f"Sorry, I don't understand '{cleaned_command}' yet.")
