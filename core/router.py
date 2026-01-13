# core/router.py
from __future__ import annotations

import config as _cfg
from utils.logger import get_logger
from . import commands
from os_backend import get_backend

log = get_logger(__name__)
backend = get_backend()
ASSISTANT_DISPLAY_NAME = getattr(_cfg, "ASSISTANT_DISPLAY_NAME", "YoChan")


def _feedback(msg: str) -> None:
    """Log + desktop notification for a command result."""
    if not msg:
        return
    log.info(msg)
    try:
        backend.notify.notify(ASSISTANT_DISPLAY_NAME, msg)
    except Exception:
        # Don't crash if notifications fail
        pass


def handle_text(text: str) -> None:
    """
    Very simple rule-based router from text -> commands.
    Improve later with fuzzy matching / intent classification.
    """
    t = (text or "").strip().lower()
    if not t:
        return

    # Volume
    if t.startswith("set volume to"):
        # "set volume to 50 percent"
        parts = t.split()
        for part in reversed(parts):
            if part.rstrip("%").isdigit():
                pct = int(part.rstrip("%"))
                _feedback(commands.volume_set(pct))
                return
    if "volume up" in t or "increase volume" in t:
        _feedback(commands.volume_change(+10))
        return
    if "volume down" in t or "decrease volume" in t:
        _feedback(commands.volume_change(-10))
        return

    # Brightness
    if t.startswith("set brightness to"):
        parts = t.split()
        for part in reversed(parts):
            if part.rstrip("%").isdigit():
                pct = int(part.rstrip("%"))
                _feedback(commands.brightness_set(pct))
                return
    if "brightness up" in t or "increase brightness" in t:
        _feedback(commands.brightness_change(+10))
        return
    if "brightness down" in t or "decrease brightness" in t:
        _feedback(commands.brightness_change(-10))
        return

    # Apps
    if t.startswith("open "):
        name = t[len("open "):].strip()
        _feedback(commands.app_open(name))
        return
    if t.startswith("close "):
        name = t[len("close "):].strip()
        if name == "all":
            _feedback(commands.app_close_all())
        else:
            _feedback(commands.app_close(name))
        return

    # Power
    for kw in ["shutdown", "power off", "reboot", "restart", "suspend", "hibernate", "log out", "logout"]:
        if kw in t:
            _feedback(commands.power_action(kw))
            return

    # Timers / alarms
    if t.startswith("set timer for"):
        # naive: "set timer for 10 minutes"
        words = t.split()
        try:
            num = int(next(w for w in words if w.isdigit()))
        except StopIteration:
            num = 0
        secs = num
        if "minute" in t:
            secs = num * 60
        _feedback(commands.set_timer_seconds(secs))
        return

    if t.startswith("set alarm"):
        _feedback(commands.set_alarm(t))
        return

    # Screenshot
    if "screenshot" in t or "take screenshot" in t:
        # commands.take_screenshot already shows a notification with the path,
        # but we still send a generic feedback too.
        path = commands.take_screenshot()
        _feedback(f"Screenshot saved: {path}")
        return

    # Clipboard
    if "read clipboard" in t or "what is on clipboard" in t or "clipboard" in t:
        clip = commands.read_clipboard()
        _feedback(f"Clipboard: {clip}")
        return

    # Context actions
    for act in ["copy", "paste", "reload", "open downloads", "back", "forward", "new tab", "close tab", "select all"]:
        if act in t:
            _feedback(commands.context_action(act))
            return

    _feedback(f"Sorry, I don't understand '{t}' yet.")
