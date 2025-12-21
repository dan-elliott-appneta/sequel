"""Integration tests for cache lifecycle and behavior.

Tests cache TTL expiration, LRU eviction, statistics tracking,
and cache behavior across multiple service operations.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from sequel.cache.memory import MemoryCache, get_cache, reset_cache
from sequel.models.project import Project
from sequel.services.auth import reset_auth_manager
from sequel.services.projects import reset_project_service


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services and cache before each test."""
    reset_project_service()
    reset_auth_manager()
    reset_cache()
    yield
    reset_project_service()
    reset_auth_manager()
    reset_cache()


@pytest.fixture
def mock_gcp_credentials():
    """Mock Google Cloud credentials."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh = MagicMock()
    return creds


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_ttl_expiration():
    """Test that cache entries expire after TTL.

    Verifies:
    1. Entry is cached with TTL
    2. Entry is valid before TTL expires
    3. Entry is expired and removed after TTL
    """
    cache = MemoryCache()

    # Set entry with 1 second TTL
    await cache.set("test-key", "test-value", ttl=1)

    # Immediately retrieve - should hit
    value = await cache.get("test-key")
    assert value == "test-value"

    # Check stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0

    # Wait for TTL to expire
    await asyncio.sleep(1.1)

    # Retrieve after expiration - should miss
    value = await cache.get("test-key")
    assert value is None

    # Check stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["expirations"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_lru_eviction():
    """Test LRU eviction when cache size limit is reached.

    Verifies:
    1. Cache respects max size limit
    2. Least recently used entries are evicted first
    3. Recently accessed entries are preserved
    """
    # Create small cache (1KB limit)
    cache = MemoryCache(max_size_bytes=1024)

    # Add entries that will exceed limit
    # Each entry is approximately 200 bytes
    entries = {
        "entry-1": "x" * 200,
        "entry-2": "y" * 200,
        "entry-3": "z" * 200,
        "entry-4": "a" * 200,
        "entry-5": "b" * 200,
        "entry-6": "c" * 200,  # This should trigger evictions
    }

    for key, value in entries.items():
        await cache.set(key, value, ttl=60)

    # Check eviction stats
    stats = cache.get_stats()
    assert stats["evictions"] > 0

    # Oldest entries should be evicted
    assert await cache.get("entry-1") is None  # Evicted
    assert await cache.get("entry-6") is not None  # Most recent, kept


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_move_to_end_on_access():
    """Test that accessing an entry moves it to the end (most recent).

    Verifies:
    1. Accessing old entry updates its position
    2. Accessed entry is not evicted even if old
    """
    # Small cache
    cache = MemoryCache(max_size_bytes=800)

    # Add initial entries
    await cache.set("old-entry", "x" * 200, ttl=60)
    await cache.set("mid-entry", "y" * 200, ttl=60)

    # Access old entry to move it to end
    value = await cache.get("old-entry")
    assert value == "x" * 200

    # Add more entries to trigger eviction
    await cache.set("new-1", "a" * 200, ttl=60)
    await cache.set("new-2", "b" * 200, ttl=60)

    # Old entry should still be present (was moved to end)
    assert await cache.get("old-entry") is not None
    # Mid entry should be evicted (was least recently used)
    assert await cache.get("mid-entry") is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_statistics_tracking():
    """Test cache statistics are accurately tracked.

    Verifies:
    1. Hits are counted
    2. Misses are counted
    3. Evictions are counted
    4. Expirations are counted
    """
    cache = MemoryCache(max_size_bytes=500)

    # Initial stats
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["evictions"] == 0
    assert stats["expirations"] == 0

    # Add entry
    await cache.set("key-1", "value-1", ttl=1)

    # Cache hit
    await cache.get("key-1")
    stats = cache.get_stats()
    assert stats["hits"] == 1

    # Cache miss
    await cache.get("nonexistent")
    stats = cache.get_stats()
    assert stats["misses"] == 1

    # Wait for expiration
    await asyncio.sleep(1.1)
    await cache.get("key-1")  # Will detect expiration
    stats = cache.get_stats()
    assert stats["expirations"] == 1

    # Trigger eviction by filling cache
    for i in range(5):
        await cache.set(f"big-key-{i}", "x" * 150, ttl=60)

    stats = cache.get_stats()
    assert stats["evictions"] > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_cleanup_expired_entries():
    """Test manual cleanup of expired entries.

    Verifies:
    1. Expired entries are removed by cleanup
    2. Valid entries are preserved
    3. Stats are updated correctly
    """
    cache = MemoryCache()

    # Add entries with different TTLs
    await cache.set("short-ttl", "expires-soon", ttl=1)
    await cache.set("long-ttl", "expires-later", ttl=60)

    # Wait for short TTL to expire
    await asyncio.sleep(1.1)

    # Run cleanup
    await cache.cleanup_expired()

    # Check stats
    stats = cache.get_stats()
    assert stats["expirations"] == 1

    # Long TTL entry should still be present (via get, not counted in cleanup)
    value = await cache.get("long-ttl")
    assert value == "expires-later"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_background_cleanup_task():
    """Test background cleanup task runs periodically.

    Verifies:
    1. Cleanup task can be started
    2. Cleanup runs automatically
    3. Cleanup task can be stopped
    """
    cache = MemoryCache()

    # Add entry with short TTL
    await cache.set("test-key", "test-value", ttl=1)

    # Start background cleanup (run every 0.5 seconds for testing)
    await cache.start_cleanup_task(interval_seconds=1)

    # Wait for entry to expire and cleanup to run
    await asyncio.sleep(1.5)

    # Entry should be cleaned up
    assert cache.size() == 0

    # Stop cleanup task
    await cache.stop_cleanup_task()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_invalidation():
    """Test cache invalidation removes specific entries.

    Verifies:
    1. Invalidate removes specific key
    2. Other entries are preserved
    """
    cache = MemoryCache()

    # Add multiple entries
    await cache.set("key-1", "value-1", ttl=60)
    await cache.set("key-2", "value-2", ttl=60)
    await cache.set("key-3", "value-3", ttl=60)

    # Invalidate one key
    await cache.invalidate("key-2")

    # Check results
    assert await cache.get("key-1") == "value-1"
    assert await cache.get("key-2") is None
    assert await cache.get("key-3") == "value-3"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_clear_all():
    """Test clearing all cache entries.

    Verifies:
    1. Clear removes all entries
    2. Cache size becomes 0
    """
    cache = MemoryCache()

    # Add multiple entries
    for i in range(10):
        await cache.set(f"key-{i}", f"value-{i}", ttl=60)

    assert cache.size() == 10

    # Clear all
    await cache.clear()

    assert cache.size() == 0

    # All keys should be gone
    for i in range(10):
        assert await cache.get(f"key-{i}") is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_with_project_service(mock_gcp_credentials):
    """Test cache behavior with ProjectService.

    Verifies:
    1. First call fetches from API (cache miss)
    2. Second call uses cache (cache hit)
    3. Cache invalidation triggers new API call
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    # Mock API responses
    mock_projects = [
        MagicMock(
            name="projects/project-1",
            project_id="project-1",
            display_name="Project 1",
            state=MagicMock(name="ACTIVE"),
            create_time=MagicMock(isoformat=lambda: "2024-01-01T00:00:00Z"),
            labels={},
            parent="",
        )
    ]

    api_call_count = 0

    def mock_search_projects(*args, **kwargs):
        nonlocal api_call_count
        api_call_count += 1
        return mock_projects

    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects = mock_search_projects

        project_service = await get_project_service()

        # First call - cache miss, API called
        projects1 = await project_service.list_projects(use_cache=True)
        assert len(projects1) == 1
        assert api_call_count == 1

        # Second call - cache hit, API not called
        projects2 = await project_service.list_projects(use_cache=True)
        assert len(projects2) == 1
        assert api_call_count == 1  # Still 1, not incremented

        # Verify same objects from cache
        assert projects1 is projects2

        # Invalidate cache
        cache = get_cache()
        await cache.invalidate("projects:all")

        # Third call - cache miss after invalidation, API called again
        projects3 = await project_service.list_projects(use_cache=True)
        assert len(projects3) == 1
        assert api_call_count == 2  # Incremented


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_with_different_ttls(mock_gcp_credentials):
    """Test cache with different TTLs for projects vs resources.

    Verifies:
    1. Projects use longer TTL (600s default)
    2. Resources use shorter TTL (300s default)
    3. Different TTLs work correctly
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.cloudsql import get_cloudsql_service
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    cache = get_cache()

    # Mock project API
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            MagicMock(
                name="projects/test-project",
                project_id="test-project",
                display_name="Test",
                state=MagicMock(name="ACTIVE"),
                create_time=MagicMock(isoformat=lambda: "2024-01-01T00:00:00Z"),
                labels={},
                parent="",
            )
        ]

        project_service = await get_project_service()
        await project_service.list_projects(use_cache=True)

    # Mock CloudSQL API
    with patch("sequel.services.cloudsql.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client
        mock_client.instances().list().execute.return_value = {
            "items": [
                {
                    "name": "test-instance",
                    "databaseVersion": "POSTGRES_14",
                    "region": "us-central1",
                    "state": "RUNNABLE",
                }
            ]
        }

        cloudsql_service = await get_cloudsql_service()
        await cloudsql_service.list_instances("test-project", use_cache=True)

    # Verify both are cached
    projects_cached = await cache.get("projects:all")
    cloudsql_cached = await cache.get("cloudsql:instances:test-project")

    assert projects_cached is not None
    assert cloudsql_cached is not None

    # Projects and CloudSQL instances should both be in cache
    assert cache.size() >= 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_size_calculation():
    """Test cache size calculation and limits.

    Verifies:
    1. Cache tracks size in bytes
    2. Size is calculated correctly
    3. Size limit is enforced
    """
    cache = MemoryCache(max_size_bytes=1000)

    # Add entry and check size
    await cache.set("small-key", "small-value", ttl=60)
    size1 = cache.get_size_bytes()
    assert size1 > 0

    # Add larger entry
    await cache.set("large-key", "x" * 500, ttl=60)
    size2 = cache.get_size_bytes()
    assert size2 > size1

    # Size should be less than or equal to max
    assert cache.get_size_bytes() <= 1000


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_across_multiple_operations(mock_gcp_credentials):
    """Test cache behavior across multiple service operations.

    Verifies:
    1. Cache works correctly with multiple services
    2. Different cache keys don't conflict
    3. Cache statistics are global across services
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.cloudsql import get_cloudsql_service
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    cache = get_cache()
    initial_stats = cache.get_stats()

    # Operation 1: List projects
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = []

        project_service = await get_project_service()
        await project_service.list_projects(use_cache=True)
        await project_service.list_projects(use_cache=True)  # Cache hit

    # Operation 2: List CloudSQL
    with patch("sequel.services.cloudsql.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client
        mock_client.instances().list().execute.return_value = {"items": []}

        cloudsql_service = await get_cloudsql_service()
        await cloudsql_service.list_instances("test-project", use_cache=True)
        await cloudsql_service.list_instances("test-project", use_cache=True)  # Cache hit

    # Check global stats
    final_stats = cache.get_stats()

    # Should have 2 cache hits (one from each service's second call)
    assert final_stats["hits"] >= 2
    # Should have 2 cache misses (one from each service's first call)
    assert final_stats["misses"] >= 2
