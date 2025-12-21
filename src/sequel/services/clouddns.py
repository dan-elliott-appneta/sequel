"""Cloud DNS service for managing DNS zones and records."""

import asyncio
from typing import Any, Optional

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.clouddns import DNSRecord, ManagedZone
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)

# Global service instance
_clouddns_service: Optional["CloudDNSService"] = None


class CloudDNSService(BaseService):
    """Service for interacting with Google Cloud DNS API."""

    def __init__(self) -> None:
        """Initialize CloudDNS service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()
        self._logger = logger

    async def _get_client(self) -> discovery.Resource:
        """Get or create Cloud DNS API client.

        Returns:
            Cloud DNS API client
        """
        if self._client is not None:
            return self._client  # type: ignore[no-any-return]

        auth_manager = await get_auth_manager()
        credentials = auth_manager.credentials

        # Build Cloud DNS API client
        self._client = await asyncio.to_thread(
            discovery.build,
            "dns",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        return self._client  # type: ignore[return-value]

    async def list_zones(
        self, project_id: str, use_cache: bool = True
    ) -> list[ManagedZone]:
        """List all managed zones in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of managed zones
        """
        cache_key = f"zones:{project_id}"

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached  # type: ignore[no-any-return]

        try:
            client = await self._get_client()

            # List managed zones
            request = client.managedZones().list(project=project_id)  # type: ignore[attr-defined]
            response = await asyncio.to_thread(request.execute)

            zones = []
            for zone_data in response.get("managedZones", []):
                zone = ManagedZone.from_api_response(zone_data)
                zones.append(zone)

            if use_cache:
                ttl = get_config().cache_ttl_resources
                await self._cache.set(cache_key, zones, ttl)
            return zones

        except Exception as e:
            self._logger.error(f"Error listing DNS zones for project {project_id}: {e}")
            return []

    async def get_zone(
        self, project_id: str, zone_name: str, use_cache: bool = True
    ) -> ManagedZone | None:
        """Get a specific managed zone.

        Args:
            project_id: GCP project ID
            zone_name: Name of the managed zone
            use_cache: Whether to use cached results

        Returns:
            Managed zone or None if not found
        """
        cache_key = f"zone:{project_id}:{zone_name}"

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached  # type: ignore[no-any-return]

        try:
            client = await self._get_client()

            # Get managed zone
            request = client.managedZones().get(project=project_id, managedZone=zone_name)  # type: ignore[attr-defined]
            response = await asyncio.to_thread(request.execute)

            zone = ManagedZone.from_api_response(response)
            if use_cache:
                ttl = get_config().cache_ttl_resources
                await self._cache.set(cache_key, zone, ttl)
            return zone

        except Exception as e:
            self._logger.error(
                f"Error getting DNS zone {zone_name} in project {project_id}: {e}"
            )
            return None

    async def list_records(
        self, project_id: str, zone_name: str, use_cache: bool = True
    ) -> list[DNSRecord]:
        """List all DNS records in a managed zone.

        Args:
            project_id: GCP project ID
            zone_name: Name of the managed zone
            use_cache: Whether to use cached results

        Returns:
            List of DNS records
        """
        cache_key = f"records:{project_id}:{zone_name}"

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached  # type: ignore[no-any-return]

        try:
            client = await self._get_client()

            # List resource record sets
            request = client.resourceRecordSets().list(  # type: ignore[attr-defined]
                project=project_id, managedZone=zone_name
            )
            response = await asyncio.to_thread(request.execute)

            records = []
            for record_data in response.get("rrsets", []):
                record = DNSRecord.from_api_response(record_data)
                records.append(record)

            if use_cache:
                ttl = get_config().cache_ttl_resources
                await self._cache.set(cache_key, records, ttl)
            return records

        except Exception as e:
            self._logger.error(
                f"Error listing DNS records for zone {zone_name} in project {project_id}: {e}"
            )
            return []

    async def get_record(
        self,
        project_id: str,
        zone_name: str,
        record_name: str,
        record_type: str,
        use_cache: bool = True,
    ) -> DNSRecord | None:
        """Get a specific DNS record.

        Args:
            project_id: GCP project ID
            zone_name: Name of the managed zone
            record_name: Name of the DNS record
            record_type: Type of the DNS record (A, AAAA, CNAME, etc.)
            use_cache: Whether to use cached results

        Returns:
            DNS record or None if not found
        """
        cache_key = f"record:{project_id}:{zone_name}:{record_name}:{record_type}"

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached  # type: ignore[no-any-return]

        # Get all records and filter (Cloud DNS API doesn't support get by name)
        records = await self.list_records(project_id, zone_name, use_cache=use_cache)

        for record in records:
            if record.record_name == record_name and record.record_type == record_type:
                if use_cache:
                    ttl = get_config().cache_ttl_resources
                    await self._cache.set(cache_key, record, ttl)
                return record

        return None


async def get_clouddns_service() -> CloudDNSService:
    """Get or create the global CloudDNS service instance.

    Returns:
        CloudDNS service instance
    """
    global _clouddns_service
    if _clouddns_service is None:
        _clouddns_service = CloudDNSService()
    return _clouddns_service


def reset_clouddns_service() -> None:
    """Reset the global CloudDNS service instance (mainly for testing)."""
    global _clouddns_service
    _clouddns_service = None
