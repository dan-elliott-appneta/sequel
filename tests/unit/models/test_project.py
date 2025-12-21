"""Unit tests for Project model."""



from sequel.models.project import Project


class TestProject:
    """Test Project model functionality."""

    def test_create_project(self) -> None:
        """Test creating a Project instance."""
        project = Project(
            id="my-project",
            name="My Project",
            project_id="my-project",
            project_number="123456789",
            display_name="My Project",
            state="ACTIVE",
            labels={"env": "prod"},
        )

        assert project.id == "my-project"
        assert project.name == "My Project"
        assert project.project_id == "my-project"
        assert project.project_number == "123456789"
        assert project.display_name == "My Project"
        assert project.state == "ACTIVE"
        assert project.labels == {"env": "prod"}

    def test_default_state(self) -> None:
        """Test that state defaults to ACTIVE."""
        project = Project(
            id="my-project",
            name="My Project",
            project_id="my-project",
            display_name="My Project",
        )

        assert project.state == "ACTIVE"

    def test_from_api_response_full(self) -> None:
        """Test creating Project from full API response."""
        data = {
            "name": "projects/my-project",
            "projectId": "my-project",
            "projectNumber": "123456789",
            "displayName": "My Project",
            "lifecycleState": "ACTIVE",
            "createTime": "2023-01-01T00:00:00Z",
            "labels": {"env": "prod"},
            "parent": "folders/123456",
        }

        project = Project.from_api_response(data)

        assert project.id == "my-project"
        assert project.project_id == "my-project"
        assert project.project_number == "123456789"
        assert project.display_name == "My Project"
        assert project.state == "ACTIVE"
        assert project.labels == {"env": "prod"}
        assert project.parent == "folders/123456"
        assert project.created_at is not None

    def test_from_api_response_extract_project_id_from_name(self) -> None:
        """Test extracting project ID from name field."""
        data = {
            "name": "projects/extracted-project-id",
            "displayName": "Test Project",
        }

        project = Project.from_api_response(data)

        assert project.project_id == "extracted-project-id"
        assert project.id == "extracted-project-id"

    def test_from_api_response_minimal(self) -> None:
        """Test creating Project from minimal API response."""
        data = {
            "projectId": "minimal-project",
            "displayName": "Minimal Project",
        }

        project = Project.from_api_response(data)

        assert project.project_id == "minimal-project"
        assert project.display_name == "Minimal Project"
        assert project.state == "ACTIVE"
        assert project.labels == {}

    def test_from_api_response_parent_dict(self) -> None:
        """Test parsing parent from dict format."""
        data = {
            "projectId": "my-project",
            "displayName": "My Project",
            "parent": {"type": "folder", "id": "123456"},
        }

        project = Project.from_api_response(data)

        assert project.parent == "folder/123456"

    def test_from_api_response_parent_string(self) -> None:
        """Test parsing parent from string format."""
        data = {
            "projectId": "my-project",
            "displayName": "My Project",
            "parent": "organizations/789012",
        }

        project = Project.from_api_response(data)

        assert project.parent == "organizations/789012"

    def test_is_active_true(self) -> None:
        """Test is_active returns True for active project."""
        project = Project(
            id="my-project",
            name="My Project",
            project_id="my-project",
            display_name="My Project",
            state="ACTIVE",
        )

        assert project.is_active() is True

    def test_is_active_false(self) -> None:
        """Test is_active returns False for non-active project."""
        project = Project(
            id="my-project",
            name="My Project",
            project_id="my-project",
            display_name="My Project",
            state="DELETE_REQUESTED",
        )

        assert project.is_active() is False

    def test_to_dict(self) -> None:
        """Test converting Project to dictionary."""
        project = Project(
            id="my-project",
            name="My Project",
            project_id="my-project",
            project_number="123456789",
            display_name="My Project",
            state="ACTIVE",
            labels={"env": "prod"},
        )

        result = project.to_dict()

        assert result["id"] == "my-project"
        assert result["project_id"] == "my-project"
        assert result["project_number"] == "123456789"
        assert result["display_name"] == "My Project"
        assert result["state"] == "ACTIVE"
        assert result["labels"] == {"env": "prod"}
