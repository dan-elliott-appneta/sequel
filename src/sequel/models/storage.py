"""Google Cloud Storage bucket model."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class Bucket(BaseModel):
    """Model for a Google Cloud Storage bucket.

    Represents a Cloud Storage bucket with metadata.
    """

    bucket_name: str = Field(..., description="Bucket name")
    location: str | None = Field(None, description="Bucket location (region or multi-region)")
    storage_class: str | None = Field(None, description="Storage class (STANDARD, NEARLINE, etc.)")
    versioning_enabled: bool = Field(default=False, description="Whether versioning is enabled")
    lifecycle_rules_count: int = Field(default=0, description="Number of lifecycle rules")
    labels_count: int = Field(default=0, description="Number of labels")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Bucket":
        """Create Bucket from Cloud Storage API response.

        Args:
            data: API response data from buckets.get()

        Returns:
            Bucket instance

        Example API response structure:
            {
                "name": "my-bucket",
                "location": "US",
                "storageClass": "STANDARD",
                "timeCreated": "2023-01-01T00:00:00.000Z",
                "updated": "2023-01-02T00:00:00.000Z",
                "projectNumber": "123456789",
                "versioning": {
                    "enabled": true
                },
                "lifecycle": {
                    "rule": [...]
                },
                "labels": {
                    "env": "prod"
                }
            }
        """
        bucket_name = data.get("name", "")

        # Extract project_id from projectNumber if available
        project_id = None
        if "projectNumber" in data:
            # Note: projectNumber is numeric, we might need to map it to project_id
            # For now, we'll store it as string
            project_id = str(data["projectNumber"])

        # Parse versioning
        versioning_enabled = False
        versioning = data.get("versioning", {})
        if isinstance(versioning, dict):
            versioning_enabled = versioning.get("enabled", False)

        # Count lifecycle rules
        lifecycle_rules_count = 0
        lifecycle = data.get("lifecycle", {})
        if isinstance(lifecycle, dict):
            rules = lifecycle.get("rule", [])
            lifecycle_rules_count = len(rules) if isinstance(rules, list) else 0

        # Count labels
        labels_count = 0
        labels = data.get("labels", {})
        if isinstance(labels, dict):
            labels_count = len(labels)

        # Parse creation timestamp
        created_at = None
        if "timeCreated" in data:
            from datetime import datetime
            try:
                # GCS timestamps are in RFC 3339 format
                timestamp = data["timeCreated"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        return cls(
            id=bucket_name,
            name=bucket_name,
            project_id=project_id,
            created_at=created_at,
            bucket_name=bucket_name,
            location=data.get("location"),
            storage_class=data.get("storageClass"),
            versioning_enabled=versioning_enabled,
            lifecycle_rules_count=lifecycle_rules_count,
            labels_count=labels_count,
            raw_data=data.copy(),
        )
