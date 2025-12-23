"""VPC Networks and Subnets models."""

from datetime import datetime
from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class VPCNetwork(BaseModel):
    """Model for a VPC Network.

    Represents a Google Cloud VPC network with metadata.
    """

    network_name: str = Field(..., description="Network name")
    mode: str | None = Field(None, description="Network mode (AUTO or CUSTOM)")
    subnet_count: int = Field(default=0, description="Number of subnets")
    mtu: int = Field(default=1460, description="Maximum Transmission Unit")
    auto_create_subnets: bool = Field(
        default=False, description="Whether subnets are auto-created"
    )
    routing_mode: str | None = Field(None, description="Routing mode (REGIONAL or GLOBAL)")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "VPCNetwork":
        """Create VPCNetwork from Compute API response.

        Args:
            data: API response data from networks.list()

        Returns:
            VPCNetwork instance

        Example API response structure:
            {
                "name": "default",
                "id": "1234567890",
                "creationTimestamp": "2023-01-01T00:00:00.000-08:00",
                "autoCreateSubnetworks": false,
                "subnetworks": [
                    "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1/subnetworks/default"
                ],
                "routingConfig": {
                    "routingMode": "REGIONAL"
                },
                "mtu": 1460,
                "selfLink": "https://www.googleapis.com/compute/v1/projects/my-project/global/networks/default"
            }
        """
        # Extract network name
        network_name = data.get("name", "")

        # Extract project_id from selfLink if available
        project_id = None
        self_link = data.get("selfLink", "")
        if "/projects/" in self_link:
            parts = self_link.split("/")
            try:
                project_idx = parts.index("projects")
                project_id = parts[project_idx + 1]
            except (ValueError, IndexError):
                pass

        # Determine mode from autoCreateSubnetworks
        auto_create = data.get("autoCreateSubnetworks", False)
        mode = "AUTO" if auto_create else "CUSTOM"

        # Count subnets
        subnetworks = data.get("subnetworks", [])
        subnet_count = len(subnetworks) if isinstance(subnetworks, list) else 0

        # Get MTU
        mtu = data.get("mtu", 1460)

        # Get routing mode
        routing_config = data.get("routingConfig", {})
        routing_mode = None
        if isinstance(routing_config, dict):
            routing_mode = routing_config.get("routingMode")

        # Parse creation timestamp
        created_at = None
        if "creationTimestamp" in data:
            try:
                timestamp = data["creationTimestamp"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        return cls(
            id=network_name,
            name=network_name,
            project_id=project_id,
            created_at=created_at,
            network_name=network_name,
            mode=mode,
            subnet_count=subnet_count,
            mtu=mtu,
            auto_create_subnets=auto_create,
            routing_mode=routing_mode,
            raw_data=data.copy(),
        )


class Subnet(BaseModel):
    """Model for a VPC Subnet.

    Represents a subnet within a VPC network.
    """

    subnet_name: str = Field(..., description="Subnet name")
    network_name: str | None = Field(None, description="Parent network name")
    region: str | None = Field(None, description="Subnet region")
    ip_cidr_range: str | None = Field(None, description="Primary IP CIDR range")
    gateway_address: str | None = Field(None, description="Gateway IP address")
    private_ip_google_access: bool = Field(
        default=False, description="Private Google Access enabled"
    )
    enable_flow_logs: bool = Field(default=False, description="Flow logs enabled")
    purpose: str | None = Field(None, description="Subnet purpose")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Subnet":
        """Create Subnet from Compute API response.

        Args:
            data: API response data from subnetworks.aggregatedList()

        Returns:
            Subnet instance

        Example API response structure:
            {
                "name": "default",
                "id": "1234567890",
                "creationTimestamp": "2023-01-01T00:00:00.000-08:00",
                "network": "https://www.googleapis.com/compute/v1/projects/my-project/global/networks/default",
                "ipCidrRange": "10.128.0.0/20",
                "gatewayAddress": "10.128.0.1",
                "region": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1",
                "privateIpGoogleAccess": false,
                "enableFlowLogs": false,
                "purpose": "PRIVATE",
                "selfLink": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1/subnetworks/default"
            }
        """
        # Extract subnet name
        subnet_name = data.get("name", "")

        # Extract project_id from selfLink if available
        project_id = None
        self_link = data.get("selfLink", "")
        if "/projects/" in self_link:
            parts = self_link.split("/")
            try:
                project_idx = parts.index("projects")
                project_id = parts[project_idx + 1]
            except (ValueError, IndexError):
                pass

        # Extract network name from network URL
        network_name = None
        network_url = data.get("network", "")
        if "/networks/" in network_url:
            network_name = network_url.split("/")[-1]

        # Extract region from region URL
        region = None
        region_url = data.get("region", "")
        if "/regions/" in region_url:
            region = region_url.split("/")[-1]

        # Get IP CIDR range
        ip_cidr_range = data.get("ipCidrRange")

        # Get gateway address
        gateway_address = data.get("gatewayAddress")

        # Get private Google access
        private_ip_google_access = data.get("privateIpGoogleAccess", False)

        # Get flow logs setting
        enable_flow_logs = data.get("enableFlowLogs", False)

        # Get purpose
        purpose = data.get("purpose")

        # Parse creation timestamp
        created_at = None
        if "creationTimestamp" in data:
            try:
                timestamp = data["creationTimestamp"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        # Create unique ID from region and name
        subnet_id = f"{region}:{subnet_name}" if region else subnet_name

        return cls(
            id=subnet_id,
            name=subnet_name,
            project_id=project_id,
            created_at=created_at,
            subnet_name=subnet_name,
            network_name=network_name,
            region=region,
            ip_cidr_range=ip_cidr_range,
            gateway_address=gateway_address,
            private_ip_google_access=private_ip_google_access,
            enable_flow_logs=enable_flow_logs,
            purpose=purpose,
            raw_data=data.copy(),
        )
