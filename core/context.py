# core/context.py
from os_backend import get_backend

backend = get_backend()


def get_active_window_class() -> str:
    return backend.window.active_class()


def send_key(keys: str) -> None:
    backend.window.send_key(keys)
