"""Local cache manager for license status (offline support).

SECTION 0D §11 — values are encrypted at rest with an app-derived Fernet key
when `enable_security()` is called. Writes fail closed (never plaintext) once
security is enabled; legacy plaintext cache files are still read and upgraded.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .security import SecurityRules, SecurityUnavailableError, _FERNET_AVAILABLE

_ENCRYPTED_MARKER = 'ENCRYPTED:'


class CacheManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.product_id = config.get('product', {}).get('id', 'unknown')
        safe_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in self.product_id)
        self._cache_dir = Path.home() / '.websmith' / safe_name
        self._cache_file = self._cache_dir / 'cache.json'
        self._tmp_file = self._cache_dir / 'cache.tmp'
        self._corrupt_file = self._cache_dir / 'cache.corrupt'
        self._ttl_days = self._get_ttl()
        self._cache: Optional[Dict[str, Any]] = None
        self._encryption_enabled = False
        self._fingerprint: Optional[str] = None

    def enable_security(self, fingerprint: str) -> None:
        """Turn on encryption-at-rest (§0D.11). Fail closed after this point:
        the cache is never written to disk in plaintext again."""
        self._fingerprint = fingerprint
        self._encryption_enabled = True
        SecurityRules.set_key(fingerprint)

    def _serialize(self, cache: Dict[str, Any]) -> str:
        plain = json.dumps(cache)
        if not self._encryption_enabled:
            return plain
        if not _FERNET_AVAILABLE:
            raise SecurityUnavailableError(
                'Encryption is unavailable. Cached values must never be '
                'written in plaintext (SECTION 0D §11).'
            )
        return _ENCRYPTED_MARKER + SecurityRules.encrypt(plain)

    def _deserialize(self, raw: str) -> Optional[Dict[str, Any]]:
        raw = raw.strip()
        if raw.startswith(_ENCRYPTED_MARKER):
            try:
                ciphertext = raw[len(_ENCRYPTED_MARKER):]
                return json.loads(SecurityRules.decrypt(ciphertext))
            except (SecurityUnavailableError, json.JSONDecodeError):
                return None
        # Legacy plaintext cache (pre-0D.11) — read it; the next save upgrades it.
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _get_ttl(self) -> int:
        offline = self.config.get('offline', {})
        return offline.get('cache_days', 0)

    def _ensure_cache_dir(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache
        self._ensure_cache_dir()
        if not self._cache_file.exists():
            self._cache = {}
            return self._cache
        try:
            with open(self._cache_file, 'r') as f:
                raw = f.read()
            loaded = self._deserialize(raw)
            if loaded is None:
                self._preserve_corrupt_cache()
                self._cache = {}
                return self._cache
            self._cache = loaded
            return self._cache
        except (json.JSONDecodeError, IOError):
            self._preserve_corrupt_cache()
            self._cache = {}
            return self._cache

    def _preserve_corrupt_cache(self) -> None:
        if self._cache_file.exists():
            try:
                if self._corrupt_file.exists():
                    self._corrupt_file.unlink()
                self._cache_file.rename(self._corrupt_file)
            except Exception:
                self._cache_file.unlink()

    def _save_cache(self) -> None:
        if self._cache is None:
            return
        self._ensure_cache_dir()
        try:
            payload = self._serialize(self._cache)
            with open(self._tmp_file, 'w') as f:
                f.write(payload)
            os.replace(self._tmp_file, self._cache_file)
        except Exception:
            if self._tmp_file.exists():
                try:
                    self._tmp_file.unlink()
                except Exception:
                    pass

    def get(self, key: str) -> Optional[Any]:
        cache = self._load_cache()
        entry = cache.get(key)
        if entry is None:
            return None
        if self.is_expired(entry):
            self.delete(key)
            return None
        return entry.get('value')

    def set(self, key: str, value: Any) -> None:
        cache = self._load_cache()
        cache[key] = {'value': value, 'cached_at': time.time()}
        self._save_cache()

    def delete(self, key: str) -> None:
        cache = self._load_cache()
        if key in cache:
            del cache[key]
            self._save_cache()

    def peek(self, key: str) -> Optional[Any]:
        """Raw read — returns the stored value even if the TTL expired,
        without deleting it (used by the engine for decision flags)."""
        cache = self._load_cache()
        entry = cache.get(key)
        if entry is None:
            return None
        return entry.get('value')

    def flush(self) -> None:
        """Force the in-memory cache to disk (used pre-restart)."""
        self._save_cache()

    def clear(self) -> None:
        self._cache = {}
        self._save_cache()

    def is_expired(self, entry: Dict[str, Any]) -> bool:
        cached_at = entry.get('cached_at', 0)
        ttl_seconds = self._ttl_days * 24 * 60 * 60
        return (time.time() - cached_at) > ttl_seconds

    def is_valid(self) -> bool:
        cache = self._load_cache()
        entry = cache.get('license_status')
        if entry is None:
            return False
        return not self.is_expired(entry)

    def get_license_status(self) -> Optional[Dict[str, Any]]:
        return self.get('license_status')

    def is_hardware_consistent(self, current_hardware_id: str) -> bool:
        status = self.peek_license_status()
        if not status:
            return True
        hardware_id = status.get('hardware_id')
        if not hardware_id:
            return True
        return hardware_id == current_hardware_id

    def invalidate_if_hardware_mismatch(self, current_hardware_id: str) -> None:
        if not self.is_hardware_consistent(current_hardware_id):
            self.invalidate_license_status()

    def reset_on_fresh_activation(self) -> None:
        """Rule 3 (AWS-01): clear the old cached license state before a fresh
        license activation is applied.

        Storage-only cleanup — removes stale license/customer values so a
        previous customer's license can never resurface after a new license is
        activated. The hardware ID is computed live (no stored key to clear) and
        the offline message queue is preserved. The cache never decides status.
        """
        cache = self._load_cache()
        changed = False
        for key in ('license_status', 'customer_email'):
            if key in cache and cache[key] is not None:
                cache.pop(key, None)
                changed = True
        if changed:
            self._cache = cache
            self._save_cache()

    def invalidate_license_status(self) -> None:
        self.delete('license_status')

    def peek_license_status(self) -> Optional[Dict[str, Any]]:
        cache = self._load_cache()
        entry = cache.get('license_status')
        if entry is None:
            return None
        return entry.get('value')

    def save_license_key(self, license_key: str) -> None:
        key_path = self._cache_dir / 'license.key'
        try:
            value = license_key.strip()
            if self._encryption_enabled:
                if not _FERNET_AVAILABLE:
                    raise SecurityUnavailableError(
                        'Encryption is unavailable. License key must never be '
                        'written in plaintext (SECTION 0D §11).'
                    )
                value = _ENCRYPTED_MARKER + SecurityRules.encrypt(value)
            key_path.write_text(value)
        except Exception:
            pass

    def load_license_key(self) -> Optional[str]:
        key_path = self._cache_dir / 'license.key'
        if key_path.exists():
            try:
                value = key_path.read_text().strip() or None
                if value and value.startswith(_ENCRYPTED_MARKER):
                    try:
                        return SecurityRules.decrypt(value[len(_ENCRYPTED_MARKER):])
                    except Exception:
                        return None
                return value
            except Exception:
                pass
        return None

    def clear_license_key(self) -> None:
        key_path = self._cache_dir / 'license.key'
        if key_path.exists():
            try:
                key_path.unlink()
            except Exception:
                pass

    # ====================================================================
    # Storage-only onboarding / history persistence.
    #
    # These methods persist state for offline display only. The cache NEVER
    # derives business status from them — the Global License Status API
    # (database) is the only source of truth for every license decision.
    # ====================================================================

    def set_onboarding_complete(self) -> None:
        cache = self._load_cache()
        cache['onboarding_complete'] = {'value': True, 'cached_at': time.time()}
        self._save_cache()

    def mark_has_ever_activated_paid_license(self) -> None:
        cache = self._load_cache()
        cache['has_ever_activated_paid_license'] = {'value': True, 'cached_at': time.time()}
        self._save_cache()

    # ====================================================================
    # Message Queue (Offline Retry)
    # ====================================================================

    def queue_message(self, msg: Dict[str, Any]) -> None:
        queue = self.get_message_queue()
        msg['id'] = msg.get('id', f"q_{int(time.time())}_{os.urandom(4).hex()}")
        msg['status'] = msg.get('status', 'pending')
        msg['retry_count'] = msg.get('retry_count', 0)
        msg['max_retries'] = msg.get('max_retries', 5)
        msg['created_at'] = msg.get('created_at', int(time.time()))
        msg['next_retry_at'] = msg.get('next_retry_at', int(time.time()) + 60)
        queue.append(msg)
        self.set('message_queue', queue)

    def get_message_queue(self) -> list:
        return self.get('message_queue') or []

    def save_message_queue(self, queue: list) -> None:
        self.set('message_queue', queue)

    def cleanup_sent_messages(self) -> None:
        queue = [m for m in self.get_message_queue() if m.get('status') != 'sent']
        self.save_message_queue(queue)

    def get_pending_count(self) -> int:
        return len([m for m in self.get_message_queue() if m.get('status') in ('pending', 'failed')])

    def reset_all(self) -> None:
        self.clear()
        self.clear_license_key()
