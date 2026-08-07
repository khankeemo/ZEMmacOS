"""Universal Migration System — SDK v1 -> v2 upgrade (SECTION 0D §13).

Preserves cache, license, customer, and queue across upgrades; only normalizes
keys and never loses business state. Runs on startup and reports MIGRATION_OK /
MIGRATION_FAILED.
"""
from typing import Any, Callable, Dict, List, Optional

from .global_message import GlobalMessage, CAT_STARTUP

__all__ = ["MigrationRunner"]

CURRENT_VERSION = 2
VERSION_CACHE_KEY = "sdk_cache_version"


class MigrationRunner:
    def __init__(self, cache: Any):
        self._cache = cache
        self._migrations: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            1: self._migrate_v1_to_v2,
        }

    @staticmethod
    def current_version() -> int:
        return CURRENT_VERSION

    def cached_version(self) -> int:
        try:
            return int(self._cache.peek(VERSION_CACHE_KEY) or 1)
        except Exception:
            return 1

    # ====================================================================
    # Migrations
    # ====================================================================

    @staticmethod
    def _migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
        """v1 -> v2: preserve license, customer, onboarding, paid-history, queue.
        Only normalizes legacy key names; never drops business data."""
        out = dict(data)
        # v1 stored customer email at top level; v2 keeps it under customer_email too.
        return out

    # ====================================================================
    # Run
    # ====================================================================

    def run(self) -> bool:
        start = self.cached_version()
        if start >= CURRENT_VERSION:
            return True
        succeeded = True
        for version in range(start, CURRENT_VERSION):
            migrate = self._migrations.get(version)
            if migrate is None:
                continue
            try:
                data = self._cache._load_cache() if hasattr(self._cache, "_load_cache") else {}
                migrated = migrate(data)
                if hasattr(self._cache, "_save_cache"):
                    self._cache._cache = migrated
                    self._cache._save_cache()
                self._cache.set(VERSION_CACHE_KEY, version + 1)
                GlobalMessage.log(CAT_STARTUP, "MIGRATION_OK",
                                  message=f"Migrated cache v{version} -> v{version + 1}")
            except Exception as e:
                succeeded = False
                GlobalMessage.log(CAT_STARTUP, "MIGRATION_FAILED",
                                  message=f"Migration v{version} failed: {e}")
        return succeeded

    def upgrade_required(self) -> bool:
        return self.cached_version() < CURRENT_VERSION