"""Performance benchmarks for Sequel.

These benchmarks measure key performance metrics:
- Project loading time
- Resource tree expansion time
- Cache hit rates
- Memory usage
- API call overhead vs cached calls
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from sequel.cache.memory import MemoryCache, reset_cache
from sequel.models.cloudsql import CloudSQLInstance
from sequel.services.auth import reset_auth_manager
from sequel.services.cloudsql import reset_cloudsql_service
from sequel.services.projects import reset_project_service


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each benchmark."""
    reset_project_service()
    reset_cloudsql_service()
    reset_auth_manager()
    reset_cache()
    yield
    reset_project_service()
    reset_cloudsql_service()
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


def create_mock_project(project_id: str, display_name: str) -> MagicMock:
    """Create a mock project protobuf object."""
    mock_proj = MagicMock()
    mock_proj.name = f"projects/{project_id}"
    mock_proj.project_id = project_id
    mock_proj.display_name = display_name

    state_mock = MagicMock()
    state_mock.name = "ACTIVE"
    state_mock.__str__ = MagicMock(return_value="ACTIVE")
    mock_proj.state = state_mock

    create_time_mock = MagicMock()
    create_time_mock.isoformat = MagicMock(return_value="2024-01-01T00:00:00Z")
    mock_proj.create_time = create_time_mock

    mock_proj.labels = {}
    mock_proj.parent = ""

    return mock_proj


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_project_loading_1_project(mock_gcp_credentials):
    """Benchmark loading 1 project.

    Baseline: Measures single project load time.
    Expected: < 100ms with mocked API
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    # Mock API
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            create_mock_project(
                project_id="project-0",
                display_name="Project 0",
            )
        ]

        project_service = await get_project_service()

        # Measure loading time
        start_time = time.time()
        projects = await project_service.list_projects(use_cache=False)
        end_time = time.time()

        # Assertions
        assert len(projects) == 1
        load_time = end_time - start_time

        # Log benchmark result
        print(f"\n[BENCHMARK] Load 1 project: {load_time * 1000:.2f}ms")
        assert load_time < 0.1  # Should complete in < 100ms


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_project_loading_10_projects(mock_gcp_credentials):
    """Benchmark loading 10 projects.

    Expected: < 200ms with mocked API
    Tests: Model creation and parsing overhead
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    # Mock API
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            create_mock_project(
                project_id=f"project-{i}",
                display_name=f"Project {i}",
            )
            for i in range(10)
        ]

        project_service = await get_project_service()

        # Measure loading time
        start_time = time.time()
        projects = await project_service.list_projects(use_cache=False)
        end_time = time.time()

        # Assertions
        assert len(projects) == 10
        load_time = end_time - start_time

        # Log benchmark result
        print(f"\n[BENCHMARK] Load 10 projects: {load_time * 1000:.2f}ms")
        assert load_time < 0.2  # Should complete in < 200ms


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_project_loading_100_projects(mock_gcp_credentials):
    """Benchmark loading 100 projects.

    Expected: < 1s with mocked API
    Tests: Scalability of model creation
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    # Mock API
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            create_mock_project(
                project_id=f"project-{i}",
                display_name=f"Project {i}",
            )
            for i in range(100)
        ]

        project_service = await get_project_service()

        # Measure loading time
        start_time = time.time()
        projects = await project_service.list_projects(use_cache=False)
        end_time = time.time()

        # Assertions
        assert len(projects) == 100
        load_time = end_time - start_time

        # Log benchmark result
        print(f"\n[BENCHMARK] Load 100 projects: {load_time * 1000:.2f}ms")
        assert load_time < 1.0  # Should complete in < 1s


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_cache_hit_rate():
    """Benchmark cache hit rates.

    Expected: > 90% hit rate on repeated reads
    Tests: Cache effectiveness
    """
    cache = MemoryCache()

    # Fill cache with test data
    num_entries = 100
    for i in range(num_entries):
        await cache.set(f"key-{i}", f"value-{i}", ttl=300)

    # Measure hit rate
    hits = 0
    misses = 0

    # Read all entries (should all hit)
    for i in range(num_entries):
        value = await cache.get(f"key-{i}")
        if value is not None:
            hits += 1
        else:
            misses += 1

    # Try to read non-existent keys (should all miss)
    for i in range(num_entries, num_entries + 10):
        value = await cache.get(f"key-{i}")
        if value is not None:
            hits += 1
        else:
            misses += 1

    hit_rate = hits / (hits + misses) * 100

    # Log benchmark result
    print(f"\n[BENCHMARK] Cache hit rate: {hit_rate:.1f}% ({hits} hits, {misses} misses)")
    assert hit_rate > 90  # Should have > 90% hit rate


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_cache_operations():
    """Benchmark cache operation speeds.

    Expected: Set/Get operations < 1ms each
    Tests: Cache performance
    """
    cache = MemoryCache()

    # Benchmark SET operations
    set_times = []
    for i in range(1000):
        start = time.time()
        await cache.set(f"key-{i}", f"value-{i}", ttl=60)
        end = time.time()
        set_times.append((end - start) * 1000)  # Convert to ms

    avg_set_time = sum(set_times) / len(set_times)

    # Benchmark GET operations
    get_times = []
    for i in range(1000):
        start = time.time()
        await cache.get(f"key-{i}")
        end = time.time()
        get_times.append((end - start) * 1000)  # Convert to ms

    avg_get_time = sum(get_times) / len(get_times)

    # Log benchmark results
    print(f"\n[BENCHMARK] Cache SET: {avg_set_time:.3f}ms avg")
    print(f"[BENCHMARK] Cache GET: {avg_get_time:.3f}ms avg")

    assert avg_set_time < 1.0  # Should be < 1ms
    assert avg_get_time < 1.0  # Should be < 1ms


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_concurrent_cache_operations():
    """Benchmark concurrent cache operations.

    Expected: 1000 concurrent operations complete in < 500ms
    Tests: Cache thread safety and concurrency
    """
    cache = MemoryCache()

    # Benchmark concurrent writes
    async def write_entry(i: int):
        await cache.set(f"key-{i}", f"value-{i}", ttl=60)

    start_time = time.time()
    await asyncio.gather(*[write_entry(i) for i in range(1000)])
    write_time = time.time() - start_time

    # Benchmark concurrent reads
    async def read_entry(i: int):
        return await cache.get(f"key-{i}")

    start_time = time.time()
    results = await asyncio.gather(*[read_entry(i) for i in range(1000)])
    read_time = time.time() - start_time

    # Log benchmark results
    print(f"\n[BENCHMARK] 1000 concurrent writes: {write_time * 1000:.2f}ms")
    print(f"[BENCHMARK] 1000 concurrent reads: {read_time * 1000:.2f}ms")

    assert write_time < 0.5  # Should complete in < 500ms
    assert read_time < 0.5  # Should complete in < 500ms
    assert len(results) == 1000
    assert all(r is not None for r in results)


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_api_vs_cache_overhead(mock_gcp_credentials):
    """Benchmark API call overhead vs cache.

    Expected: Cache should be 100x+ faster than API
    Tests: Cache effectiveness for reducing API calls
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.cloudsql import get_cloudsql_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    # Mock API
    with patch("sequel.services.cloudsql.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client
        mock_client.instances().list().execute.return_value = {
            "items": [
                {
                    "name": f"db-instance-{i}",
                    "project": "test-project",
                    "databaseVersion": "POSTGRES_14",
                    "region": "us-central1",
                    "state": "RUNNABLE",
                }
                for i in range(10)
            ]
        }

        cloudsql_service = await get_cloudsql_service()

        # Benchmark API call (cache miss)
        start_time = time.time()
        instances1 = await cloudsql_service.list_instances("test-project", use_cache=True)
        api_time = time.time() - start_time

        # Benchmark cache hit
        start_time = time.time()
        instances2 = await cloudsql_service.list_instances("test-project", use_cache=True)
        cache_time = time.time() - start_time

        # Log benchmark results
        speedup = api_time / cache_time if cache_time > 0 else 0
        print(f"\n[BENCHMARK] API call (cache miss): {api_time * 1000:.2f}ms")
        print(f"[BENCHMARK] Cache hit: {cache_time * 1000:.2f}ms")
        print(f"[BENCHMARK] Cache speedup: {speedup:.1f}x faster")

        assert len(instances1) == 10
        assert len(instances2) == 10
        assert instances1 is instances2  # Same object from cache
        assert cache_time < api_time  # Cache should be faster


@pytest.mark.benchmark
def test_benchmark_model_creation():
    """Benchmark model creation from API responses.

    Expected: < 1ms per model creation
    Tests: Pydantic model overhead
    """
    # Test data
    api_responses = [
        {
            "name": f"instance-{i}",
            "project": "test-project",
            "databaseVersion": "POSTGRES_14",
            "region": "us-central1",
            "state": "RUNNABLE",
            "settings": {"tier": "db-custom-2-7680"},
            "ipAddresses": [{"type": "PRIMARY", "ipAddress": "10.1.2.3"}],
        }
        for i in range(1000)
    ]

    # Benchmark model creation
    start_time = time.time()
    models = [CloudSQLInstance.from_api_response(data) for data in api_responses]
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / len(models) * 1000  # ms

    # Log benchmark results
    print(f"\n[BENCHMARK] Created {len(models)} models in {total_time * 1000:.2f}ms")
    print(f"[BENCHMARK] Average: {avg_time:.3f}ms per model")

    assert len(models) == 1000
    assert avg_time < 1.0  # Should be < 1ms per model
