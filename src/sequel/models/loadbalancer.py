"""Google Cloud load balancer model."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class LoadBalancer(BaseModel):
    """Model for a Google Cloud load balancer.

    Represents a load balancer (forwarding rule and target).
    """

    lb_name: str = Field(..., description="Load balancer name")
    description: str | None = Field(None, description="Load balancer description")
    ip_address: str | None = Field(None, description="Load balancer IP address")
    port_range: str | None = Field(None, description="Port or port range")
    protocol: str | None = Field(None, description="IP protocol (TCP/UDP/etc)")
    load_balancing_scheme: str | None = Field(None, description="Load balancing scheme")
    region: str | None = Field(None, description="Region (for regional LB)")
    network_tier: str | None = Field(None, description="Network tier (PREMIUM/STANDARD)")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "LoadBalancer":
        """Create LoadBalancer from Compute Engine API response.

        Args:
            data: API response data from forwardingRules.get()

        Returns:
            LoadBalancer instance

        Example API response structure:
            {
                "name": "my-lb",
                "description": "Production load balancer",
                "IPAddress": "34.120.1.1",
                "IPProtocol": "TCP",
                "portRange": "80-80",
                "target": "projects/my-project/regions/us-central1/targetPools/my-pool",
                "loadBalancingScheme": "EXTERNAL",
                "networkTier": "PREMIUM",
                "region": "us-central1",
                "creationTimestamp": "2023-01-01T00:00:00.000-00:00"
            }
        """
        lb_name = data.get("name", "")

        # Extract project_id from target or selfLink
        project_id = None
        target = data.get("target", "") or data.get("selfLink", "")
        if "projects/" in target:
            parts = target.split("/")
            if len(parts) >= 2:
                project_id = parts[1]

        # Extract region from region field or URL
        region = data.get("region")
        if region and "/" in region:
            region = region.split("/")[-1]

        # Parse creation timestamp
        created_at = None
        if "creationTimestamp" in data:
            from datetime import datetime
            try:
                # Remove milliseconds and timezone for parsing
                timestamp = data["creationTimestamp"].split(".")[0]
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, IndexError):
                pass

        return cls(
            id=lb_name,
            name=lb_name,
            project_id=project_id,
            created_at=created_at,
            lb_name=lb_name,
            description=data.get("description"),
            ip_address=data.get("IPAddress"),
            port_range=data.get("portRange"),
            protocol=data.get("IPProtocol"),
            load_balancing_scheme=data.get("loadBalancingScheme"),
            region=region,
            network_tier=data.get("networkTier"),
            raw_data=data.copy(),
        )

    def is_external(self) -> bool:
        """Check if load balancer is external-facing.

        Returns:
            True if external, False otherwise
        """
        return self.load_balancing_scheme == "EXTERNAL"
