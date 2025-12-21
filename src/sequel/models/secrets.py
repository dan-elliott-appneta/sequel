"""Google Secret Manager secret model."""

from datetime import datetime
from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class Secret(BaseModel):
    """Model for a Google Secret Manager secret.

    Note: This represents metadata only. Secret values are never retrieved.
    """

    secret_name: str = Field(..., description="Secret name")
    replication_policy: str | None = Field(None, description="Replication policy")
    version_count: int = Field(default=0, description="Number of secret versions")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Secret":
        """Create Secret from Secret Manager API response.

        Args:
            data: API response data from secrets.get()

        Returns:
            Secret instance

        Example API response structure:
            {
                "name": "projects/123456/secrets/my-secret",
                "replication": {
                    "automatic": {}
                },
                "createTime": "2023-01-01T00:00:00Z",
                "labels": {"env": "prod"}
            }
        """
        # Extract secret name from full path
        secret_name = data.get("name", "")
        if "/" in secret_name:
            secret_name = secret_name.split("/")[-1]

        # Extract project_id from name
        project_id = None
        name = data.get("name", "")
        if "projects/" in name:
            parts = name.split("/")
            if len(parts) >= 2:
                project_id = parts[1]

        # Parse replication policy
        replication_policy = "unknown"
        if "replication" in data:
            replication = data["replication"]
            if "automatic" in replication:
                replication_policy = "automatic"
            elif "userManaged" in replication:
                replication_policy = "user-managed"

        # Parse create time
        created_at = None
        if "createTime" in data:
            created_at = datetime.fromisoformat(data["createTime"].replace("Z", "+00:00"))

        return cls(
            id=secret_name,
            name=secret_name,
            project_id=project_id,
            secret_name=secret_name,
            replication_policy=replication_policy,
            created_at=created_at,
            labels=data.get("labels", {}),
            raw_data=data.copy(),
        )
