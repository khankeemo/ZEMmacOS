"""Support Request Workflow — lifecycle tracking (SECTION 0D §18).

Customer -> Support -> Assigned -> Reply -> Resolved -> Closed. The license is always
attached automatically when a license exists in the session. The server remains the
authority; this is a local lifecycle tracker for the ULC to render the current stage.
"""
import time
import uuid
from typing import Any, Dict, List, Optional

from .live_log import LiveLog

__all__ = ["SupportRequestTracker", "STAGE_CUSTOMER", "STAGE_SUPPORT", "STAGE_ASSIGNED",
           "STAGE_REPLY", "STAGE_RESOLVED", "STAGE_CLOSED"]

STAGE_CUSTOMER = "customer"
STAGE_SUPPORT = "support"
STAGE_ASSIGNED = "assigned"
STAGE_REPLY = "reply"
STAGE_RESOLVED = "resolved"
STAGE_CLOSED = "closed"

STAGE_ORDER = (STAGE_CUSTOMER, STAGE_SUPPORT, STAGE_ASSIGNED, STAGE_REPLY,
               STAGE_RESOLVED, STAGE_CLOSED)

CACHE_KEY = "support_requests"


class SupportRequestTracker:
    def __init__(self, cache: Any):
        self._cache = cache

    def _load(self) -> List[Dict[str, Any]]:
        items = self._cache.get(CACHE_KEY) or []
        if not isinstance(items, list):
            items = []
        return [dict(i) for i in items]

    def _save(self, items: List[Dict[str, Any]]) -> None:
        self._cache.set(CACHE_KEY, items)

    def create(self, subject: str, message: str, license_key: str = "",
               hardware_id: str = "", customer_email: str = "") -> Dict[str, Any]:
        request = {
            "id": str(uuid.uuid4()),
            "subject": subject,
            "message": message,
            "license_key": license_key,   # always attached automatically
            "hardware_id": hardware_id,
            "customer_email": customer_email,
            "stage": STAGE_CUSTOMER,
            "notes": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        items = self._load()
        items.insert(0, request)
        self._save(items)
        LiveLog.log("SUPPORT_STAGE", f"Request {request['id']} -> {STAGE_CUSTOMER}")
        return request

    def advance(self, request_id: str, stage: str, note: str = "") -> Optional[Dict[str, Any]]:
        if stage not in STAGE_ORDER:
            return None
        items = self._load()
        for r in items:
            if r.get("id") == request_id:
                r["stage"] = stage
                if note:
                    r["notes"] = r.get("notes", []) + [{"stage": stage, "note": note,
                                                        "at": int(time.time())}]
                r["updated_at"] = int(time.time())
                self._save(items)
                LiveLog.log("SUPPORT_STAGE", f"Request {request_id} -> {stage}")
                return r
        return None

    def list(self, stage: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self._load()
        if stage is not None:
            items = [r for r in items if r.get("stage") == stage]
        items.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        return items

    def get(self, request_id: str) -> Optional[Dict[str, Any]]:
        for r in self._load():
            if r.get("id") == request_id:
                return r
        return None

    @staticmethod
    def stage_label(stage: str) -> str:
        labels = {
            STAGE_CUSTOMER: "Submitted",
            STAGE_SUPPORT: "Received",
            STAGE_ASSIGNED: "Assigned",
            STAGE_REPLY: "In Progress",
            STAGE_RESOLVED: "Resolved",
            STAGE_CLOSED: "Closed",
        }
        return labels.get(stage, stage.capitalize())