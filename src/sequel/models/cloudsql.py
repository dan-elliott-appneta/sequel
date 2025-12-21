"""Google Cloud SQL instance model."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class CloudSQLInstance(BaseModel):
    """Model for a Google Cloud SQL instance.

    Represents a Cloud SQL database instance.
    """

    instance_name: str = Field(..., description="Instance name")
    database_version: str = Field(..., description="Database engine type and version")
    tier: str = Field(..., description="Machine tier (e.g., db-n1-standard-1)")
    state: str = Field(default="RUNNABLE", description="Current instance state")
    region: str | None = Field(None, description="GCP region")
    ip_addresses: list[str] = Field(default_factory=list, description="IP addresses")
    connection_name: str | None = Field(None, description="Connection name for Cloud SQL Proxy")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "CloudSQLInstance":
        """Create CloudSQLInstance from Cloud SQL Admin API response.

        Args:
            data: API response data from instances.get()

        Returns:
            CloudSQLInstance instance

        Example API response structure:
            {
                "name": "my-instance",
                "project": "my-project",
                "databaseVersion": "POSTGRES_14",
                "settings": {
                    "tier": "db-n1-standard-1",
                },
                "state": "RUNNABLE",
                "region": "us-central1",
                "ipAddresses": [
                    {"type": "PRIMARY", "ipAddress": "10.0.0.1"}
                ],
                "connectionName": "my-project:us-central1:my-instance"
            }
        """
        instance_name = data.get("name", "")
        project_id = data.get("project", "")

        # Parse IP addresses
        ip_addresses = []
        for ip_data in data.get("ipAddresses", []):
            if "ipAddress" in ip_data:
                ip_addresses.append(ip_data["ipAddress"])

        # Parse tier from settings
        tier = "unknown"
        if "settings" in data and "tier" in data["settings"]:
            tier = data["settings"]["tier"]

        return cls(
            id=instance_name,
            name=instance_name,
            project_id=project_id,
            created_at=None,  # CloudSQL API doesn't provide creation time in list response
            instance_name=instance_name,
            database_version=data.get("databaseVersion", "UNKNOWN"),
            tier=tier,
            state=data.get("state", "UNKNOWN"),
            region=data.get("region"),
            ip_addresses=ip_addresses,
            connection_name=data.get("connectionName"),
            raw_data=data.copy(),
        )

    def is_running(self) -> bool:
        """Check if instance is in running state.

        Returns:
            True if instance is running, False otherwise
        """
        return self.state == "RUNNABLE"
