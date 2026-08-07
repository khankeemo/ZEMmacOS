"""Single instance lock — acquire / release ONLY.

This module has exactly one responsibility:
    Acquire lock  ->  hold  ->  Release lock

It NEVER opens the Universal License Center, NEVER calls LicenseEngine,
Client, Migration, Session, or the API, and NEVER performs startup logic.

The acquisition is process-global and idempotent: constructing more than one
ULC (or engine) inside the same process reuses the single lock instead of
failing with "another instance running". Cross-process duplication (two real
OS processes) is still detected and the caller is told to exit.

Stale-lock safety: the lock file records the owning PID. If the owning process
no longer exists (a previous run crashed, or the restart flow shut it down),
the lock is reclaimed automatically so a fresh single process is never falsely
blocked. A short retry also covers the restart overlap where the old process
is still mid-shutdown.
"""
import atexit
import os
import sys
import tempfile
import threading
import time
from typing import Dict, Optional

__all__ = ["SingleInstance", "acquire_global_lock", "release_global_lock",
           "is_locked"]

_LOCKFILE_EXT = ".opencode.lock"
_LOCKS: Dict[str, "SingleInstance"] = {}
_GUARD = threading.Lock()
_ACQUIRE_RETRY_SECONDS = 3.0
_ACQUIRE_RETRY_STEP = 0.25


def _lock_path(name: str) -> str:
    return os.path.join(tempfile.gettempdir(), f'{name}{_LOCKFILE_EXT}')


def _pid_is_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_owner_pid(lock_file: str) -> Optional[int]:
    try:
        with open(lock_file, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if raw.isdigit():
            return int(raw)
    except Exception:
        pass
    return None


class SingleInstance:
    """File-based lock handle. Acquire + release only — no other behaviour.

    If the lock is already held by another live OS process, ``acquired`` is set
    to False without exiting; the caller decides what to do. A lock left behind
    by a dead process is reclaimed. ``release()`` removes the lock file when
    owned.
    """

    def __init__(self, lock_name: str):
        self._lock_name = lock_name
        self._lock_file = _lock_path(lock_name)
        self._fd: int = -1
        self.acquired: bool = False
        self._try_acquire()

    def _try_acquire(self) -> None:
        deadline = time.time() + _ACQUIRE_RETRY_SECONDS
        while True:
            self._fd = -1
            try:
                self._fd = os.open(self._lock_file,
                                   os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self._fd, str(os.getpid()).encode("utf-8"))
                self.acquired = True
                return
            except FileExistsError:
                # Stale lock from a dead process -> reclaim it.
                owner = _read_owner_pid(self._lock_file)
                if owner is not None and not _pid_is_alive(owner):
                    try:
                        os.unlink(self._lock_file)
                    except OSError:
                        pass
                    continue
                # Still held (or owner unknown) — retry briefly to tolerate the
                # restart overlap, then give up.
                if time.time() >= deadline:
                    self.acquired = False
                    return
                time.sleep(_ACQUIRE_RETRY_STEP)
            except Exception:
                self.acquired = False
                return

    def release(self) -> None:
        if self._fd != -1:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = -1
        try:
            os.unlink(self._lock_file)
        except Exception:
            pass

    # Backward-compatible alias (old callers used `._release()`).
    _release = release


def acquire_global_lock(lock_name: str) -> bool:
    """Acquire the lock once per process for the given name.

    Returns True when the lock is held by this process (either newly acquired
    or already acquired earlier in the same process). Returns False only when
    the lock is genuinely owned by another OS process — the caller should then
    refuse to start. The current ``sys.exit`` behaviour and the exact messages
    are kept but moved to the single decision point (startup).
    """
    with _GUARD:
        if lock_name in _LOCKS:
            return True
    handle = SingleInstance(lock_name)
    if not handle.acquired:
        return False
    with _GUARD:
        _LOCKS[lock_name] = handle
    atexit.register(lambda n=lock_name: release_global_lock(n))
    return True


def release_global_lock(lock_name: str) -> None:
    with _GUARD:
        handle = _LOCKS.pop(lock_name, None)
    if handle is not None:
        handle.release()


def is_locked(lock_name: str) -> bool:
    with _GUARD:
        return lock_name in _LOCKS