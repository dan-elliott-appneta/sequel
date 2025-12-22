"""Tests for detail pane widget."""

import json

import pytest

from sequel.models.base import BaseModel
from sequel.models.project import Project
from sequel.widgets.detail_pane import DetailPane


@pytest.fixture
def detail_pane() -> DetailPane:
    """Create a detail pane widget for testing."""
    return DetailPane()


@pytest.fixture
def sample_project() -> Project:
    """Create a sample project for testing."""
    api_data = {
        "name": "projects/my-project",
        "projectId": "my-project",
        "projectNumber": "123456789",
        "displayName": "My Test Project",
        "lifecycleState": "ACTIVE",
        "createTime": "2023-01-01T00:00:00Z",
        "labels": {"env": "test", "team": "engineering"},
        "parent": "folders/123456",
    }
    return Project.from_api_response(api_data)


@pytest.fixture
def sample_base_model() -> BaseModel:
    """Create a sample base model for testing."""
    return BaseModel(
        id="test-id",
        name="Test Resource",
        project_id="test-project",
        labels={"key": "value"},
        raw_data={
            "id": "test-id",
            "name": "Test Resource",
            "description": "A test resource",
            "status": "ACTIVE",
        },
    )


class TestDetailPane:
    """Test suite for DetailPane widget."""

    def test_initialization(self, detail_pane: DetailPane) -> None:
        """Test detail pane initialization."""
        assert detail_pane.current_resource is None

    def test_update_content_with_none(self, detail_pane: DetailPane) -> None:
        """Test updating detail pane with None resource."""
        detail_pane.update_content(None)
        # The widget should show "No resource selected"
        # We can't easily test the actual rendered content without Textual app context
        assert detail_pane.current_resource is None

    def test_update_content_with_resource(
        self, detail_pane: DetailPane, sample_project: Project
    ) -> None:
        """Test updating detail pane with a resource."""
        detail_pane.update_content(sample_project)
        assert detail_pane.current_resource == sample_project

    def test_format_resource_uses_raw_data(
        self, detail_pane: DetailPane, sample_project: Project
    ) -> None:
        """Test that format_resource uses raw_data when available."""
        result = detail_pane._format_resource(sample_project)

        assert isinstance(result, str)

        # Check that raw_data is present in the formatted output
        assert sample_project.raw_data
        assert "projectId" in sample_project.raw_data
        # JSON string should contain the project ID
        assert "my-project" in result

    def test_format_resource_with_empty_raw_data(
        self, detail_pane: DetailPane
    ) -> None:
        """Test format_resource with empty raw_data falls back to to_dict()."""
        # Create a model with empty raw_data
        model = BaseModel(
            id="test-id",
            name="Test Name",
            project_id="test-project",
            raw_data={},  # Empty raw_data
        )

        result = detail_pane._format_resource(model)

        assert isinstance(result, str)
        # Should use to_dict() as fallback
        # The JSON string should contain the model's dict data
        assert "test-id" in result
        assert "Test Name" in result

    def test_format_resource_json_structure(
        self, detail_pane: DetailPane, sample_base_model: BaseModel
    ) -> None:
        """Test that formatted JSON has correct structure."""
        result = detail_pane._format_resource(sample_base_model)

        assert isinstance(result, str)

        # Check that JSON includes raw_data fields
        assert "description" in result
        assert "A test resource" in result
        assert "ACTIVE" in result

    def test_format_resource_sorts_keys(
        self, detail_pane: DetailPane, sample_base_model: BaseModel
    ) -> None:
        """Test that JSON keys are sorted."""
        result = detail_pane._format_resource(sample_base_model)

        # The result is now a JSON string directly
        assert isinstance(result, str)

        # Parse it back to verify it's valid JSON
        parsed = json.loads(result)

        # Verify it's a dict (JSON object)
        assert isinstance(parsed, dict)

        # Keys should be sorted when we dump again
        expected_keys = sorted(sample_base_model.raw_data.keys())
        actual_keys = list(parsed.keys())
        assert actual_keys == expected_keys

    def test_format_resource_handles_datetime(
        self, detail_pane: DetailPane, sample_project: Project
    ) -> None:
        """Test that datetime objects are properly serialized."""
        # Project has a created_at field which is a datetime
        assert sample_project.created_at is not None

        result = detail_pane._format_resource(sample_project)

        # Should not raise an error
        assert isinstance(result, str)

        # JSON should be valid (datetime converted to string)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_clear_content(self, detail_pane: DetailPane, sample_project: Project) -> None:
        """Test clearing detail pane content."""
        # Set a resource first
        detail_pane.update_content(sample_project)
        assert detail_pane.current_resource is not None

        # Clear it
        detail_pane.clear_content()
        assert detail_pane.current_resource is None

    def test_textarea_config(
        self, detail_pane: DetailPane
    ) -> None:
        """Test that TextArea is configured correctly."""
        # Verify it's a TextArea widget
        from textual.widgets import TextArea
        assert isinstance(detail_pane, TextArea)

        # Verify configuration
        assert detail_pane.language == "json"
        # Theme is not hardcoded anymore - it uses the default/app theme
        assert detail_pane.read_only is True
        assert detail_pane.show_line_numbers is True
        assert detail_pane.soft_wrap is False

    def test_raw_data_preserves_all_api_fields(self) -> None:
        """Test that raw_data preserves all original API response fields."""
        api_data = {
            "name": "projects/test-project",
            "projectId": "test-project",
            "displayName": "Test",
            "lifecycleState": "ACTIVE",
            "custom_field": "custom_value",  # Extra field not in model
            "nested": {"key": "value"},  # Nested data
        }

        project = Project.from_api_response(api_data)

        # raw_data should contain all original fields
        assert project.raw_data == api_data
        assert "custom_field" in project.raw_data
        assert project.raw_data["nested"] == {"key": "value"}
