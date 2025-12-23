"""Google Cloud load balancer service."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.loadbalancer import LoadBalancer
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class LoadBalancerService(BaseService):
    """Service for interacting with Google Cloud load balancers."""

    def __init__(self) -> None:
        """Initialize the LoadBalancer service."""
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

    async def list_load_balancers(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[LoadBalancer]:
        """List all load balancers (forwarding rules) in a project.

        This aggregates both global and regional forwarding rules.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of LoadBalancer instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"loadbalancer:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} load balancers from cache")
                return cast("list[LoadBalancer]", cached)

        async def _list_global_forwarding_rules() -> list[LoadBalancer]:
            """List global forwarding rules."""
            client = await self._get_client()

            try:
                request = client.globalForwardingRules().list(project=project_id)
                response = await asyncio.to_thread(request.execute)

                load_balancers: list[LoadBalancer] = []
                for item in response.get("items", []):
                    lb = LoadBalancer.from_api_response(item)
                    load_balancers.append(lb)

                return load_balancers

            except Exception as e:
                logger.error(f"Failed to list global forwarding rules: {e}")
                return []

        async def _list_regional_forwarding_rules() -> list[LoadBalancer]:
            """List regional forwarding rules across all regions.

            Note: Must fetch regions FULLY SEQUENTIALLY - ANY concurrency causes
            memory corruption in the Google API client. This is slow but necessary.
            """
            client = await self._get_client()

            try:
                # Get list of regions
                regions_request = client.regions().list(project=project_id)
                regions_response = await asyncio.to_thread(regions_request.execute)

                regions = [r.get("name", "") for r in regions_response.get("items", [])]
                all_load_balancers: list[LoadBalancer] = []

                logger.info(f"Fetching load balancers from {len(regions)} regions (this may take a while)...")

                # CRITICAL: Must be fully sequential - ANY parallel access causes crashes
                for region in regions:
                    try:
                        request = client.forwardingRules().list(
                            project=project_id,
                            region=region
                        )
                        response = await asyncio.to_thread(request.execute)

                        for item in response.get("items", []):
                            lb = LoadBalancer.from_api_response(item)
                            all_load_balancers.append(lb)
                    except Exception as e:
                        logger.debug(f"Failed to list forwarding rules in region {region}: {e}")
                        continue

                return all_load_balancers

            except Exception as e:
                logger.error(f"Failed to list regional forwarding rules: {e}")
                return []

        async def _list_all_load_balancers() -> list[LoadBalancer]:
            """Internal function to list all load balancers."""
            logger.info(f"Listing load balancers in project: {project_id}")

            # Run both global and regional queries concurrently
            global_lbs, regional_lbs = await asyncio.gather(
                _list_global_forwarding_rules(),
                _list_regional_forwarding_rules(),
                return_exceptions=True
            )

            # Handle exceptions - need explicit type handling due to return_exceptions=True
            if isinstance(global_lbs, Exception):
                logger.error(f"Error fetching global load balancers: {global_lbs}")
                global_results: list[LoadBalancer] = []
            else:
                global_results = cast("list[LoadBalancer]", global_lbs)

            if isinstance(regional_lbs, Exception):
                logger.error(f"Error fetching regional load balancers: {regional_lbs}")
                regional_results: list[LoadBalancer] = []
            else:
                regional_results = cast("list[LoadBalancer]", regional_lbs)

            all_lbs = global_results + regional_results
            logger.info(f"Found {len(all_lbs)} load balancers ({len(global_results)} global, {len(regional_results)} regional)")
            return all_lbs

        # Execute with retry logic
        load_balancers = await self._execute_with_retry(
            operation=_list_all_load_balancers,
            operation_name=f"list_load_balancers({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            load_balancers,
            ttl=config.cache_ttl_resources,
        )

        return load_balancers


# Singleton instance
_loadbalancer_service: LoadBalancerService | None = None


async def get_loadbalancer_service() -> LoadBalancerService:
    """Get the singleton LoadBalancerService instance.

    Returns:
        LoadBalancerService instance
    """
    global _loadbalancer_service
    if _loadbalancer_service is None:
        _loadbalancer_service = LoadBalancerService()
    return _loadbalancer_service
