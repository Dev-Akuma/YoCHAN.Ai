# core/commands.py
from __future__ import annotations
import os
from datetime import datetime

from os_backend import get_backend
from utils.logger import get_logger

backend = get_backend()
log = get_logger(__name__)


# ---- Volume / Brightness ----------------------------------------------------


def volume_set(percent: int) -> str:
    return backend.volume.set(percent)


def volume_change(delta: int) -> str:
    return backend.volume.change(delta)


def brightness_set(percent: int) -> str:
    return backend.brightness.set(percent)


def brightness_change(delta: int) -> str:
    return backend.brightness.change(delta)


# ---- Apps -------------------------------------------------------------------


def app_open(name: str) -> str:
    return backend.apps.open(name)


def app_close(name: str) -> str:
    return backend.apps.close(name)


def app_close_all() -> str:
    return backend.apps.close_all()


def app_list() -> list[str]:
    return backend.apps.list_apps()


# ---- Power ------------------------------------------------------------------


def power_action(name: str) -> str:
    return backend.power.action(name)


# ---- Timers / Alarms --------------------------------------------------------


def set_timer_seconds(seconds: int) -> str:
    return backend.timer.set_timer(seconds)


def set_alarm(time_str: str) -> str:
    return backend.timer.set_alarm(time_str)


# ---- Screenshot -------------------------------------------------------------


def take_screenshot() -> str:
    # default directory: ~/Pictures
    directory = os.path.expanduser("~/Pictures")
    path = backend.screen.screenshot(directory=directory)
    backend.notify.notify("Screenshot", path)
    return path


# ---- Clipboard --------------------------------------------------------------


def read_clipboard() -> str:
    return backend.clipboard.read()


# ---- Context-aware actions --------------------------------------------------


def context_action(action: str) -> str:
    """
    Map generic actions to keys based on active window class.
    """
    klass = (backend.window.active_class() or "").lower()
    log.info("Active window class: %s", klass)

    def k(keys: str):
        backend.window.send_key(keys)

    # Browser-like classes
    if any(x in klass for x in ("firefox", "chrome", "brave", "edge")):
        if action == "open downloads":
            k("ctrl+j")
            return "Opening downloads."
        if action == "reload":
            k("ctrl+r")
            return "Reloading page."
        if action == "back":
            k("alt+Left")
            return "Going back."
        if action == "forward":
            k("alt+Right")
            return "Going forward."
        if action == "new tab":
            k("ctrl+t")
            return "Opening new tab."
        if action == "close tab":
            k("ctrl+w")
            return "Closing tab."

    # Editor / notepad style
    if any(x in klass for x in ("gedit", "code", "notepad", "sublime", "vim")):
        if action == "copy":
            k("ctrl+c")
            return "Copied."
        if action == "paste":
            k("ctrl+v")
            return "Pasted."
        if action == "select all":
            k("ctrl+a")
            return "Selected all."

    return "No context action available."
