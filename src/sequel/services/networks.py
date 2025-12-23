"""VPC Networks service for managing networks and subnets."""

import asyncio
from typing import Any

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.networks import Subnet, VPCNetwork
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class NetworksService(BaseService):
    """Service for interacting with Google Compute Engine Networks API."""

    def __init__(self) -> None:
        """Initialize Networks service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> discovery.Resource:
        """Get or create Compute API client.

        Returns:
            Compute API client
        """
        if self._client is not None:
            return self._client  # type: ignore[no-any-return]

        auth_manager = await get_auth_manager()
        credentials = auth_manager.credentials

        # Build Compute API client
        self._client = await asyncio.to_thread(
            discovery.build,
            "compute",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        return self._client  # type: ignore[return-value]

    async def list_networks(
        self, project_id: str, use_cache: bool = True
    ) -> list[VPCNetwork]:
        """List all VPC networks in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of VPC networks
        """
        cache_key = f"networks:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} VPC networks from cache")
                return cached  # type: ignore[no-any-return]

        async def _list_networks() -> list[VPCNetwork]:
            """Internal function to list VPC networks."""
            logger.info(f"Listing VPC networks in project: {project_id}")

            try:
                client = await self._get_client()

                # List networks (global resource, no region needed)
                request = client.networks().list(project=project_id)  # type: ignore[attr-defined]
                response = await asyncio.to_thread(request.execute)

                networks: list[VPCNetwork] = []
                for item in response.get("items", []):
                    network = VPCNetwork.from_api_response(item)
                    # Set project_id if not already set
                    if network.project_id is None:
                        network.project_id = project_id
                    networks.append(network)
                    logger.debug(f"Loaded VPC network: {network.network_name}")

                logger.info(f"Found {len(networks)} VPC networks")
                return networks

            except Exception as e:
                logger.error(f"Failed to list VPC networks: {e}", exc_info=True)
                return []

        # Execute with retry logic
        networks = await self._execute_with_retry(
            operation=_list_networks,
            operation_name=f"list_networks({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            networks,
            ttl=config.cache_ttl_resources,
        )

        return networks

    async def list_subnets(
        self, project_id: str, network_name: str | None = None, use_cache: bool = True
    ) -> list[Subnet]:
        """List all subnets in a project, optionally filtered by network.

        Uses aggregatedList to get subnets across all regions in one call.

        Args:
            project_id: GCP project ID
            network_name: Optional network name to filter by
            use_cache: Whether to use cached results

        Returns:
            List of subnets
        """
        # Different cache keys for all subnets vs filtered by network
        cache_key = (
            f"subnets:{project_id}"
            if network_name is None
            else f"subnets:{project_id}:{network_name}"
        )

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} subnets from cache")
                return cached  # type: ignore[no-any-return]

        async def _list_subnets() -> list[Subnet]:
            """Internal function to list subnets."""
            logger.info(
                f"Listing subnets in project: {project_id}"
                + (f" for network: {network_name}" if network_name else "")
            )

            try:
                client = await self._get_client()

                # Use aggregatedList to get subnets across all regions
                request = client.subnetworks().aggregatedList(project=project_id)  # type: ignore[attr-defined]
                response = await asyncio.to_thread(request.execute)

                subnets: list[Subnet] = []

                # Parse aggregated response
                # Response format: {"items": {"regions/us-central1": {"subnetworks": [...]}}}
                items = response.get("items", {})
                for region_data in items.values():
                    if "subnetworks" in region_data:
                        for subnet_data in region_data["subnetworks"]:
                            subnet = Subnet.from_api_response(subnet_data)
                            # Set project_id if not already set
                            if subnet.project_id is None:
                                subnet.project_id = project_id

                            # Filter by network if specified
                            if network_name is None or subnet.network_name == network_name:
                                subnets.append(subnet)
                                logger.debug(
                                    f"Loaded subnet: {subnet.subnet_name} "
                                    f"(network: {subnet.network_name}, region: {subnet.region})"
                                )

                logger.info(f"Found {len(subnets)} subnets")
                return subnets

            except Exception as e:
                logger.error(f"Failed to list subnets: {e}", exc_info=True)
                return []

        # Execute with retry logic
        subnets = await self._execute_with_retry(
            operation=_list_subnets,
            operation_name=f"list_subnets({project_id}, {network_name})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            subnets,
            ttl=config.cache_ttl_resources,
        )

        return subnets


# Singleton instance
_networks_service: NetworksService | None = None


async def get_networks_service() -> NetworksService:
    """Get the singleton NetworksService instance.

    Returns:
        NetworksService instance
    """
    global _networks_service
    if _networks_service is None:
        _networks_service = NetworksService()
    return _networks_service
