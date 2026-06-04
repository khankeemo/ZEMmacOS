import threading
import time
import requests
from typing import Callable, Optional


class APIMonitor:
    """Monitor API health, latency, and provide callbacks with status updates."""

    def __init__(
        self, api_base: str, interval: int = 10, callback: Optional[Callable] = None
    ):
        self.api_base = api_base.rstrip("/")
        self.interval = interval
        self.callback = callback or (lambda s: None)
        self._stop = threading.Event()
        self._thread = None

    def _check(self):
        url = self.api_base + "/health"
        start = time.time()
        try:
            r = requests.get(url, timeout=3)
            latency = int((time.time() - start) * 1000)
            data = (
                r.json()
                if r.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            status = {
                "online": r.status_code == 200
                and (data.get("status") == "ok" or data.get("success")),
                "latency_ms": latency,
                "raw": data,
            }
        except Exception as e:
            status = {"online": False, "latency_ms": None, "error": str(e)}
        return status

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)

    def _loop(self):
        while not self._stop.is_set():
            s = self._check()
            try:
                self.callback(s)
            except Exception:
                pass
            time.sleep(self.interval)
