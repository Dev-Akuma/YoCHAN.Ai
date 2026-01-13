# os_backend/__init__.py
import sys
from .base import Backend
from .linux import make_backend

# For now only Linux backend exists, but this is where you'll later plug in
# Windows / macOS backends.
_backend: Backend = make_backend()


def get_backend() -> Backend:
    return _backend
