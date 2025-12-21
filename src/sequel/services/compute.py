"""Google Compute Engine service using Compute Engine API."""

import asyncio
from typing import Any

from googleapiclient import discovery  # type: ignore[import-untyped]

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.compute import InstanceGroup
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class ComputeService(BaseService):
    """Service for interacting with Google Compute Engine resources."""

    def __init__(self) -> None:
        """Initialize the Compute service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> Any:
        """Get or create the Compute Engine API client.

        Returns:
            Initialized compute client
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = discovery.build(
                "compute",
                "v1",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )
        return self._client

    async def list_instance_groups(
        self,
        project_id: str,
        zone: str | None = None,
        use_cache: bool = True,
    ) -> list[InstanceGroup]:
        """List instance groups in a project.

        Args:
            project_id: GCP project ID
            zone: Optional specific zone to list from
            use_cache: Whether to use cached results

        Returns:
            List of InstanceGroup instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"instance_groups:{project_id}:{zone or 'all'}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} instance groups from cache")
                return cached

        async def _list_instance_groups() -> list[InstanceGroup]:
            """Internal function to list instance groups."""
            client = await self._get_client()

            logger.info(f"Listing instance groups in project: {project_id}")

            groups: list[InstanceGroup] = []

            try:
                if zone:
                    # List groups in specific zone
                    groups.extend(await self._list_zone_instance_groups(client, project_id, zone))
                else:
                    # Use aggregated list to get all instance groups across all zones efficiently
                    groups.extend(await self._list_all_instance_groups_aggregated(client, project_id))

                logger.info(f"Found {len(groups)} instance groups")
                return groups

            except Exception as e:
                logger.error(f"Failed to list instance groups: {e}")
                return []

        # Execute with retry logic
        groups = await self._execute_with_retry(
            operation=_list_instance_groups,
            operation_name=f"list_instance_groups({project_id})",
        )

        # Cache the results
        if use_cache:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, groups, ttl)

        return groups

    async def _list_all_instance_groups_aggregated(
        self,
        client: Any,
        project_id: str,
    ) -> list[InstanceGroup]:
        """List all instance groups across all zones using aggregated list API.

        This is much more efficient than listing each zone individually.

        Args:
            client: Compute API client
            project_id: GCP project ID

        Returns:
            List of InstanceGroup instances
        """
        groups: list[InstanceGroup] = []

        try:
            # List managed instance groups across all zones
            request = client.instanceGroupManagers().aggregatedList(project=project_id)  # type: ignore[no-untyped-call]
            response = await asyncio.to_thread(request.execute)  # type: ignore[no-untyped-call]

            for _zone_name, zone_data in response.get("items", {}).items():
                for item in zone_data.get("instanceGroupManagers", []):
                    group = InstanceGroup.from_api_response(item, is_managed=True)
                    groups.append(group)

        except Exception as e:
            logger.debug(f"Error listing managed instance groups: {e}")

        try:
            # List unmanaged instance groups across all zones
            request = client.instanceGroups().aggregatedList(project=project_id)  # type: ignore[no-untyped-call]
            response = await asyncio.to_thread(request.execute)  # type: ignore[no-untyped-call]

            for _zone_name, zone_data in response.get("items", {}).items():
                for item in zone_data.get("instanceGroups", []):
                    # Skip if already added as managed group
                    if not any(g.group_name == item.get("name") for g in groups):
                        group = InstanceGroup.from_api_response(item, is_managed=False)
                        groups.append(group)

        except Exception as e:
            logger.debug(f"Error listing unmanaged instance groups: {e}")

        return groups

    async def _list_zones(self, client: Any, project_id: str) -> list[str]:
        """List all available zones in a project.

        Args:
            client: Compute API client
            project_id: GCP project ID

        Returns:
            List of zone names
        """
        try:
            request = client.zones().list(project=project_id)  # type: ignore[no-untyped-call]
            # Run blocking execute() in thread to avoid blocking event loop
            response = await asyncio.to_thread(request.execute)  # type: ignore[no-untyped-call]

            zones = []
            for item in response.get("items", []):
                zones.append(item["name"])

            return zones

        except Exception as e:
            logger.error(f"Failed to list zones: {e}")
            return []

    async def _list_zone_instance_groups(
        self,
        client: Any,
        project_id: str,
        zone: str,
    ) -> list[InstanceGroup]:
        """List instance groups in a specific zone.

        Args:
            client: Compute API client
            project_id: GCP project ID
            zone: Zone name

        Returns:
            List of InstanceGroup instances
        """
        groups: list[InstanceGroup] = []

        try:
            # List managed instance groups
            request = client.instanceGroupManagers().list(  # type: ignore[no-untyped-call]
                project=project_id,
                zone=zone,
            )
            # Run blocking execute() in thread to avoid blocking event loop
            response = await asyncio.to_thread(request.execute)  # type: ignore[no-untyped-call]

            for item in response.get("items", []):
                group = InstanceGroup.from_api_response(item, is_managed=True)
                groups.append(group)

        except Exception as e:
            logger.debug(f"No managed instance groups in zone {zone}: {e}")

        try:
            # List unmanaged instance groups
            request = client.instanceGroups().list(  # type: ignore[no-untyped-call]
                project=project_id,
                zone=zone,
            )
            # Run blocking execute() in thread to avoid blocking event loop
            response = await asyncio.to_thread(request.execute)  # type: ignore[no-untyped-call]

            for item in response.get("items", []):
                # Skip if already added as managed group
                if not any(g.group_name == item.get("name") for g in groups):
                    group = InstanceGroup.from_api_response(item, is_managed=False)
                    groups.append(group)

        except Exception as e:
            logger.debug(f"No unmanaged instance groups in zone {zone}: {e}")

        return groups


# Global service instance
_compute_service: ComputeService | None = None


async def get_compute_service() -> ComputeService:
    """Get the global Compute service instance.

    Returns:
        Initialized ComputeService
    """
    global _compute_service
    if _compute_service is None:
        _compute_service = ComputeService()
    return _compute_service


def reset_compute_service() -> None:
    """Reset the global Compute service (mainly for testing)."""
    global _compute_service
    _compute_service = None
