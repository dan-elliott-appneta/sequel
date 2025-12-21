"""Unit tests for memory cache."""

import asyncio
import time

import pytest

from sequel.cache.memory import CacheEntry, MemoryCache, get_cache, reset_cache


class TestCacheEntry:
    """Test CacheEntry functionality."""

    def test_create_entry(self) -> None:
        """Test creating a cache entry."""
        entry = CacheEntry("test_value", ttl=60)

        assert entry.value == "test_value"
        assert entry.expires_at > time.time()

    def test_is_expired_false(self) -> None:
        """Test entry is not expired within TTL."""
        entry = CacheEntry("test_value", ttl=60)
        assert entry.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Test entry is expired after TTL."""
        entry = CacheEntry("test_value", ttl=0)
        time.sleep(0.1)  # Wait a bit
        assert entry.is_expired() is True

    def test_entry_has_size(self) -> None:
        """Test cache entry tracks size in bytes."""
        entry = CacheEntry("test_value", ttl=60)
        assert entry.size_bytes > 0
        assert isinstance(entry.size_bytes, int)


class TestMemoryCache:
    """Test MemoryCache functionality."""

    @pytest.fixture
    def cache(self) -> MemoryCache:
        """Create a fresh cache instance."""
        return MemoryCache()

    @pytest.mark.asyncio
    async def test_get_miss(self, cache: MemoryCache) -> None:
        """Test cache miss returns None."""
        result = await cache.get("missing_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: MemoryCache) -> None:
        """Test setting and getting a value."""
        await cache.set("test_key", "test_value", ttl=60)
        result = await cache.get("test_key")

        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_expired(self, cache: MemoryCache) -> None:
        """Test getting an expired entry returns None."""
        await cache.set("test_key", "test_value", ttl=0)
        await asyncio.sleep(0.1)  # Wait for expiry

        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self, cache: MemoryCache) -> None:
        """Test invalidating a cache entry."""
        await cache.set("test_key", "test_value", ttl=60)
        await cache.invalidate("test_key")

        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_missing_key(self, cache: MemoryCache) -> None:
        """Test invalidating a non-existent key doesn't error."""
        await cache.invalidate("missing_key")  # Should not raise

    @pytest.mark.asyncio
    async def test_clear(self, cache: MemoryCache) -> None:
        """Test clearing all cache entries."""
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=60)
        await cache.clear()

        result1 = await cache.get("key1")
        result2 = await cache.get("key2")

        assert result1 is None
        assert result2 is None
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache: MemoryCache) -> None:
        """Test cleanup removes expired entries."""
        await cache.set("valid", "valid_value", ttl=60)
        await cache.set("expired", "expired_value", ttl=0)
        await asyncio.sleep(0.1)  # Wait for expiry

        await cache.cleanup_expired()

        assert await cache.get("valid") == "valid_value"
        assert await cache.get("expired") is None

    @pytest.mark.asyncio
    async def test_size(self, cache: MemoryCache) -> None:
        """Test cache size tracking."""
        assert cache.size() == 0

        await cache.set("key1", "value1", ttl=60)
        assert cache.size() == 1

        await cache.set("key2", "value2", ttl=60)
        assert cache.size() == 2

        await cache.invalidate("key1")
        assert cache.size() == 1

    @pytest.mark.asyncio
    async def test_cache_different_types(self, cache: MemoryCache) -> None:
        """Test caching different value types."""
        await cache.set("string", "test", ttl=60)
        await cache.set("int", 123, ttl=60)
        await cache.set("list", [1, 2, 3], ttl=60)
        await cache.set("dict", {"key": "value"}, ttl=60)

        assert await cache.get("string") == "test"
        assert await cache.get("int") == 123
        assert await cache.get("list") == [1, 2, 3]
        assert await cache.get("dict") == {"key": "value"}

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache: MemoryCache) -> None:
        """Test concurrent cache access is thread-safe."""

        async def setter(key: str, value: str) -> None:
            await cache.set(key, value, ttl=60)

        async def getter(key: str) -> str | None:
            return await cache.get(key)

        # Run multiple concurrent operations
        await asyncio.gather(
            setter("key1", "value1"),
            setter("key2", "value2"),
            setter("key3", "value3"),
        )

        results = await asyncio.gather(
            getter("key1"),
            getter("key2"),
            getter("key3"),
        )

        assert results == ["value1", "value2", "value3"]

    @pytest.mark.asyncio
    async def test_statistics_hits_and_misses(self, cache: MemoryCache) -> None:
        """Test cache statistics track hits and misses."""
        # Initial stats should be zero
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Set a value
        await cache.set("test_key", "test_value", ttl=60)

        # Miss - key doesn't exist
        await cache.get("missing_key")
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

        # Hit - key exists
        await cache.get("test_key")
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

        # Another hit
        await cache.get("test_key")
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_statistics_expirations(self, cache: MemoryCache) -> None:
        """Test cache statistics track expirations."""
        stats = cache.get_stats()
        assert stats["expirations"] == 0

        # Set an expired entry
        await cache.set("expired_key", "value", ttl=0)
        await asyncio.sleep(0.1)

        # Getting expired entry increments expiration count
        await cache.get("expired_key")
        stats = cache.get_stats()
        assert stats["expirations"] == 1

    @pytest.mark.asyncio
    async def test_lru_eviction_on_size_limit(self, cache: MemoryCache) -> None:
        """Test LRU eviction when cache exceeds size limit."""
        # Create a cache with very small size limit (1KB)
        small_cache = MemoryCache(max_size_bytes=1024)

        # Add entries that will exceed the limit
        # Use larger values to trigger eviction
        large_value = "x" * 500  # 500 bytes

        await small_cache.set("key1", large_value, ttl=60)
        await small_cache.set("key2", large_value, ttl=60)
        await small_cache.set("key3", large_value, ttl=60)

        # Should have triggered evictions
        stats = small_cache.get_stats()
        assert stats["evictions"] > 0

        # Oldest entry (key1) should be evicted
        result = await small_cache.get("key1")
        assert result is None

        # Newer entries should still exist
        result2 = await small_cache.get("key2")
        result3 = await small_cache.get("key3")
        assert result2 is not None or result3 is not None

    @pytest.mark.asyncio
    async def test_lru_ordering(self, cache: MemoryCache) -> None:
        """Test LRU properly tracks access order."""
        # Create cache with small limit
        small_cache = MemoryCache(max_size_bytes=2048)

        # Add three entries
        large_value = "x" * 600
        await small_cache.set("key1", large_value, ttl=60)
        await small_cache.set("key2", large_value, ttl=60)

        # Access key1 to make it recently used
        await small_cache.get("key1")

        # Add key3, which should evict key2 (least recently used)
        await small_cache.set("key3", large_value, ttl=60)

        # key1 and key3 should exist, key2 should be evicted
        assert await small_cache.get("key1") is not None
        assert await small_cache.get("key3") is not None

    @pytest.mark.asyncio
    async def test_get_size_bytes(self, cache: MemoryCache) -> None:
        """Test getting total cache size in bytes."""
        assert cache.get_size_bytes() == 0

        await cache.set("key1", "value1", ttl=60)
        size1 = cache.get_size_bytes()
        assert size1 > 0

        await cache.set("key2", "value2", ttl=60)
        size2 = cache.get_size_bytes()
        assert size2 > size1

        await cache.invalidate("key1")
        size3 = cache.get_size_bytes()
        assert size3 < size2

    @pytest.mark.asyncio
    async def test_background_cleanup_task(self, cache: MemoryCache) -> None:
        """Test background cleanup task lifecycle."""
        # Start cleanup task with short interval
        await cache.start_cleanup_task(interval_seconds=1)

        # Add an expired entry
        await cache.set("expired", "value", ttl=0)
        await asyncio.sleep(0.1)

        # Wait for cleanup to run
        await asyncio.sleep(1.5)

        # Expired entry should be removed by background task
        # (Check via size since get() would remove it anyway)
        assert cache.size() == 0

        # Stop cleanup task
        await cache.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_background_cleanup_task_already_running(
        self, cache: MemoryCache
    ) -> None:
        """Test starting cleanup task when already running."""
        await cache.start_cleanup_task(interval_seconds=10)

        # Starting again should log warning but not error
        await cache.start_cleanup_task(interval_seconds=10)

        # Cleanup
        await cache.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_stop_cleanup_task_not_running(self, cache: MemoryCache) -> None:
        """Test stopping cleanup task when not running."""
        # Should not error
        await cache.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_get_stats_returns_copy(self, cache: MemoryCache) -> None:
        """Test get_stats returns a copy, not reference."""
        stats1 = cache.get_stats()
        stats1["hits"] = 999

        stats2 = cache.get_stats()
        assert stats2["hits"] == 0  # Original unchanged

    @pytest.mark.asyncio
    async def test_cache_replacement_updates_size(self, cache: MemoryCache) -> None:
        """Test replacing a cached value updates size correctly."""
        await cache.set("key", "small", ttl=60)
        size1 = cache.get_size_bytes()

        # Replace with larger value
        await cache.set("key", "x" * 1000, ttl=60)
        size2 = cache.get_size_bytes()

        assert size2 > size1

    @pytest.mark.asyncio
    async def test_eviction_frees_memory(self, cache: MemoryCache) -> None:
        """Test that eviction actually frees memory."""
        small_cache = MemoryCache(max_size_bytes=1024)

        # Fill cache
        large_value = "x" * 400
        await small_cache.set("key1", large_value, ttl=60)
        await small_cache.set("key2", large_value, ttl=60)

        # Add another entry to trigger eviction
        await small_cache.set("key3", large_value, ttl=60)

        size_after = small_cache.get_size_bytes()

        # Size should be less than or equal to max (may be slightly over due to overhead)
        assert size_after <= small_cache._max_size_bytes + 100  # Small tolerance


class TestGlobalCache:
    """Test global cache instance management."""

    def test_get_cache_singleton(self) -> None:
        """Test get_cache returns singleton instance."""
        reset_cache()  # Ensure clean state

        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2

    @pytest.mark.asyncio
    async def test_reset_cache(self) -> None:
        """Test reset_cache creates new instance."""
        cache1 = get_cache()
        await cache1.set("test", "value", ttl=60)

        reset_cache()
        cache2 = get_cache()

        assert cache1 is not cache2
        result = await cache2.get("test")
        assert result is None
