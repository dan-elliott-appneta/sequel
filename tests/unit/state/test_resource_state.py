"""Tests for ResourceState class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.cloudsql import CloudSQLInstance
from sequel.models.compute import InstanceGroup
from sequel.models.gke import GKECluster
from sequel.models.iam import ServiceAccount
from sequel.models.project import Project
from sequel.models.secrets import Secret
from sequel.state.resource_state import ResourceState, get_resource_state


class TestResourceState:
    """Test ResourceState class."""

    @pytest.fixture
    def resource_state(self) -> ResourceState:
        """Create a fresh ResourceState instance."""
        return ResourceState()

    @pytest.fixture
    def sample_projects(self) -> list[Project]:
        """Create sample projects for testing."""
        return [
            Project(
                id="proj-1",
                name="Project 1",
                project_id="proj-1",
                display_name="Project 1",
                project_number="111",
                state="ACTIVE",
                labels={},
            ),
            Project(
                id="proj-2",
                name="Project 2",
                project_id="proj-2",
                display_name="Project 2",
                project_number="222",
                state="ACTIVE",
                labels={},
            ),
        ]

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        """Create a mock config with no filters."""
        config = MagicMock()
        config.project_filter_regex = None  # No project filtering
        config.dns_zone_filter = None
        return config

    @pytest.mark.asyncio
    async def test_load_projects_first_time(
        self, resource_state: ResourceState, sample_projects: list[Project], mock_config: MagicMock
    ) -> None:
        """Test loading projects for the first time."""
        with (
            patch("sequel.state.resource_state.get_project_service") as mock_get_service,
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
        ):
            mock_service = AsyncMock()
            mock_service.list_projects.return_value = sample_projects
            mock_get_service.return_value = mock_service

            projects = await resource_state.load_projects()

            assert len(projects) == 2
            assert projects[0].project_id == "proj-1"
            assert projects[1].project_id == "proj-2"
            mock_service.list_projects.assert_called_once_with(use_cache=True)

    @pytest.mark.asyncio
    async def test_load_projects_from_cache(
        self, resource_state: ResourceState, sample_projects: list[Project], mock_config: MagicMock
    ) -> None:
        """Test loading projects from state cache."""
        with (
            patch("sequel.state.resource_state.get_project_service") as mock_get_service,
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
        ):
            mock_service = AsyncMock()
            mock_service.list_projects.return_value = sample_projects
            mock_get_service.return_value = mock_service

            # First load
            await resource_state.load_projects()

            # Second load (should return from cache)
            projects = await resource_state.load_projects()

            assert len(projects) == 2
            # Service should only be called once (first time)
            mock_service.list_projects.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_projects_force_refresh(
        self, resource_state: ResourceState, sample_projects: list[Project], mock_config: MagicMock
    ) -> None:
        """Test force refresh bypasses cache."""
        with (
            patch("sequel.state.resource_state.get_project_service") as mock_get_service,
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
        ):
            mock_service = AsyncMock()
            mock_service.list_projects.return_value = sample_projects
            mock_get_service.return_value = mock_service

            # First load
            await resource_state.load_projects()

            # Force refresh
            projects = await resource_state.load_projects(force_refresh=True)

            assert len(projects) == 2
            # Service should be called twice (force refresh)
            assert mock_service.list_projects.call_count == 2
            mock_service.list_projects.assert_called_with(use_cache=False)

    @pytest.mark.asyncio
    async def test_load_cloudsql_instances(self, resource_state: ResourceState) -> None:
        """Test loading CloudSQL instances."""
        instances = [
            CloudSQLInstance(
                id="sql-1",
                name="sql-1",
                project_id="proj-1",
                instance_name="sql-1",
                database_version="POSTGRES_14",
                region="us-central1",
                tier="db-f1-micro",
                state="RUNNABLE",
                ip_addresses=[],
            ),
        ]

        with patch("sequel.state.resource_state.get_cloudsql_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances.return_value = instances
            mock_get_service.return_value = mock_service

            result = await resource_state.load_cloudsql_instances("proj-1")

            assert len(result) == 1
            assert result[0].instance_name == "sql-1"
            mock_service.list_instances.assert_called_once_with("proj-1", use_cache=True)

    @pytest.mark.asyncio
    async def test_load_compute_groups(self, resource_state: ResourceState) -> None:
        """Test loading compute instance groups."""
        groups = [
            InstanceGroup(
                id="group-1",
                name="group-1",
                project_id="proj-1",
                group_name="group-1",
                zone="us-central1-a",
                size=3,
                is_managed=True,
                template_url="https://...",
            ),
        ]

        with patch("sequel.state.resource_state.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instance_groups.return_value = groups
            mock_get_service.return_value = mock_service

            result = await resource_state.load_compute_groups("proj-1")

            assert len(result) == 1
            assert result[0].group_name == "group-1"

    @pytest.mark.asyncio
    async def test_load_gke_clusters(self, resource_state: ResourceState) -> None:
        """Test loading GKE clusters."""
        clusters = [
            GKECluster(
                id="cluster-1",
                name="cluster-1",
                project_id="proj-1",
                cluster_name="cluster-1",
                location="us-central1-a",
                status="RUNNING",
                endpoint="1.2.3.4",
                node_count=3,
            ),
        ]

        with patch("sequel.state.resource_state.get_gke_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_clusters.return_value = clusters
            mock_get_service.return_value = mock_service

            result = await resource_state.load_gke_clusters("proj-1")

            assert len(result) == 1
            assert result[0].cluster_name == "cluster-1"

    @pytest.mark.asyncio
    async def test_load_secrets(self, resource_state: ResourceState) -> None:
        """Test loading secrets."""
        secrets = [
            Secret(
                id="secret-1",
                name="secret-1",
                project_id="proj-1",
                secret_name="secret-1",
                replication_policy="automatic",
                create_time="2024-01-01T00:00:00Z",
            ),
        ]

        with patch("sequel.state.resource_state.get_secret_manager_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_secrets.return_value = secrets
            mock_get_service.return_value = mock_service

            result = await resource_state.load_secrets("proj-1")

            assert len(result) == 1
            assert result[0].secret_name == "secret-1"

    @pytest.mark.asyncio
    async def test_load_iam_accounts(self, resource_state: ResourceState) -> None:
        """Test loading IAM service accounts."""
        accounts = [
            ServiceAccount(
                id="sa@project.iam.gserviceaccount.com",
                name="Service Account",
                project_id="proj-1",
                email="sa@project.iam.gserviceaccount.com",
                display_name="Service Account",
                disabled=False,
            ),
        ]

        with patch("sequel.state.resource_state.get_iam_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_service_accounts.return_value = accounts
            mock_get_service.return_value = mock_service

            result = await resource_state.load_iam_accounts("proj-1")

            assert len(result) == 1
            assert result[0].email == "sa@project.iam.gserviceaccount.com"

    def test_is_loaded(self, resource_state: ResourceState) -> None:
        """Test checking if resource type is loaded."""
        # Not loaded initially
        assert not resource_state.is_loaded("proj-1", "cloudsql")

        # Mark as loaded
        resource_state._loaded.add(("proj-1", "cloudsql"))

        # Now it's loaded
        assert resource_state.is_loaded("proj-1", "cloudsql")

    def test_get_projects_empty(self, resource_state: ResourceState) -> None:
        """Test getting projects when none are loaded."""
        projects = resource_state.get_projects()
        assert projects == []

    def test_get_projects_with_data(
        self, resource_state: ResourceState, sample_projects: list[Project]
    ) -> None:
        """Test getting projects after loading."""
        resource_state._projects = {p.project_id: p for p in sample_projects}
        resource_state._loaded.add(("projects",))

        projects = resource_state.get_projects()
        assert len(projects) == 2

    def test_get_cloudsql_instances_empty(self, resource_state: ResourceState) -> None:
        """Test getting CloudSQL instances when none loaded."""
        instances = resource_state.get_cloudsql_instances("proj-1")
        assert instances == []

    def test_get_compute_groups_empty(self, resource_state: ResourceState) -> None:
        """Test getting compute groups when none loaded."""
        groups = resource_state.get_compute_groups("proj-1")
        assert groups == []

    def test_get_resource_state_singleton(self) -> None:
        """Test that get_resource_state returns a singleton."""
        state1 = get_resource_state()
        state2 = get_resource_state()
        assert state1 is state2
