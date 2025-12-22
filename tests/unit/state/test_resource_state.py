"""Tests for ResourceState manager."""

from unittest.mock import AsyncMock, patch

import pytest

from sequel.models.clouddns import DNSRecord, ManagedZone
from sequel.models.cloudsql import CloudSQLInstance
from sequel.models.project import Project
from sequel.state.resource_state import ResourceState, get_resource_state, reset_resource_state


@pytest.fixture
def state() -> ResourceState:
    """Create a fresh state instance for testing."""
    reset_resource_state()
    return get_resource_state()


@pytest.fixture
def mock_project() -> Project:
    """Create a mock project for testing."""
    return Project(
        id="projects/test-project-1",
        name="Test Project 1",
        project_id="test-project-1",
        display_name="Test Project 1",
        state="ACTIVE",
        parent=None,
    )


@pytest.fixture
def mock_dns_zone() -> ManagedZone:
    """Create a mock DNS zone for testing."""
    return ManagedZone(
        id="example-zone",
        name="example.com.",
        zone_name="example-zone",
        dns_name="example.com.",
        visibility="public",
        name_servers=["ns1.example.com.", "ns2.example.com."],
    )


@pytest.fixture
def mock_dns_record() -> DNSRecord:
    """Create a mock DNS record for testing."""
    return DNSRecord(
        id="www.example.com.:A",
        name="www.example.com.",
        record_name="www.example.com.",
        record_type="A",
        ttl=300,
        rrdatas=["1.2.3.4"],
    )


