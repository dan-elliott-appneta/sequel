"""Base model for all Google Cloud resources."""

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    """Base model for Google Cloud resources.

    All resource models inherit from this base class and provide:
    - Standard fields common to most GCP resources
    - Serialization/deserialization methods
    - Type-safe data validation via Pydantic
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=False,
        validate_assignment=True,
        extra="allow",
    )

    id: str = Field(..., description="Unique identifier for the resource")
    name: str = Field(..., description="Display name of the resource")
    project_id: str | None = Field(None, description="GCP project ID containing this resource")
    created_at: datetime | None = Field(None, description="Resource creation timestamp")
    labels: dict[str, str] = Field(default_factory=dict, description="Resource labels")
    raw_data: dict[str, Any] = Field(
        default_factory=dict, description="Raw API response data for this resource"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of the model
        """
        return self.model_dump(mode="python", exclude_none=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "BaseModel":
        """Create model instance from GCP API response.

        Args:
            data: Raw API response data

        Returns:
            Model instance populated from API data
        """
        # Store raw data for later use (e.g., JSON display in UI)
        # Subclasses should call this or manually set raw_data
        if "raw_data" not in data:
            data = {**data, "raw_data": data.copy()}

        # Default implementation - subclasses should override for custom mapping
        return cls(**data)

    def __str__(self) -> str:
        """String representation of the model."""
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self) -> str:
        """Detailed string representation of the model."""
        return f"{self.__class__.__name__}({self.to_dict()})"
