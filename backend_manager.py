import os
import sys
import threading
import time
import subprocess
import requests
from typing import Callable, Optional


class BackendManager:
    """Manage starting and monitoring the local backend for internal admin use.

    This manager is intentionally conservative: it will only attempt to start
    a backend when the API is unreachable, and it will hide created console
    windows on Windows using CREATE_NO_WINDOW.
    """

    def __init__(
        self, api_url: str, log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.api_url = api_url.rstrip("/")
        self.log = log_callback or (lambda m, l="info": None)
        self._proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._monitor_interval = 10

    def _health_check(self, timeout=2) -> bool:
        try:
            r = requests.get(self.api_url + "/health", timeout=timeout)
            return r.status_code == 200 and (
                r.json().get("status") == "ok" or r.json().get("success")
            )
        except Exception:
            return False

    def ensure_backend_running(self, wait_seconds: int = 30) -> bool:
        """Ensure API is reachable; if not, attempt to start a bundled backend.

        Returns True when API responds within wait_seconds, else False.
        """
        if self._health_check():
            self.log("API already online", "debug")
            return True

        self.log("API offline, attempting to start backend", "info")
        started = self._start_backend_process()
        if not started:
            self.log("No backend start command found", "warning")
        # Wait for API to come online
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            if self._health_check():
                self.log("API responded after starting backend", "success")
                return True
            time.sleep(1)

        self.log("API did not respond in time", "error")
        return False

    def _start_backend_process(self) -> bool:
        """Try to find and start a backend start command. Returns True if started."""
        cwd = os.getcwd()
        candidates = [
            os.path.join(cwd, "run_backend.bat"),
            os.path.join(cwd, "run.bat"),
            os.path.join(cwd, "run_admin_ui.bat"),
            os.path.join(cwd, "gibMacOS.bat"),
            os.path.join(cwd, "gibMacOS.command"),
        ]
        for p in candidates:
            if os.path.isfile(p):
                try:
                    # Windows: hide console window
                    creationflags = 0
                    if sys.platform.startswith("win"):
                        creationflags = subprocess.CREATE_NO_WINDOW
                    self._proc = subprocess.Popen(
                        [p], shell=True, creationflags=creationflags
                    )
                    self.log(f"Started backend process: {p}", "info")
                    return True
                except Exception as e:
                    self.log(f"Failed to start backend {p}: {e}", "error")
        return False

    def start_monitor(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.log("Backend monitor started", "debug")

    def stop_monitor(self):
        self._stop.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

    def _monitor_loop(self):
        while not self._stop.is_set():
            online = self._health_check()
            if not online:
                self.log("Monitor: API offline — attempting restart", "warning")
                self._start_backend_process()
            time.sleep(self._monitor_interval)

    def __del__(self):
        try:
            self.stop_monitor()
        except Exception:
            pass


import os
import sys
import time
import threading
import subprocess
import shutil
from urllib.parse import urlparse

import requests

WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000 if WINDOWS else 0


class BackendManager:
    """Auto-start and monitor the local ZEM API backend."""

    def __init__(
        self,
        api_url: str,
        log_callback=None,
        startup_timeout: int = 30,
        check_interval: int = 10,
    ):
        self.api_url = api_url.rstrip("/")
        self.startup_timeout = startup_timeout
        self.check_interval = check_interval
        self.process = None
        self._monitor_thread = None
        self._stop_event = threading.Event()
        self.log_callback = log_callback or (lambda message, level="info": None)

    def _log(self, message: str, level: str = "info"):
        try:
            self.log_callback(message, level)
        except Exception:
            pass

    def _health_endpoint(self) -> str:
        if self.api_url.endswith("/health"):
            return self.api_url
        return f"{self.api_url}/health"

    def _is_local_address(self) -> bool:
        parsed = urlparse(self.api_url)
        host = (parsed.hostname or "").lower()
        return host in ("localhost", "127.0.0.1", "0.0.0.0", "::1")

    def is_api_online(self) -> bool:
        try:
            response = requests.get(self._health_endpoint(), timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _get_backend_command(self):
        parsed = urlparse(self.api_url)
        port = parsed.port or 8000
        backend_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ZEM_API"
        )
        python_executable = sys.executable
        if getattr(sys, "frozen", False):
            python_executable = (
                shutil.which("python") or shutil.which("python3") or python_executable
            )

        return [
            python_executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ], backend_dir

    def is_backend_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start_backend_process(self) -> bool:
        if not self._is_local_address():
            self._log("Backend auto-start disabled for non-local API URL.", "warning")
            return False
        if self.is_backend_running():
            self._log("Backend process already running.", "debug")
            return True

        command, cwd = self._get_backend_command()
        if not os.path.isdir(cwd):
            self._log(f"Backend folder not found: {cwd}", "error")
            return False

        self._log(f"Starting backend process: {command}", "info")
        try:
            self.process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                shell=False,
                creationflags=CREATE_NO_WINDOW,
            )
            return True
        except Exception as exc:
            self._log(f"Failed to launch backend: {exc}", "error")
            self.process = None
            return False

    def wait_for_api(self) -> bool:
        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if self.is_api_online():
                self._log("Backend health check passed.", "success")
                return True
            if self.process and self.process.poll() is not None:
                self._log("Backend process exited unexpectedly.", "warning")
            time.sleep(1)
        self._log("Backend did not become available within timeout.", "error")
        return self.is_api_online()

    def ensure_backend_running(self) -> bool:
        if self.is_api_online():
            self._log("API already online.", "success")
            return True

        if not self._is_local_address():
            self._log(
                "API is offline and backend auto-start is disabled for remote URL.",
                "warning",
            )
            return False

        if not self.start_backend_process():
            return False

        return self.wait_for_api()

    def start_monitor(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        while not self._stop_event.wait(self.check_interval):
            online = self.is_api_online()
            if online:
                if self.process and self.process.poll() is not None:
                    self._log(
                        "API is online but backend process stopped. Restarting local backend.",
                        "warning",
                    )
                    self.start_backend_process()
                continue

            self._log("API health check failed. Attempting auto-recovery.", "warning")
            if not self.is_backend_running():
                self.start_backend_process()
            else:
                self._log(
                    "Backend process running but API still unavailable.", "warning"
                )

    def stop_monitor(self):
        self._stop_event.set()
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
