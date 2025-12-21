"""Google Cloud Project model."""

from datetime import datetime
from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class Project(BaseModel):
    """Model for a Google Cloud Project.

    Represents a GCP project with metadata from the Resource Manager API.
    """

    project_id: str = Field(..., description="The unique project ID")
    project_number: str | None = Field(None, description="The unique project number")
    display_name: str = Field(..., description="The user-friendly display name")
    state: str = Field(default="ACTIVE", description="Project lifecycle state")
    parent: str | None = Field(None, description="Parent resource (folder or organization)")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Project":
        """Create Project from GCP Resource Manager API response.

        Args:
            data: API response data from projects.get()

        Returns:
            Project instance

        Example API response structure:
            {
                "name": "projects/123456789",
                "projectId": "my-project",
                "projectNumber": "123456789",
                "displayName": "My Project",
                "lifecycleState": "ACTIVE",
                "createTime": "2023-01-01T00:00:00Z",
                "labels": {"env": "prod"},
                "parent": "folders/123456"
            }
        """
        # Extract project_id from name if not present directly
        project_id = data.get("projectId", "")
        if not project_id and "name" in data:
            # name is typically "projects/{project_id}"
            project_id = data["name"].split("/")[-1]

        # Parse create time
        created_at = None
        if "createTime" in data:
            created_at = datetime.fromisoformat(data["createTime"].replace("Z", "+00:00"))

        # Extract parent resource
        parent = None
        if "parent" in data:
            parent_data = data["parent"]
            if isinstance(parent_data, dict):
                # Parent is {"type": "folder", "id": "123"}
                parent = f"{parent_data.get('type', 'unknown')}/{parent_data.get('id', '')}"
            elif isinstance(parent_data, str):
                # Parent is already formatted
                parent = parent_data

        return cls(
            id=project_id,
            name=data.get("displayName", project_id),
            project_id=project_id,
            project_number=str(data.get("projectNumber", "")),
            display_name=data.get("displayName", project_id),
            state=data.get("lifecycleState", "ACTIVE"),
            parent=parent,
            created_at=created_at,
            labels=data.get("labels", {}),
            raw_data=data.copy(),
        )

    def is_active(self) -> bool:
        """Check if project is in active state.

        Returns:
            True if project is active, False otherwise
        """
        return self.state == "ACTIVE"
