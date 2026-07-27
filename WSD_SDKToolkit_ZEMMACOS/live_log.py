"""LiveLog — shared event logging used across SDK modules"""
import time
from typing import Any, Callable, Optional


class LiveLog:
    _entries: list = []
    _external_logger = None

    @classmethod
    def set_external_logger(cls, callback: Optional[Callable[[str, str], None]]) -> None:
        cls._external_logger = callback

    @classmethod
    def log(cls, event: str, detail: str = "") -> None:
        entry = f"[{time.strftime('%H:%M:%S')}] {event}"
        if detail:
            entry += f" \u2014 {detail}"
        cls._entries.append(entry)
        print(entry)
        if cls._external_logger:
            try:
                cls._external_logger(event, detail)
            except Exception:
                pass

    @classmethod
    def get_log(cls) -> list:
        return list(cls._entries)

    @classmethod
    def clear(cls) -> None:
        cls._entries = []
