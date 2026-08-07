"""Notification Center — a full local notification system (SECTION 0D §9).

History, read/unread, pinned, dismissed, and severity (success / warning / error /
information). Backed by the cache so notifications survive restarts. Every add()
emits 'notification.added' on EventBus for the ULC to render.
"""
import time
import uuid
from typing import Any, Dict, List, Optional

from .live_log import LiveLog

__all__ = ["NotificationCenter"]

SEVERITY_SUCCESS = "success"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITY_INFO = "information"

SEVERITIES = (SEVERITY_SUCCESS, SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_INFO)

CACHE_KEY = "notification_center"


class NotificationCenter:
    def __init__(self, cache: Any):
        self._cache = cache

    def _load(self) -> List[Dict[str, Any]]:
        items = self._cache.get(CACHE_KEY) or []
        if not isinstance(items, list):
            items = []
        return [dict(i) for i in items]

    def _save(self, items: List[Dict[str, Any]]) -> None:
        self._cache.set(CACHE_KEY, items)

    # ====================================================================
    # Mutations
    # ====================================================================

    def add(self, title: str, body: str = "", severity: str = SEVERITY_INFO,
            source: str = "", **extra: Any) -> Dict[str, Any]:
        if severity not in SEVERITIES:
            severity = SEVERITY_INFO
        notification = {
            "id": str(uuid.uuid4()),
            "title": title,
            "body": body,
            "severity": severity,
            "read": False,
            "pinned": bool(extra.get("pinned", False)),
            "dismissed": False,
            "source": source,
            "created_at": int(time.time()),
        }
        items = self._load()
        items.insert(0, notification)
        self._save(items)
        try:
            from .event_bus import EventBus
            EventBus.emit("notification.added", notification)
        except Exception:
            pass
        LiveLog.log("NOTIFICATION_ADDED", f"[{severity}] {title}")
        return notification

    def mark_read(self, notification_id: str) -> bool:
        items = self._load()
        for n in items:
            if n.get("id") == notification_id and not n.get("read"):
                n["read"] = True
                self._save(items)
                return True
        return False

    def mark_all_read(self) -> int:
        items = self._load()
        count = 0
        for n in items:
            if not n.get("read"):
                n["read"] = True
                count += 1
        if count:
            self._save(items)
        return count

    def pin(self, notification_id: str) -> bool:
        items = self._load()
        for n in items:
            if n.get("id") == notification_id:
                n["pinned"] = True
                self._save(items)
                return True
        return False

    def dismiss(self, notification_id: str) -> bool:
        items = self._load()
        for n in items:
            if n.get("id") == notification_id:
                n["dismissed"] = True
                n["read"] = True
                self._save(items)
                return True
        return False

    def remove(self, notification_id: str) -> bool:
        items = self._load()
        kept = [n for n in items if n.get("id") != notification_id]
        changed = len(kept) != len(items)
        if changed:
            self._save(kept)
        return changed

    # ====================================================================
    # Reads
    # ====================================================================

    def list(self, unread_only: bool = False, pinned_only: bool = False,
             severity: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self._load()
        if unread_only:
            items = [n for n in items if not n.get("read")]
        if pinned_only:
            items = [n for n in items if n.get("pinned")]
        if severity is not None:
            items = [n for n in items if n.get("severity") == severity]
        items.sort(key=lambda n: n.get("created_at", 0), reverse=True)
        return items

    def unread_count(self) -> int:
        return len([n for n in self._load() if not n.get("read")])

    def clear(self) -> None:
        self._save([])