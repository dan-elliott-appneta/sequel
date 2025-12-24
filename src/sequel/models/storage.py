"""Google Cloud Storage models."""

import contextlib
from datetime import datetime
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


class StorageObject(BaseModel):
    """Model for a Cloud Storage object.

    Represents an object (file) within a Cloud Storage bucket.
    """

    object_name: str = Field(..., description="Object name (path)")
    bucket_name: str | None = Field(None, description="Parent bucket name")
    size: int | None = Field(None, description="Object size in bytes")
    content_type: str | None = Field(None, description="Content type (MIME type)")
    storage_class: str | None = Field(None, description="Storage class")
    crc32c: str | None = Field(None, description="CRC32C checksum")
    generation: str | None = Field(None, description="Object generation number")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "StorageObject":
        """Create StorageObject from Cloud Storage API response.

        Args:
            data: API response data from objects.list()

        Returns:
            StorageObject instance

        Example API response structure:
            {
                "name": "path/to/file.txt",
                "bucket": "my-bucket",
                "size": "1234",
                "contentType": "text/plain",
                "storageClass": "STANDARD",
                "crc32c": "AAAAAA==",
                "timeCreated": "2023-01-01T00:00:00.000Z",
                "updated": "2023-01-02T00:00:00.000Z",
                "generation": "1672531200000000",
                "metageneration": "1"
            }
        """
        object_name = data.get("name", "")
        bucket_name = data.get("bucket")

        # Parse size (API returns it as string)
        size = None
        if "size" in data:
            with contextlib.suppress(ValueError, TypeError):
                size = int(data["size"])

        # Get content type
        content_type = data.get("contentType")

        # Get storage class
        storage_class = data.get("storageClass")

        # Get CRC32C checksum
        crc32c = data.get("crc32c")

        # Get generation
        generation = data.get("generation")

        # Parse creation timestamp
        created_at = None
        if "timeCreated" in data:
            try:
                # GCS timestamps are in RFC 3339 format
                timestamp = data["timeCreated"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        # Extract project_id from bucket if available
        project_id = None
        # Objects don't typically include project info in their response
        # It will be set by the service layer when fetching

        # Create unique ID from bucket:object
        object_id = f"{bucket_name}:{object_name}" if bucket_name else object_name

        return cls(
            id=object_id,
            name=object_name,
            project_id=project_id,
            created_at=created_at,
            object_name=object_name,
            bucket_name=bucket_name,
            size=size,
            content_type=content_type,
            storage_class=storage_class,
            crc32c=crc32c,
            generation=generation,
            raw_data=data.copy(),
        )

    def get_display_size(self) -> str:
        """Get a human-readable size for the object.

        Returns:
            Formatted size string (e.g., "1.5 KB", "2.3 MB")
        """
        if self.size is None:
            return "Unknown"

        # Convert bytes to human-readable format
        size_bytes = float(self.size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
