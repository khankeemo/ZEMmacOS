"""Communication Queue — explicit delivery lifecycle (SECTION 0D §8).

Pending -> Sending -> Retry -> Delivered -> Failed. A message is never dropped
silently: every terminal state is logged and the message is retained until ack()
or an explicit purge. Backed by the cache message queue (preserved across
activations per Rule 3).
"""
import time
from typing import Any, Callable, Dict, List, Optional

from .live_log import LiveLog

__all__ = ["CommunicationQueue"]

STATE_PENDING = "pending"
STATE_SENDING = "sending"
STATE_RETRY = "retry"
STATE_DELIVERED = "delivered"
STATE_FAILED = "failed"


class CommunicationQueue:
    def __init__(self, cache: Any):
        self._cache = cache

    # ====================================================================
    # Enqueue / read
    # ====================================================================

    def enqueue(self, message: Dict[str, Any]) -> Dict[str, Any]:
        msg = dict(message)
        msg.setdefault("id", f"q_{int(time.time())}_{abs(hash(str(message))) % 10**8}")
        msg.setdefault("status", STATE_PENDING)
        msg.setdefault("retry_count", 0)
        msg.setdefault("max_retries", 5)
        msg.setdefault("created_at", int(time.time()))
        msg.setdefault("next_retry_at", int(time.time()) + 60)
        self._cache.queue_message(msg)
        LiveLog.log("COMM_QUEUE_PENDING", f"Message {msg['id']} queued")
        return msg

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        queue = self._cache.get_message_queue()
        if status is None:
            return queue
        return [m for m in queue if m.get("status") == status]

    def pending_count(self) -> int:
        return len([m for m in self._cache.get_message_queue()
                    if m.get("status") in (STATE_PENDING, STATE_FAILED, STATE_RETRY)])

    # ====================================================================
    # Processing
    # ====================================================================

    def process(self, deliver: Callable[[Dict[str, Any]], bool],
                now_ts: Optional[int] = None) -> Dict[str, int]:
        """Attempt delivery of due messages. ``deliver`` performs the actual send
        (engine passthrough) and returns True on success. Never drops messages.
        """
        now = int(now_ts or time.time())
        queue = self._cache.get_message_queue()
        changed = False
        stats = {"delivered": 0, "failed": 0, "retry": 0, "skipped": 0}
        for msg in queue:
            status = msg.get("status")
            if status in (STATE_DELIVERED, STATE_SENDING):
                continue
            if now < msg.get("next_retry_at", 0):
                stats["skipped"] += 1
                continue
            if msg.get("retry_count", 0) >= msg.get("max_retries", 5):
                if status != STATE_FAILED:
                    msg["status"] = STATE_FAILED
                    changed = True
                    LiveLog.log("COMM_QUEUE_FAILED", f"Message {msg.get('id')} failed permanently")
                stats["failed"] += 1
                continue
            msg["status"] = STATE_SENDING
            try:
                ok = bool(deliver(msg))
            except Exception as e:
                msg["last_error"] = str(e)
                ok = False
            if ok:
                msg["status"] = STATE_DELIVERED
                msg["delivered_at"] = int(time.time())
                stats["delivered"] += 1
                LiveLog.log("COMM_QUEUE_DELIVERED", f"Message {msg.get('id')} delivered")
            else:
                msg["retry_count"] = msg.get("retry_count", 0) + 1
                msg["last_error"] = msg.get("last_error") or "delivery returned False"
                exp_backoff = pow(2, msg["retry_count"]) * 60
                msg["next_retry_at"] = now + exp_backoff
                msg["status"] = STATE_RETRY
                stats["retry"] += 1
                LiveLog.log("COMM_QUEUE_RETRY", f"Message {msg.get('id')} retry #{msg['retry_count']}")
            changed = True
        if changed:
            self._cache.save_message_queue(queue)
        return stats

    def ack(self, message_id: str) -> bool:
        queue = self._cache.get_message_queue()
        for msg in queue:
            if msg.get("id") == message_id:
                msg["status"] = STATE_DELIVERED
                msg["delivered_at"] = int(time.time())
                self._cache.save_message_queue(queue)
                return True
        return False

    def requeue(self, message_id: str) -> bool:
        queue = self._cache.get_message_queue()
        for msg in queue:
            if msg.get("id") == message_id:
                msg["status"] = STATE_PENDING
                msg["retry_count"] = 0
                msg["next_retry_at"] = int(time.time())
                self._cache.save_message_queue(queue)
                return True
        return False

    def purge(self, only_delivered: bool = True) -> int:
        queue = self._cache.get_message_queue()
        if only_delivered:
            kept = [m for m in queue if m.get("status") != STATE_DELIVERED]
        else:
            kept = []
        removed = len(queue) - len(kept)
        self._cache.save_message_queue(kept)
        return removed