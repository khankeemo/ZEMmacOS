"""API Idempotency — one operation per click storm (SECTION 0D §6).

Every mutating workflow (activation, renewal, hardware bind, trial) carries an
idempotency key derived from a per-workflow ID. Five clicks produce one operation:
the backend deduplicates on the key, and the SDK no-ops locally once the operation
is COMPLETED.
"""
import hashlib
import os
import time
import uuid
from typing import Any, Dict, Optional

from .live_log import LiveLog

__all__ = ["IdempotencyManager", "Operation"]

OPERATIONS = ("activation", "renewal", "hardware_bind", "trial", "trial_conversion",
              "reactivation")


class Operation:
    def __init__(self, workflow_id: str, kind: str):
        self.workflow_id = workflow_id
        self.kind = kind
        self.operation_id = str(uuid.uuid4())
        self.created_at = time.time()
        seed = f"{workflow_id}:{kind}:{self.operation_id}"
        self.idempotency_key = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]

    def payload(self) -> Dict[str, str]:
        return {
            "workflow_id": self.workflow_id,
            "operation_id": self.operation_id,
            "idempotency_key": self.idempotency_key,
        }


class IdempotencyManager:
    def __init__(self, cache: Any = None):
        self._cache = cache
        self._completed: Dict[str, str] = {}
        self._restore()

    def _key_cache(self, kind: str) -> str:
        return f"idem_{kind}"

    def _restore(self) -> None:
        if self._cache is None:
            return
        for kind in OPERATIONS:
            try:
                value = self._cache.get(self._key_cache(kind))
                if value:
                    self._completed[kind] = str(value)
            except Exception:
                pass

    def _persist(self, kind: str) -> None:
        if self._cache is None:
            return
        try:
            self._cache.set(self._key_cache(kind), self._completed.get(kind, ""))
        except Exception:
            pass

    # ====================================================================
    # API
    # ====================================================================

    def new_workflow_id(self) -> str:
        return str(uuid.uuid4())

    def begin(self, kind: str, workflow_id: Optional[str] = None) -> Operation:
        """Start (or resume) an idempotent operation. If the same kind already
        completed in this workflow, returns None — the caller treats it as a no-op.
        """
        if kind not in OPERATIONS:
            kind = "activation"
        if workflow_id is None:
            workflow_id = self.new_workflow_id()
        if self._completed.get(kind):
            LiveLog.log("IDEMPOTENCY", f"{kind} already completed in this workflow — no-op")
            return None  # type: ignore
        op = Operation(workflow_id, kind)
        LiveLog.log("IDEMPOTENCY", f"{kind} started (idempotency_key={op.idempotency_key[:8]}…)")
        return op

    def complete(self, op: Operation) -> None:
        if op is None:
            return
        self._completed[op.kind] = op.idempotency_key
        self._persist(op.kind)
        LiveLog.log("IDEMPOTENCY", f"{op.kind} completed (idempotency_key={op.idempotency_key[:8]}…)")

    def is_completed(self, kind: str) -> bool:
        return bool(self._completed.get(kind))

    def reset(self, kind: Optional[str] = None) -> None:
        if kind is None:
            self._completed.clear()
            if self._cache is not None:
                for op_kind in OPERATIONS:
                    try:
                        self._cache.delete(self._key_cache(op_kind))
                    except Exception:
                        pass
        else:
            self._completed.pop(kind, None)
            if self._cache is not None:
                try:
                    self._cache.delete(self._key_cache(kind))
                except Exception:
                    pass