"""Unit tests for base model."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from sequel.models.base import BaseModel


class TestBaseModel:
    """Test BaseModel functionality."""

    def test_create_base_model(self) -> None:
        """Test creating a base model instance."""
        model = BaseModel(
            id="test-id",
            name="Test Resource",
            project_id="test-project",
            labels={"env": "test"},
        )

        assert model.id == "test-id"
        assert model.name == "Test Resource"
        assert model.project_id == "test-project"
        assert model.labels == {"env": "test"}
        assert model.created_at is None

    def test_create_with_created_at(self) -> None:
        """Test creating a model with creation timestamp."""
        now = datetime.now(UTC)
        model = BaseModel(
            id="test-id",
            name="Test Resource",
            created_at=now,
        )

        assert model.created_at == now

    def test_default_labels(self) -> None:
        """Test that labels default to empty dict."""
        model = BaseModel(id="test-id", name="Test Resource")
        assert model.labels == {}

    def test_to_dict(self) -> None:
        """Test converting model to dictionary."""
        model = BaseModel(
            id="test-id",
            name="Test Resource",
            project_id="test-project",
            labels={"env": "test"},
        )

        result = model.to_dict()
        assert result["id"] == "test-id"
        assert result["name"] == "Test Resource"
        assert result["project_id"] == "test-project"
        assert result["labels"] == {"env": "test"}

    def test_to_dict_excludes_none(self) -> None:
        """Test that to_dict excludes None values."""
        model = BaseModel(id="test-id", name="Test Resource")
        result = model.to_dict()

        assert "created_at" not in result
        assert "project_id" not in result

    def test_from_api_response(self) -> None:
        """Test creating model from API response."""
        data = {
            "id": "test-id",
            "name": "Test Resource",
            "project_id": "test-project",
            "labels": {"env": "prod"},
        }

        model = BaseModel.from_api_response(data)
        assert model.id == "test-id"
        assert model.name == "Test Resource"
        assert model.project_id == "test-project"
        assert model.labels == {"env": "prod"}

    def test_str_representation(self) -> None:
        """Test string representation of model."""
        model = BaseModel(id="test-id", name="Test Resource")
        result = str(model)

        assert "BaseModel" in result
        assert "test-id" in result
        assert "Test Resource" in result

    def test_repr_representation(self) -> None:
        """Test detailed string representation."""
        model = BaseModel(id="test-id", name="Test Resource")
        result = repr(model)

        assert "BaseModel" in result
        assert "test-id" in result
        assert "Test Resource" in result

    def test_validation(self) -> None:
        """Test that Pydantic validation is enabled."""
        with pytest.raises(ValidationError):
            BaseModel(name="Test Resource")  # Missing required 'id'

    def test_extra_fields_allowed(self) -> None:
        """Test that extra fields are allowed."""
        model = BaseModel(
            id="test-id",
            name="Test Resource",
            custom_field="custom_value",  # type: ignore[call-arg]
        )

        assert model.id == "test-id"
        # Extra fields are stored but not in standard attributes
        result = model.to_dict()
        assert "custom_field" in result
