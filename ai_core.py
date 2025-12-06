# ai_core.py
from __future__ import annotations

import re
import shlex
from typing import TypedDict, Optional, Literal

from state import AssistantState
from apps import APP_COMMANDS

# --- NEW IMPORTS: Direct Intent Execution ---
from handlers import (
    handle_app_launch,
    handle_app_closure,
    handle_close_all,
    handle_volume,
    handle_brightness,
    handle_clipboard_read,
    handle_screenshot,
    handle_set_timer,
    handle_set_alarm,
    execute_command,
    run_command,
    show_notification,
    list_configured_apps,
)
# -------------------------------------------


# ==========================
# === TYPES & GLOBAL STATE =
# ==========================

class Intent(TypedDict, total=False):
    type: str                # e.g. "open_app", "close_app", "change_brightness", ...
    raw: str                 # normalized text
    app: Optional[str]
    value: Optional[int]     # numeric value (e.g. 50 for brightness)
    delta: Optional[int]     # relative change
    # --- NEW: for time-based commands ---
    time_str: Optional[str]  # e.g. "10 minutes", "7 30 a m"
    duration_s: Optional[int] # duration in seconds


STATE = AssistantState()  # single global state instance for now


# ==========================
# === NORMALIZATION ========
# ==========================

FILLER_PHRASES = [
    "yochan", "yo chan",
    "please", "can you",
    "will you", "would you",
    "uh", "umm", "um",
    "kind of", "sort of",
    "a little", "a bit",
]


def normalize_text(text: str) -> str:
    text = text.lower().strip()

    # remove punctuation that doesn't help much for our use-case
    text = re.sub(r"[,\.\?!]", " ", text)

    for f in FILLER_PHRASES:
        text = text.replace(f, " ")

    # collapse whitespace
    text = " ".join(text.split())
    return text


# ==========================
# === HELPERS ==============
# ==========================

def _match_app_in_text(text: str) -> Optional[str]:
    """
    Try to match one of the APP_COMMANDS keys inside the text.
    Offline, simple approach: substring scanning, biased towards longer names.
    """
    if not text:
        return None

    # Bias towards longer names for specificity
    candidates = sorted(APP_COMMANDS.keys(), key=len, reverse=True)
    for name in candidates:
        name_low = name.lower()
        # Simple substring check (can be improved with fuzzy/tokenizing later)
        if name_low in text:
            return name  # return canonical key as defined in APP_COMMANDS
    return None


def _extract_number(text: str) -> Optional[int]:
    """
    Extract first integer number if present.
    'set brightness to 60' -> 60
    'increase volume by 5 percent' -> 5
    """
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def _extract_time_duration(text: str) -> tuple[Optional[str], Optional[int]]:
    """
    Extracts time strings (e.g., '10 minutes', '3 hours') and converts to seconds.
    Returns (raw_time_str, duration_in_seconds)
    """
    time_units = {
        "second": 1,
        "seconds": 1,
        "minute": 60,
        "minutes": 60,
        "hour": 3600,
        "hours": 3600,
    }

    # Regex 1: Capture (number) (unit) for duration/timer
    m = re.search(r"(\d+)\s*(second|seconds|minute|minutes|hour|hours)", text)
    if m:
        number = int(m.group(1))
        unit = m.group(2)
        seconds = number * time_units[unit]
        return m.group(0), seconds

    # Regex 2: Capture (hour) (minute, optional) (am/pm) for alarms
    m_alarm = re.search(r"(\d+)(\s*(\d+))?\s*(a\.?m\.?|p\.?m\.?)", text)
    if m_alarm:
        # Cannot calculate duration in seconds without knowing current time, so return raw string
        return m_alarm.group(0), None

    return None, None


def _exec_raw_command(cmd_text: str) -> str:
    """
    Safe wrapper that converts a raw string into tokens and calls handlers.execute_command.
    This keeps the rest of the code able to pass simple strings.
    """
    if not cmd_text:
        return "No command provided."
    try:
        tokens = shlex.split(cmd_text)
    except Exception:
        # fallback: simple whitespace split
        tokens = cmd_text.split()
    # handlers.execute_command expects a list of tokens
    return execute_command(tokens)


# ==========================
# === OFFLINE INTENT NLU ===
# ==========================

