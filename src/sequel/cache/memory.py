"""In-memory TTL-based cache for API responses."""

import asyncio
import time
from typing import Any, Generic, TypeVar

from sequel.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CacheEntry(Generic[T]):
    """A cache entry with TTL support.

    Attributes:
        value: The cached value
        expires_at: Timestamp when this entry expires
    """

    def __init__(self, value: T, ttl: int) -> None:
        """Initialize cache entry.

        Args:
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        self.value = value
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if entry is expired, False otherwise
        """
        return time.time() > self.expires_at


class MemoryCache:
    """Thread-safe in-memory cache with TTL support.

    This cache stores API responses in memory with configurable TTL.
    It's async-safe using asyncio.Lock for concurrent access.

    Example:
        ```python
        cache = MemoryCache()
        await cache.set("projects", projects_list, ttl=600)
        projects = await cache.get("projects")
        ```
    """

    def __init__(self) -> None:
        """Initialize the memory cache."""
        self._cache: dict[str, CacheEntry[Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                logger.debug(f"Cache miss: {key}")
                return None

            if entry.is_expired():
                logger.debug(f"Cache expired: {key}")
                del self._cache[key]
                return None

            logger.debug(f"Cache hit: {key}")
            return entry.value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        async with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    async def invalidate(self, key: str) -> None:
        """Invalidate (remove) a cache entry.

        Args:
            key: Cache key to invalidate
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated: {key}")

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.debug(f"Cache cleared: {count} entries removed")

    async def cleanup_expired(self) -> None:
        """Remove all expired entries from cache."""
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self._cache[key]
            if expired_keys:
                logger.debug(f"Cache cleanup: {len(expired_keys)} expired entries removed")

    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of entries in cache (including expired)
        """
        return len(self._cache)


# Global cache instance
_cache: MemoryCache | None = None


def get_cache() -> MemoryCache:
    """Get the global cache instance.

    Returns:
        Global MemoryCache instance
    """
    global _cache
    if _cache is None:
        _cache = MemoryCache()
    return _cache


def reset_cache() -> None:
    """Reset the global cache instance (mainly for testing)."""
    global _cache
    _cache = None
