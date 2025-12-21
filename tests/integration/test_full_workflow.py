"""Integration tests for complete user workflows.

These tests simulate realistic user scenarios by mocking GCP APIs
and testing the full stack from service layer through models.
"""

from unittest.mock import MagicMock, patch

import pytest

from sequel.cache.memory import reset_cache
from sequel.services.auth import reset_auth_manager
from sequel.services.cloudsql import reset_cloudsql_service
from sequel.services.compute import reset_compute_service
from sequel.services.gke import reset_gke_service
from sequel.services.projects import reset_project_service
from sequel.services.secrets import reset_secret_manager_service

from .conftest import create_mock_gke_cluster, create_mock_project, create_mock_secret


@pytest.fixture(autouse=True)
def reset_all_services():
    """Reset all service singletons before each test."""
    reset_project_service()
    reset_cloudsql_service()
    reset_compute_service()
    reset_gke_service()
    reset_secret_manager_service()
    reset_auth_manager()
    reset_cache()
    yield
    # Cleanup after test
    reset_project_service()
    reset_cloudsql_service()
    reset_compute_service()
    reset_gke_service()
    reset_secret_manager_service()
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


@pytest.fixture
def mock_projects_data():
    """Mock project list API response."""
    return [
        {
            "name": "projects/proj-prod-web",
            "projectId": "proj-prod-web",
            "displayName": "Production Web",
            "lifecycleState": "ACTIVE",
            "createTime": "2024-01-01T00:00:00Z",
            "labels": {"env": "prod"},
        },
        {
            "name": "projects/proj-dev-api",
            "projectId": "proj-dev-api",
            "displayName": "Development API",
            "lifecycleState": "ACTIVE",
            "createTime": "2024-01-15T00:00:00Z",
            "labels": {"env": "dev"},
        },
    ]


@pytest.fixture
def mock_cloudsql_data():
    """Mock CloudSQL instances API response."""
    return {
        "items": [
            {
                "name": "postgres-main",
                "project": "proj-prod-web",
                "databaseVersion": "POSTGRES_14",
                "region": "us-central1",
                "state": "RUNNABLE",
                "settings": {"tier": "db-custom-2-7680"},
                "ipAddresses": [{"type": "PRIMARY", "ipAddress": "10.1.2.3"}],
            }
        ]
    }


@pytest.fixture
def mock_gke_data():
    """Mock GKE cluster API response."""
    return {
        "clusters": [
            {
                "name": "production-cluster",
                "location": "us-central1",
                "status": "RUNNING",
                "currentMasterVersion": "1.27.3-gke.100",
                "currentNodeVersion": "1.27.3-gke.100",
                "nodePools": [
                    {
                        "name": "default-pool",
                        "config": {
                            "machineType": "e2-standard-4",
                            "diskSizeGb": 100,
                        },
                        "initialNodeCount": 3,
                        "status": {"state": "RUNNING"},
                    }
                ],
            }
        ]
    }