def detect_intent_offline(text: str, state: AssistantState) -> Intent:
    """
    Pure offline, rule-based NLU.
    Input: normalized text
    Output: Intent structure.
    """

    intent: Intent = {"type": "raw_command", "raw": text}

    if not text:
        intent["type"] = "empty"
        return intent

    # --- CONTEXTUAL PRONOUNS -----------------------------

    # "close that"/"close it" -> close last_app
    if ("close that" in text or "close it" in text) and state.last_app:
        return {
            "type": "close_app",
            "app": state.last_app,
            "raw": text,
        }

    # "open that again" -> re-open last_app if we have one
    if ("open that" in text or "open it again" in text) and state.last_app:
        return {
            "type": "open_app",
            "app": state.last_app,
            "raw": text,
        }

    # --- APP OPEN/CLOSE/LAUNCH ---------------------------

    # try to detect an app name in the text
    app_name = _match_app_in_text(text)

    if any(w in text for w in ["open ", "launch ", "start ", "run "]) and app_name:
        return {
            "type": "open_app",
            "app": app_name,
            "raw": text,
        }

    if any(w in text for w in ["close ", "quit ", "exit ", "kill "]) and app_name:
        return {
            "type": "close_app",
            "app": app_name,
            "raw": text,
        }

    # "close all" / "kill all"
    if "close all" in text or "kill all" in text:
        return {
            "type": "close_all",
            "raw": text,
        }

    # --- BRIGHTNESS --------------------------------------

    # Ensure single words like 'brighter' or 'darker' trigger intent detection
    if "brightness" in text or "brighter" in text or "darker" in text:

        # absolute: "set brightness to 50"
        if "set" in text and "to" in text:
            value = _extract_number(text)
            if value is not None:
                return {
                    "type": "set_brightness",
                    "value": value,
                    "raw": text,
                }

        # relative up: "increase brightness", "bit brighter"
        if any(phrase in text for phrase in [
            "increase brightness",
            "raise brightness",
            "more brightness",
            "bit brighter",
            "little brighter",
            "brighter",
        ]):
            delta = _extract_number(text)
            if delta is None:
                # fall back to last or default
                delta = state.last_brightness_change or 10
            return {
                "type": "change_brightness",
                "delta": abs(delta),
                "raw": text,
            }

        # relative down: "decrease brightness", "bit darker"
        if any(phrase in text for phrase in [
            "decrease brightness",
            "lower brightness",
            "reduce brightness",
            "dim it",
            "bit darker",
            "little darker",
            "darker",
        ]):
            delta = _extract_number(text)
            if delta is None:
                delta = state.last_brightness_change or 10
            return {
                "type": "change_brightness",
                "delta": -abs(delta),
                "raw": text,
            }

    # --- VOLUME ------------------------------------------

    # Ensure single words like 'louder' or 'quieter' trigger intent detection
    if "volume" in text or "sound" in text or "louder" in text or "quieter" in text:
        if "mute" in text:
            return {
                "type": "set_volume",
                "value": 0,
                "raw": text,
            }

        # absolute: "set volume to 60"
        if "set" in text and "to" in text:
            value = _extract_number(text)
            if value is not None:
                return {
                    "type": "set_volume",
                    "value": value,
                    "raw": text,
                }

        # relative up
        if any(phrase in text for phrase in [
            "increase volume",
            "raise volume",
            "turn it up",
            "bit louder",
            "little louder",
            "louder",
        ]):
            delta = _extract_number(text)
            if delta is None:
                delta = state.last_volume_change or 5
            return {
                "type": "change_volume",
                "delta": abs(delta),
                "raw": text,
            }

        # relative down
        if any(phrase in text for phrase in [
            "decrease volume",
            "lower volume",
            "turn it down",
            "bit quieter",
            "little quieter",
            "quieter",
        ]):
            delta = _extract_number(text)
            if delta is None:
                delta = state.last_volume_change or 5
            return {
                "type": "change_volume",
                "delta": -abs(delta),
                "raw": text,
            }

    # --- CLIPBOARD COMMAND HINT ---
    if "clipboard" in text and ("show" in text or "read" in text or "what is" in text):
        return {"type": "clipboard_read", "raw": text}

    # --- SCREENSHOT --------------------------------------
    if any(word in text for word in ["screenshot", "capture screen", "print screen", "take a picture"]):
        return {
            "type": "take_screenshot",
            "raw": text,
        }

    # --- TIMERS & ALARMS ---------------------------------
    time_str, duration_s = _extract_time_duration(text)

    if "set a timer" in text or "start a timer" in text or "timer for" in text:
        if duration_s is not None:
            return {
                "type": "set_timer",
                "time_str": time_str,
                "duration_s": duration_s,
                "raw": text,
            }

    if "set an alarm" in text or "alarm for" in text:
        # Note: alarms rely on external tools and exact time extraction is tricky
        if time_str is not None:
            return {
                "type": "set_alarm",
                "time_str": time_str,
                "raw": text,
            }

    # --- FALLBACK: raw command, let existing handlers handle it (including power) -------
    return intent


