"""TTL-based in-memory cache for session data."""

import threading
import time
from typing import Any


class TTLCache:
    """Thread-safe in-memory cache with per-entry TTL expiry."""

    def __init__(self, default_ttl: int = 3600) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with TTL."""
        expiry = time.time() + (ttl or self._default_ttl)
        with self._lock:
            self._cache[key] = (value, expiry)

    def get(self, key: str) -> Any | None:
        """Retrieve a value, returning None if expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if time.time() > expiry:
                del self._cache[key]
                return None
            return value

    def delete(self, key: str) -> None:
        """Remove a key from the cache."""
        with self._lock:
            self._cache.pop(key, None)

    def purge_expired(self) -> int:
        """Remove expired entries and return the count removed."""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._cache.items() if now > exp]
            for k in expired:
                del self._cache[k]
        return len(expired)
