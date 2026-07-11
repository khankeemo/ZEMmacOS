"""Simple file-based cache for offline status persistence"""
import os
import json
import time
from pathlib import Path
from typing import Optional, Any

class CacheManager:
    def __init__(self, product_name: str = "websmith", ttl_days: int = 30):
        safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in product_name)
        self._cache_dir = Path.home() / '.websmith' / safe_name
        self._cache_file = self._cache_dir / 'cache.json'
        self._ttl_seconds = ttl_days * 86400
        self._cache = self._load()

    def _load(self) -> dict:
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def _save(self):
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, 'w') as f:
                json.dump(self._cache, f)
        except:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._cache.get(key)
        if entry is None:
            return default
        if entry.get('ttl') and time.time() > entry['ttl']:
            self.delete(key)
            return default
        return entry.get('value')

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        entry = {'value': value, 'stored_at': time.time()}
        if ttl is not None:
            entry['ttl'] = time.time() + ttl
        elif self._ttl_seconds:
            entry['ttl'] = time.time() + self._ttl_seconds
        self._cache[key] = entry
        self._save()

    def delete(self, key: str):
        self._cache.pop(key, None)
        self._save()

    def clear(self):
        self._cache = {}
        self._save()

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def set_onboarding_complete(self):
        self.set('onboarding_complete', True, ttl=None)

    def is_onboarding_complete(self) -> bool:
        return self.get('onboarding_complete', False) is True
