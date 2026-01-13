# os_backend/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


class VolumeController(Protocol):
    def set(self, percent: int) -> str: ...
    def change(self, delta: int) -> str: ...


class BrightnessController(Protocol):
    def set(self, percent: int) -> str: ...
    def change(self, delta: int) -> str: ...


class PowerController(Protocol):
    def action(self, name: str) -> str: ...


class AppController(Protocol):
    def open(self, name: str) -> str: ...
    def close(self, name: str) -> str: ...
    def close_all(self) -> str: ...
    def list_apps(self) -> list[str]: ...


class ScreenController(Protocol):
    def screenshot(self, directory: str | None = None) -> str: ...


class ClipboardController(Protocol):
    def read(self) -> str: ...


class TimerController(Protocol):
    def set_timer(self, seconds: int) -> str: ...
    def set_alarm(self, time_str: str) -> str: ...


class WindowContext(Protocol):
    def active_class(self) -> str: ...
    def send_key(self, keys: str) -> None: ...


class NotificationCenter(Protocol):
    def notify(self, summary: str, body: str = "") -> None: ...


@dataclass
class Backend:
    volume: VolumeController
    brightness: BrightnessController
    power: PowerController
    apps: AppController
    screen: ScreenController
    clipboard: ClipboardController
    timer: TimerController
    window: WindowContext
    notify: NotificationCenter