class TestResourceStateLoading:
    """Test resource loading functionality."""

    @pytest.mark.asyncio
    async def test_load_projects_first_time(
        self, state: ResourceState, mock_project: Project
    ) -> None:
        """Test loading projects for the first time."""
        with patch("sequel.state.resource_state.get_project_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_projects = AsyncMock(return_value=[mock_project])
            mock_get_service.return_value = mock_service

            # Load projects
            projects = await state.load_projects()

            # Should call service
            mock_service.list_projects.assert_called_once_with(use_cache=True)

            # Should return projects
            assert len(projects) == 1
            assert projects[0].project_id == "test-project-1"

            # Should be marked as loaded
            assert state.is_loaded("projects")

            # Should be stored in state
            assert len(state._projects) == 1
            assert "test-project-1" in state._projects

    @pytest.mark.asyncio
    async def test_load_projects_from_cache(
        self, state: ResourceState, mock_project: Project
    ) -> None:
        """Test that subsequent loads use state cache."""
        with patch("sequel.state.resource_state.get_project_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_projects = AsyncMock(return_value=[mock_project])
            mock_get_service.return_value = mock_service

            # First load
            await state.load_projects()
            assert mock_service.list_projects.call_count == 1

            # Second load (should use state cache)
            projects = await state.load_projects()

            # Service should not be called again
            assert mock_service.list_projects.call_count == 1

            # Should still return data from state
            assert len(projects) == 1
            assert projects[0].project_id == "test-project-1"

    @pytest.mark.asyncio
    async def test_load_projects_force_refresh(
        self, state: ResourceState, mock_project: Project
    ) -> None:
        """Test force refresh bypasses state cache."""
        with patch("sequel.state.resource_state.get_project_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_projects = AsyncMock(return_value=[mock_project])
            mock_get_service.return_value = mock_service

            # First load
            await state.load_projects()

            # Force refresh
            projects = await state.load_projects(force_refresh=True)

            # Service should be called with use_cache=False
            assert mock_service.list_projects.call_count == 2
            mock_service.list_projects.assert_called_with(use_cache=False)

            # Should still return data
            assert len(projects) == 1

    @pytest.mark.asyncio
    async def test_load_dns_zones(
        self, state: ResourceState, mock_dns_zone: ManagedZone
    ) -> None:
        """Test loading DNS zones for a project."""
        with patch("sequel.state.resource_state.get_clouddns_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_zones = AsyncMock(return_value=[mock_dns_zone])
            mock_get_service.return_value = mock_service

            # Load zones
            zones = await state.load_dns_zones("test-project-1")

            # Should call service
            mock_service.list_zones.assert_called_once_with("test-project-1", use_cache=True)

            # Should return zones
            assert len(zones) == 1
            assert zones[0].zone_name == "example-zone"

            # Should be marked as loaded
            assert state.is_loaded("test-project-1", "dns_zones")

            # Should be stored in state
            assert "test-project-1" in state._dns_zones
            assert len(state._dns_zones["test-project-1"]) == 1

    @pytest.mark.asyncio
    async def test_load_dns_records(
        self, state: ResourceState, mock_dns_record: DNSRecord
    ) -> None:
        """Test loading DNS records for a zone."""
        with patch("sequel.state.resource_state.get_clouddns_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_records = AsyncMock(return_value=[mock_dns_record])
            mock_get_service.return_value = mock_service

            # Load records
            records = await state.load_dns_records("test-project-1", "example-zone")

            # Should call service
            mock_service.list_records.assert_called_once_with(
                "test-project-1", "example-zone", use_cache=True
            )

            # Should return records
            assert len(records) == 1
            assert records[0].record_name == "www.example.com."

            # Should be marked as loaded
            assert state.is_loaded("test-project-1", "example-zone", "dns_records")

            # Should be stored in state
            key = ("test-project-1", "example-zone")
            assert key in state._dns_records
            assert len(state._dns_records[key]) == 1

    @pytest.mark.asyncio
    async def test_load_cloudsql_instances(self, state: ResourceState) -> None:
        """Test loading Cloud SQL instances."""
        mock_instance = CloudSQLInstance(
            id="test-db",
            name="test-db",
            instance_name="test-db",
            database_version="POSTGRES_14",
            state="RUNNABLE",
            region="us-central1",
            tier="db-f1-micro",
        )

        with patch("sequel.state.resource_state.get_cloudsql_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances = AsyncMock(return_value=[mock_instance])
            mock_get_service.return_value = mock_service

            # Load instances
            instances = await state.load_cloudsql_instances("test-project-1")

            # Should call service
            mock_service.list_instances.assert_called_once_with("test-project-1", use_cache=True)

            # Should return instances
            assert len(instances) == 1
            assert instances[0].instance_name == "test-db"

            # Should be marked as loaded
            assert state.is_loaded("test-project-1", "cloudsql")


class TestResourceStateGetters:
    """Test state getter methods."""

    def test_get_project(self, state: ResourceState, mock_project: Project) -> None:
        """Test getting a project from state."""
        # Add project to state
        state._projects["test-project-1"] = mock_project

        # Get project
        project = state.get_project("test-project-1")

        assert project is not None
        assert project.project_id == "test-project-1"

    def test_get_project_not_found(self, state: ResourceState) -> None:
        """Test getting a project that doesn't exist."""
        project = state.get_project("nonexistent")

        assert project is None

    def test_get_dns_zones(self, state: ResourceState, mock_dns_zone: ManagedZone) -> None:
        """Test getting DNS zones from state."""
        # Add zones to state
        state._dns_zones["test-project-1"] = [mock_dns_zone]

        # Get zones
        zones = state.get_dns_zones("test-project-1")

        assert len(zones) == 1
        assert zones[0].zone_name == "example-zone"

    def test_get_dns_zones_empty(self, state: ResourceState) -> None:
        """Test getting DNS zones when none are loaded."""
        zones = state.get_dns_zones("test-project-1")

        # Should return empty list, not None
        assert zones == []

    def test_get_dns_records(self, state: ResourceState, mock_dns_record: DNSRecord) -> None:
        """Test getting DNS records from state."""
        # Add records to state
        state._dns_records[("test-project-1", "example-zone")] = [mock_dns_record]

        # Get records
        records = state.get_dns_records("test-project-1", "example-zone")

        assert len(records) == 1
        assert records[0].record_name == "www.example.com."

    def test_get_dns_records_empty(self, state: ResourceState) -> None:
        """Test getting DNS records when none are loaded."""
        records = state.get_dns_records("test-project-1", "example-zone")

        # Should return empty list, not None
        assert records == []


class TestResourceStateInvalidation:
    """Test state invalidation functionality."""

    def test_invalidate_project(self, state: ResourceState, mock_project: Project) -> None:
        """Test invalidating a single project."""
        # Setup state with project data
        state._projects["test-project-1"] = mock_project
        state._dns_zones["test-project-1"] = []
        state._cloudsql["test-project-1"] = []
        state._loaded.add(("test-project-1", "dns_zones"))
        state._loaded.add(("test-project-1", "cloudsql"))

        # Invalidate project
        state.invalidate_project("test-project-1")

        # Project should be removed
        assert "test-project-1" not in state._projects

        # Resources should be removed
        assert "test-project-1" not in state._dns_zones
        assert "test-project-1" not in state._cloudsql

        # Loaded tracking should be cleared
        assert ("test-project-1", "dns_zones") not in state._loaded
        assert ("test-project-1", "cloudsql") not in state._loaded

    def test_invalidate_project_with_nested_resources(
        self, state: ResourceState, mock_project: Project
    ) -> None:
        """Test invalidating a project with nested resources."""
        # Setup state with nested resources
        state._projects["test-project-1"] = mock_project
        state._dns_records[("test-project-1", "zone1")] = []
        state._dns_records[("test-project-1", "zone2")] = []
        state._compute_instances[("test-project-1", "group1")] = []

        # Invalidate project
        state.invalidate_project("test-project-1")

        # Nested resources should be removed
        assert ("test-project-1", "zone1") not in state._dns_records
        assert ("test-project-1", "zone2") not in state._dns_records
        assert ("test-project-1", "group1") not in state._compute_instances

    def test_invalidate_all(self, state: ResourceState, mock_project: Project) -> None:
        """Test invalidating all state."""
        # Setup state with multiple projects
        state._projects["test-project-1"] = mock_project
        state._projects["test-project-2"] = mock_project
        state._dns_zones["test-project-1"] = []
        state._loaded.add(("projects",))
        state._loaded.add(("test-project-1", "dns_zones"))

        # Invalidate all
        state.invalidate_all()

        # Everything should be cleared
        assert len(state._projects) == 0
        assert len(state._dns_zones) == 0
        assert len(state._loaded) == 0

    def test_invalidate_project_does_not_affect_others(
        self, state: ResourceState, mock_project: Project
    ) -> None:
        """Test that invalidating one project doesn't affect others."""
        # Setup state with multiple projects
        state._projects["test-project-1"] = mock_project
        state._projects["test-project-2"] = mock_project
        state._dns_zones["test-project-1"] = []
        state._dns_zones["test-project-2"] = []

        # Invalidate only project-1
        state.invalidate_project("test-project-1")

        # Project-1 should be removed
        assert "test-project-1" not in state._projects
        assert "test-project-1" not in state._dns_zones

        # Project-2 should remain
        assert "test-project-2" in state._projects
        assert "test-project-2" in state._dns_zones


class TestResourceStateIsLoaded:
    """Test is_loaded functionality."""

    def test_is_loaded_true(self, state: ResourceState) -> None:
        """Test is_loaded returns True when resource is loaded."""
        state._loaded.add(("test-project-1", "dns_zones"))

        assert state.is_loaded("test-project-1", "dns_zones")

    def test_is_loaded_false(self, state: ResourceState) -> None:
        """Test is_loaded returns False when resource is not loaded."""
        assert not state.is_loaded("test-project-1", "dns_zones")

    def test_is_loaded_partial_key(self, state: ResourceState) -> None:
        """Test is_loaded with partial keys."""
        state._loaded.add(("projects",))

        assert state.is_loaded("projects")
        assert not state.is_loaded("test-project-1", "dns_zones")


class TestResourceStateSingleton:
    """Test singleton behavior."""

    def test_get_resource_state_returns_same_instance(self) -> None:
        """Test that get_resource_state returns the same instance."""
        reset_resource_state()

        state1 = get_resource_state()
        state2 = get_resource_state()

        assert state1 is state2

    def test_reset_resource_state_creates_new_instance(self) -> None:
        """Test that reset_resource_state creates a new instance."""
        state1 = get_resource_state()

        reset_resource_state()
        state2 = get_resource_state()

        assert state1 is not state2
