# state.py
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AssistantState:
    """
    Holds short-term context for YoChan.

    Phase 1 goals:
      - remember last app opened/closed
      - remember last brightness/volume change
      - remember a small history of recent commands (optional)
    """
    last_action: Optional[str] = None          # "open_app", "close_app", "set_brightness", ...
    last_app: Optional[str] = None             # canonical app key (e.g. "code", "firefox")
    last_brightness_change: int = 0            # last relative percentage change (+10 / -10)
    last_volume_change: int = 0                # last relative change (+5 / -5)
    recent_commands: List[str] = field(default_factory=list)

    def remember_command(self, text: str, max_len: int = 10) -> None:
        text = text.strip()
        if not text:
            return
        self.recent_commands.append(text)
        if len(self.recent_commands) > max_len:
            self.recent_commands.pop(0)
