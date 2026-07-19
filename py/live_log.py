import os
import threading
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

CATEGORIES = {
    "STARTUP": 0,
    "SDK": 1,
    "WELCOME": 2,
    "ACTIVATION": 3,
    "RENEWAL": 4,
    "DEVICE": 5,
    "UI": 6,
}

LEVELS = {"DEBUG": 0, "INFO": 1, "SUCCESS": 2, "WARNING": 3, "ERROR": 4}

LEVEL_COLORS = {
    "DEBUG": "#888888",
    "INFO": "#51cf66",
    "SUCCESS": "#00ff88",
    "WARNING": "#ffd43b",
    "ERROR": "#ff6b6b",
}

CATEGORY_COLORS = {
    "STARTUP": "#5ac8fa",
    "SDK": "#af52de",
    "WELCOME": "#ff9f0a",
    "ACTIVATION": "#0071e3",
    "RENEWAL": "#34c759",
    "DEVICE": "#ff6482",
    "UI": "#86868b",
}


class LiveLog:
    def __init__(self):
        self._lock = threading.Lock()
        self._callbacks = []
        self._buffer = []
        self._running = True
        os.makedirs(LIVE_LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._log_path = os.path.join(LIVE_LOG_DIR, f"ZEMmacOS_live_{ts}.log")
        with open(self._log_path, "w", encoding="utf-8") as f:
            f.write(f"ZEMmacOS Live Log - Started {datetime.now().isoformat()}\n")
            f.write(f"{'='*80}\n")
        self._write_entry("STARTUP", "INFO", "LiveLog system initialized")
        self._write_entry("STARTUP", "INFO", f"Log file: {self._log_path}")

    def register(self, callback):
        with self._lock:
            self._callbacks.append(callback)
            for entry in self._buffer[-200:]:
                try:
                    callback(*entry)
                except Exception:
                    pass

    def unregister(self, callback):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def write(self, category, level, message, detail=None):
        entry = (category, level, message, detail)
        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) > 10000:
                self._buffer = self._buffer[-5000:]
            self._write_entry(category, level, message, detail)
            for cb in self._callbacks:
                try:
                    cb(category, level, message, detail)
                except Exception:
                    pass

    def _write_entry(self, category, level, message, detail=None):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{category:<10}] [{level:<7}] {message}"
        if detail:
            line += f" | {detail}"
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def get_log_path(self):
        return self._log_path

    def get_recent(self, count=200):
        with self._lock:
            return list(self._buffer[-count:])

    def stop(self):
        self._running = False
        self.write("STARTUP", "INFO", "LiveLog system stopped")


_LIVE_LOG_INSTANCE = None
_LIVE_LOG_LOCK = threading.Lock()


def get_live_log():
    global _LIVE_LOG_INSTANCE
    if _LIVE_LOG_INSTANCE is None:
        with _LIVE_LOG_LOCK:
            if _LIVE_LOG_INSTANCE is None:
                _LIVE_LOG_INSTANCE = LiveLog()
    return _LIVE_LOG_INSTANCE
