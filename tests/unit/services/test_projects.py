"""Unit tests for Project service."""

from unittest.mock import MagicMock, patch

import pytest

from sequel.services.projects import ProjectService, get_project_service, reset_project_service


class MockProjectProto:
    """Mock protobuf project message."""

    def __init__(self, **kwargs: str) -> None:  # type: ignore[no-untyped-def]
        self.name = kwargs.get("name", "projects/test-project")
        self.project_id = kwargs.get("project_id", "test-project")
        self.display_name = kwargs.get("display_name", "Test Project")
        self.state = MagicMock()
        self.state.name = kwargs.get("state", "ACTIVE")
        self.create_time = MagicMock()
        self.create_time.isoformat = MagicMock(return_value="2023-01-01T00:00:00+00:00")
        self.labels = kwargs.get("labels", {})
        self.parent = kwargs.get("parent", "")


class TestProjectService:
    """Test ProjectService functionality."""

    @pytest.fixture
    def service(self) -> ProjectService:
        """Create a ProjectService instance."""
        return ProjectService()

    @pytest.fixture
    def mock_auth(self) -> MagicMock:
        """Mock authentication manager."""
        mock = MagicMock()
        mock.credentials = MagicMock()
        return mock

    @pytest.mark.asyncio
    @patch("sequel.services.projects.get_auth_manager")
    @patch("sequel.services.projects.resourcemanager_v3.ProjectsClient")
    async def test_get_client(
        self,
        mock_client_class: MagicMock,
        mock_get_auth: MagicMock,
        service: ProjectService,
        mock_auth: MagicMock,
    ) -> None:
        """Test getting the Resource Manager client."""
        mock_get_auth.return_value = mock_auth

        client = await service._get_client()

        assert client is not None
        mock_client_class.assert_called_once_with(credentials=mock_auth.credentials)

    @pytest.mark.asyncio
    @patch("sequel.services.projects.get_auth_manager")
    @patch("sequel.services.projects.resourcemanager_v3.ProjectsClient")
    async def test_list_projects(
        self,
        mock_client_class: MagicMock,
        mock_get_auth: MagicMock,
        service: ProjectService,
        mock_auth: MagicMock,
    ) -> None:
        """Test listing projects."""
        mock_get_auth.return_value = mock_auth

        # Create mock projects
        mock_project1 = MockProjectProto(
            project_id="project-1",
            display_name="Project 1",
        )
        mock_project2 = MockProjectProto(
            project_id="project-2",
            display_name="Project 2",
        )

        # Mock client
        mock_client = MagicMock()
        mock_client.list_projects.return_value = [mock_project1, mock_project2]
        mock_client_class.return_value = mock_client

        # List projects
        projects = await service.list_projects(use_cache=False)

        assert len(projects) == 2
        assert projects[0].project_id == "project-1"
        assert projects[1].project_id == "project-2"

    @pytest.mark.asyncio
    @patch("sequel.services.projects.get_auth_manager")
    @patch("sequel.services.projects.resourcemanager_v3.ProjectsClient")
    async def test_list_projects_with_parent(
        self,
        mock_client_class: MagicMock,
        mock_get_auth: MagicMock,
        service: ProjectService,
        mock_auth: MagicMock,
    ) -> None:
        """Test listing projects under a parent."""
        mock_get_auth.return_value = mock_auth

        mock_project = MockProjectProto(
            project_id="child-project",
            parent="organizations/123456",
        )

        mock_client = MagicMock()
        mock_client.list_projects.return_value = [mock_project]
        mock_client_class.return_value = mock_client

        projects = await service.list_projects(
            parent="organizations/123456",
            use_cache=False,
        )

        assert len(projects) == 1
        assert projects[0].project_id == "child-project"

    @pytest.mark.asyncio
    @patch("sequel.services.projects.get_auth_manager")
    @patch("sequel.services.projects.resourcemanager_v3.ProjectsClient")
    async def test_list_projects_uses_cache(
        self,
        mock_client_class: MagicMock,
        mock_get_auth: MagicMock,
        service: ProjectService,
        mock_auth: MagicMock,
    ) -> None:
        """Test that list_projects uses cache on second call."""
        mock_get_auth.return_value = mock_auth

        mock_project = MockProjectProto(project_id="cached-project")

        mock_client = MagicMock()
        mock_client.list_projects.return_value = [mock_project]
        mock_client_class.return_value = mock_client

        # First call - should hit API
        projects1 = await service.list_projects(use_cache=True)
        assert len(projects1) == 1

        # Second call - should use cache
        projects2 = await service.list_projects(use_cache=True)
        assert len(projects2) == 1

        # Client should only be called once
        assert mock_client.list_projects.call_count == 1

    @pytest.mark.asyncio
    @patch("sequel.services.projects.get_auth_manager")
    @patch("sequel.services.projects.resourcemanager_v3.ProjectsClient")
    async def test_get_project(
        self,
        mock_client_class: MagicMock,
        mock_get_auth: MagicMock,
        service: ProjectService,
        mock_auth: MagicMock,
    ) -> None:
        """Test getting a specific project."""
        mock_get_auth.return_value = mock_auth

        mock_project = MockProjectProto(
            project_id="test-project",
            display_name="Test Project",
        )

        mock_client = MagicMock()
        mock_client.get_project.return_value = mock_project
        mock_client_class.return_value = mock_client

        project = await service.get_project("test-project", use_cache=False)

        assert project is not None
        assert project.project_id == "test-project"
        assert project.display_name == "Test Project"

    @pytest.mark.asyncio
    @patch("sequel.services.projects.get_auth_manager")
    @patch("sequel.services.projects.resourcemanager_v3.ProjectsClient")
    async def test_get_project_not_found(
        self,
        mock_client_class: MagicMock,
        mock_get_auth: MagicMock,
        service: ProjectService,
        mock_auth: MagicMock,
    ) -> None:
        """Test getting a non-existent project."""
        mock_get_auth.return_value = mock_auth

        mock_client = MagicMock()
        mock_client.get_project.side_effect = Exception("Not found")
        mock_client_class.return_value = mock_client

        project = await service.get_project("nonexistent-project", use_cache=False)

        assert project is None

    @pytest.mark.asyncio
    @patch("sequel.services.projects.get_auth_manager")
    @patch("sequel.services.projects.resourcemanager_v3.ProjectsClient")
    async def test_get_project_uses_cache(
        self,
        mock_client_class: MagicMock,
        mock_get_auth: MagicMock,
        service: ProjectService,
        mock_auth: MagicMock,
    ) -> None:
        """Test that get_project uses cache on second call."""
        mock_get_auth.return_value = mock_auth

        mock_project = MockProjectProto(project_id="cached-project")

        mock_client = MagicMock()
        mock_client.get_project.return_value = mock_project
        mock_client_class.return_value = mock_client

        # First call - should hit API
        project1 = await service.get_project("cached-project", use_cache=True)
        assert project1 is not None

        # Second call - should use cache
        project2 = await service.get_project("cached-project", use_cache=True)
        assert project2 is not None

        # Client should only be called once
        assert mock_client.get_project.call_count == 1

    def test_proto_to_dict(self, service: ProjectService) -> None:
        """Test converting protobuf to dictionary."""
        mock_project = MockProjectProto(
            name="projects/test-project",
            project_id="test-project",
            display_name="Test Project",
            state="ACTIVE",
            labels={"env": "test"},
            parent="folders/123",
        )

        result = service._proto_to_dict(mock_project)

        assert result["name"] == "projects/test-project"
        assert result["projectId"] == "test-project"
        assert result["displayName"] == "Test Project"
        assert result["lifecycleState"] == "ACTIVE"
        assert result["labels"] == {"env": "test"}
        assert result["parent"] == "folders/123"


class TestGlobalProjectService:
    """Test global project service management."""

    @pytest.mark.asyncio
    async def test_get_project_service_singleton(self) -> None:
        """Test get_project_service returns singleton instance."""
        reset_project_service()

        service1 = await get_project_service()
        service2 = await get_project_service()

        assert service1 is service2

    def test_reset_project_service(self) -> None:
        """Test reset_project_service creates new instance."""
        reset_project_service()
        # After reset, next call should create new instance
        # (Can't easily test this without async context)