@pytest.fixture
def mock_secrets_data():
    """Mock Secret Manager API response."""
    return [
        MagicMock(
            name="projects/proj-prod-web/secrets/db-password",
            replication=MagicMock(automatic=MagicMock()),
            create_time=MagicMock(isoformat=lambda: "2024-01-01T00:00:00Z"),
            labels={"env": "prod"},
        )
    ]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_project_browsing_workflow(
    mock_gcp_credentials,
    mock_projects_data,
    mock_cloudsql_data,
    mock_gke_data,
    mock_secrets_data,
):
    """Test complete workflow: authenticate → list projects → view resources.

    This simulates a user:
    1. Launching Sequel (authentication)
    2. Viewing project list
    3. Expanding a project to view CloudSQL instances
    4. Expanding a project to view GKE clusters
    5. Expanding a project to view Secrets
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.cloudsql import get_cloudsql_service
    from sequel.services.gke import get_gke_service
    from sequel.services.projects import get_project_service
    from sequel.services.secrets import get_secret_manager_service

    # Step 1: Mock authentication
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "proj-prod-web")

        # Initialize auth manager
        auth_manager = await get_auth_manager()
        assert auth_manager.credentials.valid
        assert auth_manager.project_id == "proj-prod-web"

    # Step 2: List projects
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        # Mock SearchProjects to return our test projects
        mock_instance = mock_client.return_value
        # Use helper to create proper mock projects
        mock_projs = [
            create_mock_project(
                project_id=proj["projectId"],
                display_name=proj["displayName"],
                state=proj["lifecycleState"],
                create_time=proj["createTime"],
                labels=proj["labels"],
            )
            for proj in mock_projects_data
        ]
        mock_instance.search_projects.return_value = mock_projs

        project_service = await get_project_service()
        projects = await project_service.list_projects(use_cache=False)

        assert len(projects) == 2
        assert projects[0].project_id == "proj-prod-web"
        assert projects[0].display_name == "Production Web"
        assert projects[1].project_id == "proj-dev-api"

        # Verify projects are cached
        cached_projects = await project_service.list_projects(use_cache=True)
        assert cached_projects == projects

    # Step 3: View CloudSQL instances for first project
    with patch("sequel.services.cloudsql.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client
        mock_client.instances().list().execute.return_value = mock_cloudsql_data

        cloudsql_service = await get_cloudsql_service()
        instances = await cloudsql_service.list_instances(
            "proj-prod-web", use_cache=False
        )

        assert len(instances) == 1
        assert instances[0].name == "postgres-main"
        assert instances[0].database_version == "POSTGRES_14"
        assert instances[0].state == "RUNNABLE"

    # Step 4: View GKE clusters for first project
    with patch(
        "sequel.services.gke.container_v1.ClusterManagerClient"
    ) as mock_gke_client:
        mock_instance = mock_gke_client.return_value
        mock_instance.list_clusters.return_value = MagicMock(
            clusters=[
                create_mock_gke_cluster(
                    name="production-cluster",
                    location="us-central1",
                    status="RUNNING",
                )
            ]
        )

        gke_service = await get_gke_service()
        clusters = await gke_service.list_clusters("proj-prod-web", use_cache=False)

        assert len(clusters) == 1
        assert clusters[0].name == "production-cluster"
        assert clusters[0].status == "RUNNING"

    # Step 5: View Secrets for first project
    with patch(
        "sequel.services.secrets.secretmanager_v1.SecretManagerServiceClient"
    ) as mock_secret_client:
        mock_instance = mock_secret_client.return_value
        mock_instance.list_secrets.return_value = [
            create_mock_secret(
                name="db-password",
                project_id="proj-prod-web",
                labels={"env": "prod"},
            )
        ]

        secrets_service = await get_secret_manager_service()
        secrets = await secrets_service.list_secrets("proj-prod-web", use_cache=False)

        assert len(secrets) == 1
        assert "db-password" in secrets[0].name
        # Verify only metadata is retrieved (no secret value attribute exists)
        assert hasattr(secrets[0], "secret_name")
        assert not hasattr(secrets[0], "secret_value")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_recovery_workflow(mock_gcp_credentials):
    """Test error recovery across multiple operations.

    Simulates:
    1. Initial successful project load
    2. Permission error on CloudSQL
    3. Quota error on GKE (with retry)
    4. Successful Secret Manager access
    """
    from google.api_core.exceptions import PermissionDenied, ResourceExhausted

    from sequel.services.auth import get_auth_manager
    from sequel.services.cloudsql import get_cloudsql_service
    from sequel.services.gke import get_gke_service
    from sequel.services.projects import get_project_service
    from sequel.services.secrets import get_secret_manager_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    # Step 1: Successful project listing
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            create_mock_project(
                project_id="test-project",
                display_name="Test Project",
            )
        ]

        project_service = await get_project_service()
        projects = await project_service.list_projects(use_cache=False)
        assert len(projects) == 1

    # Step 2: Permission denied on CloudSQL
    # Note: Service catches errors and returns empty list instead of raising
    with patch("sequel.services.cloudsql.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client
        mock_client.instances().list().execute.side_effect = PermissionDenied(
            "Permission 'cloudsql.instances.list' denied"
        )

        cloudsql_service = await get_cloudsql_service()
        # Service catches permission errors and returns empty list
        instances = await cloudsql_service.list_instances("test-project", use_cache=False)
        assert len(instances) == 0  # Empty due to error

    # Step 3: Quota exceeded on GKE
    # Note: Service catches errors and returns empty list instead of raising
    with patch("sequel.services.gke.container_v1.ClusterManagerClient") as mock_client:
        mock_instance = mock_client.return_value
        # Simulate quota exceeded on all attempts
        mock_instance.list_clusters.side_effect = ResourceExhausted(
            "Quota exceeded for quota metric 'Read requests'"
        )

        gke_service = await get_gke_service()
        # Service catches quota errors and returns empty list
        clusters = await gke_service.list_clusters("test-project", use_cache=False)
        assert len(clusters) == 0  # Empty due to error

    # Step 4: Successful Secret Manager access (after previous errors)
    with patch(
        "sequel.services.secrets.secretmanager_v1.SecretManagerServiceClient"
    ) as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.list_secrets.return_value = [
            create_mock_secret(
                name="api-key",
                project_id="test-project",
            )
        ]

        secrets_service = await get_secret_manager_service()
        secrets = await secrets_service.list_secrets("test-project", use_cache=False)

        # Should succeed despite previous errors
        assert len(secrets) == 1
        assert "api-key" in secrets[0].name


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multi_project_workflow(mock_gcp_credentials):
    """Test browsing resources across multiple projects.

    Simulates:
    1. List multiple projects
    2. View resources in project 1
    3. View resources in project 2
    4. Verify cache isolation between projects
    """
    from sequel.services.auth import get_auth_manager
    from sequel.services.cloudsql import get_cloudsql_service
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "project-1")
        await get_auth_manager()

    # Step 1: List multiple projects
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            create_mock_project(
                project_id=f"project-{i}",
                display_name=f"Project {i}",
            )
            for i in range(1, 4)  # 3 projects
        ]

        project_service = await get_project_service()
        projects = await project_service.list_projects(use_cache=False)
        assert len(projects) == 3

    # Step 2: View CloudSQL in project 1
    with patch("sequel.services.cloudsql.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client
        mock_client.instances().list().execute.return_value = {
            "items": [
                {
                    "name": "db-project-1",
                    "project": "project-1",
                    "databaseVersion": "POSTGRES_14",
                    "region": "us-central1",
                    "state": "RUNNABLE",
                }
            ]
        }

        cloudsql_service = await get_cloudsql_service()
        instances_p1 = await cloudsql_service.list_instances(
            "project-1", use_cache=True  # Cache the data
        )
        assert len(instances_p1) == 1
        assert instances_p1[0].name == "db-project-1"

    # Step 3: View CloudSQL in project 2 (different results)
    # Reset client cache to ensure new mock is used
    cloudsql_service._client = None

    with patch("sequel.services.cloudsql.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client
        mock_client.instances().list().execute.return_value = {
            "items": [
                {
                    "name": "db-project-2-primary",
                    "project": "project-2",
                    "databaseVersion": "MYSQL_8_0",
                    "region": "us-east1",
                    "state": "RUNNABLE",
                },
                {
                    "name": "db-project-2-replica",
                    "project": "project-2",
                    "databaseVersion": "MYSQL_8_0",
                    "region": "us-east1",
                    "state": "RUNNABLE",
                },
            ]
        }

        instances_p2 = await cloudsql_service.list_instances(
            "project-2", use_cache=True  # Cache the data
        )
        assert len(instances_p2) == 2
        assert instances_p2[0].name == "db-project-2-primary"

    # Step 4: Verify cached data is isolated per project
    # Re-fetch project 1 from cache
    instances_p1_cached = await cloudsql_service.list_instances(
        "project-1", use_cache=True
    )
    assert len(instances_p1_cached) == 1
    assert instances_p1_cached[0].name == "db-project-1"

    # Re-fetch project 2 from cache
    instances_p2_cached = await cloudsql_service.list_instances(
        "project-2", use_cache=True
    )
    assert len(instances_p2_cached) == 2
    assert instances_p2_cached[0].name == "db-project-2-primary"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_refresh_workflow(mock_gcp_credentials):
    """Test refresh workflow (invalidate cache and reload).

    Simulates:
    1. Load projects (cached)
    2. Load resources (cached)
    3. User presses 'r' to refresh
    4. Cache invalidated, fresh data loaded
    """
    from sequel.cache.memory import get_cache
    from sequel.services.auth import get_auth_manager
    from sequel.services.projects import get_project_service

    # Setup auth
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        await get_auth_manager()

    cache = get_cache()

    # Step 1: Initial load (cache miss)
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            create_mock_project(
                project_id="original-project",
                display_name="Original",
            )
        ]

        project_service = await get_project_service()
        projects = await project_service.list_projects(use_cache=True)
        assert len(projects) == 1
        assert projects[0].project_id == "original-project"

    # Step 2: Second load (cache hit - no API call)
    cached_projects = await project_service.list_projects(use_cache=True)
    assert len(cached_projects) == 1
    assert cached_projects[0].project_id == "original-project"
    # Verify it's the same object from cache
    assert cached_projects is projects

    # Step 3: Simulate refresh (invalidate cache)
    cache_key = "projects:all"
    await cache.invalidate(cache_key)
    # Reset service client to ensure new mock is used
    project_service._client = None

    # Step 4: Load again with updated data (cache miss)
    with patch("sequel.services.projects.resourcemanager_v3.ProjectsClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search_projects.return_value = [
            create_mock_project(
                project_id="updated-project",
                display_name="Updated",
                create_time="2024-01-02T00:00:00Z",
                labels={"updated": "true"},
            )
        ]

        refreshed_projects = await project_service.list_projects(use_cache=True)
        assert len(refreshed_projects) == 1
        assert refreshed_projects[0].project_id == "updated-project"
        assert refreshed_projects[0].labels.get("updated") == "true"
