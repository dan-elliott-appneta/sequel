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
