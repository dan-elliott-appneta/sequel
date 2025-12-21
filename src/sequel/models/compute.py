"""Google Compute Engine instance group model."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class InstanceGroup(BaseModel):
    """Model for a Google Compute Engine instance group.

    Represents both managed and unmanaged instance groups.
    """

    group_name: str = Field(..., description="Instance group name")
    zone: str | None = Field(None, description="GCP zone")
    region: str | None = Field(None, description="GCP region")
    size: int = Field(default=0, description="Number of instances in the group")
    instance_template: str | None = Field(None, description="Instance template URL")
    is_managed: bool = Field(default=True, description="Whether this is a managed instance group")
    target_size: int | None = Field(None, description="Target size for managed groups")

    @classmethod
    def from_api_response(cls, data: dict[str, Any], is_managed: bool = True) -> "InstanceGroup":
        """Create InstanceGroup from Compute Engine API response.

        Args:
            data: API response data
            is_managed: Whether this is a managed instance group

        Returns:
            InstanceGroup instance

        Example API response structure (managed):
            {
                "name": "my-instance-group",
                "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
                "targetSize": 3,
                "instanceTemplate": "https://www.googleapis.com/compute/v1/projects/my-project/global/instanceTemplates/my-template",
                "currentActions": {
                    "none": 3
                }
            }
        """
        group_name = data.get("name", "")
        project_id = None

        # Extract zone from URL
        zone = None
        zone_url = data.get("zone", "")
        if zone_url:
            # Zone URL: https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}
            parts = zone_url.split("/")
            if len(parts) >= 2:
                zone = parts[-1]
            if len(parts) >= 4:
                project_id = parts[-3]

        # Extract region from zone (e.g., us-central1 from us-central1-a)
        region = None
        if zone:
            zone_parts = zone.rsplit("-", 1)
            if len(zone_parts) == 2:
                region = zone_parts[0]

        # Extract region from region URL if present
        region_url = data.get("region", "")
        if region_url:
            parts = region_url.split("/")
            if len(parts) >= 2:
                region = parts[-1]
            if len(parts) >= 4 and not project_id:
                project_id = parts[-3]

        # Get size
        size = data.get("targetSize", 0)
        if not size and "size" in data:
            size = data["size"]

        return cls(
            id=group_name,
            name=group_name,
            project_id=project_id,
            created_at=None,  # Compute API doesn't provide creation time in list response
            group_name=group_name,
            zone=zone,
            region=region,
            size=size,
            instance_template=data.get("instanceTemplate"),
            is_managed=is_managed,
            target_size=data.get("targetSize"),
        )
