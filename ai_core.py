from __future__ import annotations
import re

import handlers
from state import AssistantState

STATE = AssistantState()

VERB_MAP = {
    "opened": "open",
    "opening": "open",
    "launched": "open",
    "launching": "open",
    "started": "start",
    "starting": "start",
    "closed": "close",
    "closing": "close",
}

FILLERS = {"please", "could", "you", "can", "uh", "um"}

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    words = []
    for w in text.split():
        if w in FILLERS:
            continue
        words.append(VERB_MAP.get(w, w))
    return " ".join(words)

def handle_voice_input(text: str) -> str:
    handlers.notify("STT", f"Heard: '{text}'")

    norm = normalize(text)
    handlers.notify("NORMALIZE", f"→ '{norm}'")

    # Wake-word bleed or nonsense
    if norm.startswith(("yochan", "yo chan", "weapon")):
        return "Yes?"

    STATE.remember_command(norm)

    # ---------------- Volume ----------------
    if "volume" in norm or "louder" in norm:
        return handlers.handle_volume(relative=10)
    if "quieter" in norm:
        return handlers.handle_volume(relative=-10)
    if "mute" in norm:
        return handlers.handle_mute_toggle()

    # ---------------- Brightness ----------------
    if "brighter" in norm:
        return handlers.handle_brightness(relative=10)
    if "darker" in norm:
        return handlers.handle_brightness(relative=-10)

    # ---------------- WiFi ----------------
    if "wifi on" in norm:
        return handlers.handle_wifi(True)
    if "wifi off" in norm:
        return handlers.handle_wifi(False)

    # ---------------- Battery ----------------
    if "battery" in norm:
        return handlers.handle_battery_status()

    # ---------------- Media ----------------
    if "play" in norm or "pause" in norm:
        return handlers.handle_media("playpause")
    if "next" in norm:
        return handlers.handle_media("next")
    if "previous" in norm:
        return handlers.handle_media("previous")

    # ---------------- Open App ----------------
    if norm.startswith("open"):
        app = norm.replace("open", "", 1).strip()
        if not app:
            return "Open what?"
        return handlers.handle_app_launch(app)

    # ---------------- Fallback ----------------
    handlers.notify("ERROR", f"No intent matched for '{norm}'", critical=True)
    return "Sorry, I didn't understand that."
