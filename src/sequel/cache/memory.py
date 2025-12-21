"""In-memory TTL-based cache for API responses."""

import asyncio
import contextlib
import sys
import time
from collections import OrderedDict
from typing import Any, Generic, TypeVar

from sequel.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CacheEntry(Generic[T]):
    """A cache entry with TTL support.

    Attributes:
        value: The cached value
        expires_at: Timestamp when this entry expires
        size_bytes: Approximate size of the cached value in bytes
    """

    def __init__(self, value: T, ttl: int) -> None:
        """Initialize cache entry.

        Args:
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        self.value = value
        self.expires_at = time.time() + ttl
        self.size_bytes = sys.getsizeof(value)

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

    Features:
    - TTL-based expiration
    - LRU eviction when size limit exceeded
    - Background cleanup task
    - Statistics tracking (hits, misses, evictions)

    Example:
        ```python
        cache = MemoryCache()
        await cache.set("projects", projects_list, ttl=600)
        projects = await cache.get("projects")
        ```
    """

    def __init__(self, max_size_bytes: int = 100 * 1024 * 1024) -> None:
        """Initialize the memory cache.

        Args:
            max_size_bytes: Maximum cache size in bytes (default: 100MB)
        """
        self._cache: OrderedDict[str, CacheEntry[Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._max_size_bytes = max_size_bytes
        self._cleanup_task: asyncio.Task[None] | None = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

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
                self._stats["misses"] += 1
                logger.debug(f"Cache miss: {key}")
                return None

            if entry.is_expired():
                self._stats["expirations"] += 1
                logger.debug(f"Cache expired: {key}")
                del self._cache[key]
                return None

            # Move to end for LRU (most recently used)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
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
            entry = CacheEntry(value, ttl)

            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]

            # Check if we need to evict entries to stay under size limit
            await self._evict_if_needed(entry.size_bytes)

            self._cache[key] = entry
            logger.debug(f"Cache set: {key} (TTL: {ttl}s, size: {entry.size_bytes} bytes)")

    async def _evict_if_needed(self, new_entry_size: int) -> None:
        """Evict least recently used entries if cache is too large.

        Args:
            new_entry_size: Size of the entry being added
        """
        # Calculate current cache size
        current_size = sum(entry.size_bytes for entry in self._cache.values())

        # Evict LRU entries until we have space
        while current_size + new_entry_size > self._max_size_bytes and self._cache:
            # Remove oldest (least recently used) entry
            oldest_key, oldest_entry = self._cache.popitem(last=False)
            current_size -= oldest_entry.size_bytes
            self._stats["evictions"] += 1
            logger.debug(
                f"Cache eviction: {oldest_key} "
                f"(size: {oldest_entry.size_bytes} bytes, freed: {current_size} bytes)"
            )

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
                self._stats["expirations"] += 1
            if expired_keys:
                logger.debug(f"Cache cleanup: {len(expired_keys)} expired entries removed")

    async def start_cleanup_task(self, interval_seconds: int = 300) -> None:
        """Start background cleanup task.

        Args:
            interval_seconds: Cleanup interval in seconds (default: 300 = 5 minutes)
        """
        if self._cleanup_task is not None:
            logger.warning("Cleanup task already running")
            return

        logger.info(f"Starting background cache cleanup (interval: {interval_seconds}s)")
        self._cleanup_task = asyncio.create_task(self._background_cleanup(interval_seconds))

    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task is None:
            return

        logger.info("Stopping background cache cleanup")
        self._cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._cleanup_task
        self._cleanup_task = None

    async def _background_cleanup(self, interval_seconds: int) -> None:
        """Background task to periodically clean up expired entries.

        Args:
            interval_seconds: Cleanup interval in seconds
        """
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                logger.debug("Background cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}")

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, evictions, and expirations counts
        """
        return self._stats.copy()

    def get_size_bytes(self) -> int:
        """Get current cache size in bytes.

        Returns:
            Total size of all cached values in bytes
        """
        return sum(entry.size_bytes for entry in self._cache.values())

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
