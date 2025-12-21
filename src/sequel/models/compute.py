"""Google Compute Engine models."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class ComputeInstance(BaseModel):
    """Model for a Google Compute Engine VM instance."""

    instance_name: str = Field(..., description="Instance name")
    instance_id: str | None = Field(None, description="Instance ID")
    zone: str | None = Field(None, description="GCP zone")
    machine_type: str | None = Field(None, description="Machine type")
    status: str | None = Field(None, description="Instance status (RUNNING, TERMINATED, etc.)")
    internal_ip: str | None = Field(None, description="Internal IP address")
    external_ip: str | None = Field(None, description="External IP address")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ComputeInstance":
        """Create ComputeInstance from Compute Engine API response.

        Args:
            data: API response data

        Returns:
            ComputeInstance instance
        """
        instance_name = data.get("name", "")
        instance_id = data.get("id")

        # Extract zone from URL
        zone = None
        zone_url = data.get("zone", "")
        if zone_url:
            parts = zone_url.split("/")
            if len(parts) >= 2:
                zone = parts[-1]

        # Extract machine type
        machine_type = None
        machine_type_url = data.get("machineType", "")
        if machine_type_url:
            parts = machine_type_url.split("/")
            if len(parts) >= 2:
                machine_type = parts[-1]

        # Get status
        status = data.get("status")

        # Extract IPs
        internal_ip = None
        external_ip = None
        network_interfaces = data.get("networkInterfaces", [])
        if network_interfaces:
            first_interface = network_interfaces[0]
            internal_ip = first_interface.get("networkIP")
            access_configs = first_interface.get("accessConfigs", [])
            if access_configs:
                external_ip = access_configs[0].get("natIP")

        return cls(
            id=instance_name,
            name=instance_name,
            project_id=None,
            created_at=data.get("creationTimestamp"),
            instance_name=instance_name,
            instance_id=str(instance_id) if instance_id else None,
            zone=zone,
            machine_type=machine_type,
            status=status,
            internal_ip=internal_ip,
            external_ip=external_ip,
            raw_data=data.copy(),
        )

    def is_running(self) -> bool:
        """Check if the instance is in RUNNING state."""
        return self.status == "RUNNING"


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
            raw_data=data.copy(),
        )
