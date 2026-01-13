# os_backend/linux.py
from __future__ import annotations
import shlex
import subprocess
from typing import List

from .base import (
    Backend,
    VolumeController,
    BrightnessController,
    PowerController,
    AppController,
    ScreenController,
    ClipboardController,
    TimerController,
    WindowContext,
    NotificationCenter,
)

import handlers  # reuse existing helpers  :contentReference[oaicite:1]{index=1}


# ---- Volume / Brightness ----------------------------------------------------


class LinuxVolume(VolumeController):
    def set(self, percent: int) -> str:
        percent = max(0, min(100, int(percent)))
        return handlers.handle_volume(absolute=percent)

    def change(self, delta: int) -> str:
        return handlers.handle_volume(relative=int(delta))


class LinuxBrightness(BrightnessController):
    def set(self, percent: int) -> str:
        percent = max(0, min(100, int(percent)))
        return handlers.handle_brightness(absolute=percent)

    def change(self, delta: int) -> str:
        return handlers.handle_brightness(relative=int(delta))


# ---- Apps -------------------------------------------------------------------


class LinuxApps(AppController):
    def open(self, name: str) -> str:
        return handlers.handle_app_launch(name)

    def close(self, name: str) -> str:
        return handlers.handle_app_closure(name)

    def close_all(self) -> str:
        return handlers.handle_close_all()

    def list_apps(self) -> List[str]:
        return handlers.list_configured_apps()


# ---- Power ------------------------------------------------------------------


class LinuxPower(PowerController):
    def action(self, name: str) -> str:
        n = (name or "").lower()
        if any(k in n for k in ("shutdown", "power off")):
            cmd = ["systemctl", "poweroff"]
        elif any(k in n for k in ("reboot", "restart")):
            cmd = ["systemctl", "reboot"]
        elif "log out" in n or "logout" in n:
            cmd = ["gnome-session-quit", "--logout", "--no-prompt"]
        elif any(k in n for k in ("suspend", "sleep", "hibernate")):
            cmd = ["systemctl", "suspend"]
        else:
            return "Unknown power action."
        rc, _, err = handlers.run_command(cmd, capture_output=True, check=False)
        return "Power command sent." if rc == 0 else f"Power command failed: {err}"


# ---- Screen / Clipboard / Timer --------------------------------------------


class LinuxScreen(ScreenController):
    def screenshot(self, directory: str | None = None) -> str:
        return handlers.handle_screenshot(save_dir=directory)


class LinuxClipboard(ClipboardController):
    def read(self) -> str:
        return handlers.handle_clipboard_read()


class LinuxTimer(TimerController):
    def set_timer(self, seconds: int) -> str:
        return handlers.handle_set_timer(seconds)

    def set_alarm(self, time_str: str) -> str:
        return handlers.handle_set_alarm(time_str)


# ---- Window / Context -------------------------------------------------------


class LinuxWindow(WindowContext):
    def _run(self, args: list[str]) -> str:
        try:
            out = subprocess.check_output(args, text=True).strip()
            return out
        except Exception:
            return ""

    def active_class(self) -> str:
        wid = self._run(["xdotool", "getactivewindow"])
        if not wid:
            return ""
        return self._run(["xprop", "-id", wid, "WM_CLASS"])

    def send_key(self, keys: str) -> None:
        # keys like "ctrl+c" / "alt+Left"
        try:
            subprocess.check_output(["xdotool", "key", "--clearmodifiers", keys])
        except Exception:
            pass


# ---- Notifications ----------------------------------------------------------


class LinuxNotify(NotificationCenter):
    def notify(self, summary: str, body: str = "") -> None:
        handlers.show_notification(summary, body)


# ---- Backend factory --------------------------------------------------------


def make_backend() -> Backend:
    return Backend(
        volume=LinuxVolume(),
        brightness=LinuxBrightness(),
        power=LinuxPower(),
        apps=LinuxApps(),
        screen=LinuxScreen(),
        clipboard=LinuxClipboard(),
        timer=LinuxTimer(),
        window=LinuxWindow(),
        notify=LinuxNotify(),
    )
