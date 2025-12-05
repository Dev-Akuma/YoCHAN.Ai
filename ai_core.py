# ai_core.py
from __future__ import annotations

import re
from typing import TypedDict, Optional, Literal

from state import AssistantState
from apps import APP_COMMANDS
from yochan import execute_command


# ==========================
# === TYPES & GLOBAL STATE =
# ==========================

class Intent(TypedDict, total=False):
    type: str                # e.g. "open_app", "close_app", "change_brightness", ...
    raw: str                 # normalized text
    app: Optional[str]
    value: Optional[int]     # numeric value (e.g. 50 for brightness)
    delta: Optional[int]     # relative change


STATE = AssistantState()  # single global state instance for now


# ==========================
# === NORMALIZATION ========
# ==========================

FILLER_PHRASES = [
    "yochan", "yo chan",
    "please", "can you", "could you",
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

    Example:
      APP_COMMANDS: "vs code", "code"
      Text: "open vs code"
      -> "vs code"
    """
    if not text:
        return None

    candidates = sorted(APP_COMMANDS.keys(), key=len, reverse=True)
    for name in candidates:
        name_low = name.lower()
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

    if "brightness" in text:
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

    if "volume" in text or "sound" in text:
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

    # --- POWER COMMAND HINTS (still go through execute_command) ----

    if any(word in text for word in ["shutdown", "shut down", "turn off", "power off"]):
        return {"type": "raw_command", "raw": "shutdown"}

    if any(word in text for word in ["restart", "reboot"]):
        return {"type": "raw_command", "raw": "restart"}

    if any(word in text for word in ["sleep", "suspend"]):
        return {"type": "raw_command", "raw": "sleep"}

    if any(word in text for word in ["logout", "log out", "log off"]):
        return {"type": "raw_command", "raw": "logout"}

    # --- FALLBACK: raw command, let existing yochan handle it -------

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
        # let yochan's existing logic handle: "open <app>"
        cmd_text = f"open {app}"
        res = execute_command(cmd_text)
        state.last_action = "open_app"
        state.last_app = app
        return res

    if itype == "close_app" and intent.get("app"):
        app = intent["app"]
        cmd_text = f"close {app}"
        res = execute_command(cmd_text)
        state.last_action = "close_app"
        state.last_app = app
        return res

    if itype == "close_all":
        cmd_text = "close all"
        res = execute_command(cmd_text)
        state.last_action = "close_all"
        return res

    # --- brightness ---------------------------------------

    if itype == "set_brightness" and intent.get("value") is not None:
        value = max(0, min(100, intent["value"]))  # clamp to 0–100
        # You may need to adapt this phrase to match your current handler
        cmd_text = f"set brightness {value}"
        res = execute_command(cmd_text)
        state.last_action = "set_brightness"
        state.last_brightness_change = 0
        return res

    if itype == "change_brightness" and intent.get("delta") is not None:
        delta = intent["delta"]
        # Adapt to your format, e.g. "brightness up 10" / "brightness down 10"
        if delta > 0:
            cmd_text = f"brightness up {delta}"
        else:
            cmd_text = f"brightness down {abs(delta)}"

        res = execute_command(cmd_text)
        state.last_action = "change_brightness"
        state.last_brightness_change = delta
        return res

    # --- volume -------------------------------------------

    if itype == "set_volume" and intent.get("value") is not None:
        value = max(0, min(100, intent["value"]))
        cmd_text = f"set volume {value}"
        res = execute_command(cmd_text)
        state.last_action = "set_volume"
        state.last_volume_change = 0
        return res

    if itype == "change_volume" and intent.get("delta") is not None:
        delta = intent["delta"]
        if delta > 0:
            cmd_text = f"volume up {delta}"
        else:
            cmd_text = f"volume down {abs(delta)}"

        res = execute_command(cmd_text)
        state.last_action = "change_volume"
        state.last_volume_change = delta
        return res

    # --- default: raw command -----------------------------

    if itype == "raw_command":
        cmd_text = raw
        res = execute_command(cmd_text)
        state.last_action = "raw_command"
        # you *could* infer last_app from res if you ever return structured info
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
