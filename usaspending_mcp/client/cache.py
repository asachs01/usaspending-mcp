"""In-memory lazy cache with TTL.

Each cache key has its own asyncio.Lock to prevent thundering herd on first
access — multiple concurrent callers waiting on the same key will share one
API call rather than each making their own.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Awaitable


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl_seconds: float):
        self.value = value
        self.expires_at = time.monotonic() + ttl_seconds

    @property
    def expired(self) -> bool:
        return time.monotonic() >= self.expires_at


# Default TTLs (seconds)
TTL_24H = 86_400
TTL_12H = 43_200

# Maps cache keys to their TTL
KEY_TTLS: dict[str, float] = {
    "agencies": TTL_24H,
    "naics_codes": TTL_24H,
    "psc_codes": TTL_24H,
    "cfda_programs": TTL_24H,
    "fiscal_year": TTL_12H,
}


class LazyCache:
    """Async lazy-loading cache with per-key TTL and thundering-herd protection."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._loaders: dict[str, Callable[[], Awaitable[Any]]] = {}

    def register_loader(self, key: str, loader: Callable[[], Awaitable[Any]]) -> None:
        """Register an async loader function for a cache key."""
        self._loaders[key] = loader

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create per-key lock."""
        if key not in self._locks:
            async with self._global_lock:
                if key not in self._locks:
                    self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def get(self, key: str) -> Any:
        """Get cached value, loading from registered loader if missing/expired."""
        entry = self._store.get(key)
        if entry is not None and not entry.expired:
            return entry.value

        lock = await self._get_lock(key)
        async with lock:
            # Double-check after acquiring lock
            entry = self._store.get(key)
            if entry is not None and not entry.expired:
                return entry.value

            loader = self._loaders.get(key)
            if loader is None:
                raise KeyError(f"No loader registered for cache key: {key!r}")

            value = await loader()
            ttl = KEY_TTLS.get(key, TTL_24H)
            self._store[key] = _CacheEntry(value, ttl)
            return value

    def put(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Manually set a cache value."""
        if ttl is None:
            ttl = KEY_TTLS.get(key, TTL_24H)
        self._store[key] = _CacheEntry(value, ttl)

    def clear(self, key: str) -> None:
        """Evict a single cache entry."""
        self._store.pop(key, None)

    def clear_all(self) -> None:
        """Evict all cache entries."""
        self._store.clear()

    def is_cached(self, key: str) -> bool:
        """Check if a non-expired entry exists."""
        entry = self._store.get(key)
        return entry is not None and not entry.expired


# Singleton instance shared across the server
cache = LazyCache()
