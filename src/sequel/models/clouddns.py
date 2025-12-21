"""Cloud DNS models."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class ManagedZone(BaseModel):
    """Represents a Cloud DNS managed zone."""

    zone_name: str
    dns_name: str
    description: str | None = None
    visibility: str | None = None  # "public" or "private"
    name_servers: list[str] = Field(default_factory=list)
    creation_time: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ManagedZone":
        """Create ManagedZone from Cloud DNS API response.

        Args:
            data: API response data

        Returns:
            ManagedZone instance
        """
        zone_name = data.get("name", "")
        dns_name = data.get("dnsName", "")
        description = data.get("description")
        visibility = data.get("visibility", "public")
        name_servers = data.get("nameServers", [])
        creation_time = data.get("creationTime")

        return cls(
            id=zone_name,
            name=zone_name,
            project_id=None,  # Set by service layer when fetching
            created_at=None,
            zone_name=zone_name,
            dns_name=dns_name,
            description=description,
            visibility=visibility,
            name_servers=name_servers,
            creation_time=creation_time,
            raw_data=data,
        )


class DNSRecord(BaseModel):
    """Represents a DNS record in a managed zone."""

    record_name: str
    record_type: str
    ttl: int = 300
    rrdatas: list[str] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "DNSRecord":
        """Create DNSRecord from Cloud DNS API response.

        Args:
            data: API response data

        Returns:
            DNSRecord instance
        """
        record_name = data.get("name", "")
        record_type = data.get("type", "")
        ttl = data.get("ttl", 300)
        rrdatas = data.get("rrdatas", [])

        # Create a unique ID from name and type
        record_id = f"{record_name}:{record_type}"

        return cls(
            id=record_id,
            name=record_name,
            project_id=None,  # Set by service layer when fetching
            created_at=None,
            record_name=record_name,
            record_type=record_type,
            ttl=ttl,
            rrdatas=rrdatas,
            raw_data=data,
        )

    def get_display_value(self) -> str:
        """Get a display-friendly value for the record.

        Returns:
            Formatted record value
        """
        if not self.rrdatas:
            return ""
        if len(self.rrdatas) == 1:
            return self.rrdatas[0]
        return f"{len(self.rrdatas)} records"