# ==========================
# === INTENT EXECUTION =====
# ==========================

def execute_intent(intent: Intent, state: AssistantState) -> str:
    itype = intent.get("type")
    raw = intent.get("raw", "")

    # track command in state history
    state.remember_command(raw)

    # --- app open/close -----------------------------------

    if itype == "open_app" and intent.get("app"):
        app = intent["app"]
        res = handle_app_launch(app)  # DIRECT EXECUTION
        state.last_action = "open_app"
        state.last_app = app
        return res

    if itype == "close_app" and intent.get("app"):
        app = intent["app"]
        res = handle_app_closure(app)  # DIRECT EXECUTION
        state.last_action = "close_app"
        state.last_app = app
        return res

    if itype == "close_all":
        res = handle_close_all()  # DIRECT EXECUTION
        state.last_action = "close_all"
        return res

    # --- brightness ---------------------------------------

    if itype == "set_brightness" and intent.get("value") is not None:
        value = max(0, min(100, intent["value"]))  # clamp to 0–100
        res = handle_brightness(absolute=value)  # DIRECT EXECUTION
        state.last_action = "set_brightness"
        state.last_brightness_change = 0
        return res

    if itype == "change_brightness" and intent.get("delta") is not None:
        delta = intent["delta"]
        # handlers.handle_brightness accepts a relative integer (positive increases, negative decreases)
        res = handle_brightness(relative=delta)  # DIRECT EXECUTION
        state.last_action = "change_brightness"
        state.last_brightness_change = delta
        return res

    # --- volume -------------------------------------------

    if itype == "set_volume" and intent.get("value") is not None:
        value = max(0, min(100, intent["value"]))
        res = handle_volume(absolute=value)  # DIRECT EXECUTION
        state.last_action = "set_volume"
        state.last_volume_change = 0
        return res

    if itype == "change_volume" and intent.get("delta") is not None:
        delta = intent["delta"]
        res = handle_volume(relative=delta)  # DIRECT EXECUTION
        state.last_action = "change_volume"
        state.last_volume_change = delta
        return res

    # --- clipboard ----------------------------------------

    if itype == "clipboard_read":
        res = handle_clipboard_read()  # DIRECT EXECUTION
        state.last_action = "clipboard_read"
        return res

    # --- screenshot ---------------------------------------

    if itype == "take_screenshot":
        res = handle_screenshot()  # DIRECT EXECUTION
        state.last_action = "take_screenshot"
        return res

    # --- timers & alarms ----------------------------------

    if itype == "set_timer" and intent.get("duration_s") is not None:
        duration = intent["duration_s"]
        res = handle_set_timer(duration)  # DIRECT EXECUTION
        state.last_action = "set_timer"
        return res

    if itype == "set_alarm" and intent.get("time_str") is not None:
        time_str = intent["time_str"]
        res = handle_set_alarm(time_str)  # DIRECT EXECUTION
        state.last_action = "set_alarm"
        return res

    # --- default: raw command (includes power commands) ---

    if itype == "raw_command":
        cmd_text = raw
        # Forward raw string to handlers.execute_command safely
        res = _exec_raw_command(cmd_text)
        state.last_action = "raw_command"
        return res

    # --- empty / unknown ----------------------------------

    if itype == "empty":
        return "No speech detected."

    return "I couldn't understand that (offline)."


# ==========================
# === PUBLIC ENTRYPOINT ====
# ==========================

def handle_voice_input(text: str) -> str:
    """
    Main function YoChan's listener should call instead of execute_command.
    """
    if not text:
        return "No speech detected."

    normalized = normalize_text(text)
    intent = detect_intent_offline(normalized, STATE)
    result = execute_intent(intent, STATE)
    return result
