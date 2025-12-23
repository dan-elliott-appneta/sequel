"""Google Compute Engine firewall policy model."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class FirewallPolicy(BaseModel):
    """Model for a Google Compute Engine firewall policy.

    Represents a network firewall policy with rules.
    """

    policy_name: str = Field(..., description="Firewall policy name")
    description: str | None = Field(None, description="Policy description")
    rule_count: int = Field(default=0, description="Number of firewall rules")
    priority: int | None = Field(None, description="Policy priority")
    direction: str | None = Field(None, description="Traffic direction (INGRESS/EGRESS)")
    disabled: bool = Field(default=False, description="Whether policy is disabled")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "FirewallPolicy":
        """Create FirewallPolicy from Compute Engine API response.

        Args:
            data: API response data from firewalls.get()

        Returns:
            FirewallPolicy instance

        Example API response structure:
            {
                "name": "allow-ssh",
                "description": "Allow SSH from anywhere",
                "network": "projects/my-project/global/networks/default",
                "priority": 1000,
                "direction": "INGRESS",
                "disabled": false,
                "sourceRanges": ["0.0.0.0/0"],
                "allowed": [
                    {"IPProtocol": "tcp", "ports": ["22"]}
                ],
                "creationTimestamp": "2023-01-01T00:00:00.000-00:00"
            }
        """
        policy_name = data.get("name", "")

        # Extract project_id from network or selfLink
        project_id = None
        network = data.get("network", "")
        if "projects/" in network:
            parts = network.split("/")
            if len(parts) >= 2:
                project_id = parts[1]

        # Count rules from allowed/denied lists
        rule_count = 0
        rule_count += len(data.get("allowed", []))
        rule_count += len(data.get("denied", []))

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
            id=policy_name,
            name=policy_name,
            project_id=project_id,
            created_at=created_at,
            policy_name=policy_name,
            description=data.get("description"),
            rule_count=rule_count,
            priority=data.get("priority"),
            direction=data.get("direction"),
            disabled=data.get("disabled", False),
            raw_data=data.copy(),
        )

    def is_enabled(self) -> bool:
        """Check if firewall policy is enabled.

        Returns:
            True if policy is enabled, False otherwise
        """
        return not self.disabled
