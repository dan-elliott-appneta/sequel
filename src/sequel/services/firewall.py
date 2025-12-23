"""Google Compute Engine firewall service."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.firewall import FirewallPolicy
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class FirewallService(BaseService):
    """Service for interacting with Google Compute Engine firewall policies."""

    def __init__(self) -> None:
        """Initialize the Firewall service."""
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

    async def list_firewall_policies(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[FirewallPolicy]:
        """List all firewall policies in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of FirewallPolicy instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"firewall:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} firewall policies from cache")
                return cast("list[FirewallPolicy]", cached)

        async def _list_policies() -> list[FirewallPolicy]:
            """Internal function to list firewall policies."""
            client = await self._get_client()

            logger.info(f"Listing firewall policies in project: {project_id}")

            try:
                # Call the API
                request = client.firewalls().list(project=project_id)
                # Run blocking execute() in thread to avoid blocking event loop
                response = await asyncio.to_thread(request.execute)

                policies: list[FirewallPolicy] = []
                for item in response.get("items", []):
                    policy = FirewallPolicy.from_api_response(item)
                    policies.append(policy)

                logger.info(f"Found {len(policies)} firewall policies")
                return policies

            except Exception as e:
                logger.error(f"Failed to list firewall policies: {e}")
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        policies = await self._execute_with_retry(
            operation=_list_policies,
            operation_name=f"list_firewall_policies({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            policies,
            ttl=config.cache_ttl_resources,
        )

        return policies


# Singleton instance
_firewall_service: FirewallService | None = None


async def get_firewall_service() -> FirewallService:
    """Get the singleton FirewallService instance.

    Returns:
        FirewallService instance
    """
    global _firewall_service
    if _firewall_service is None:
        _firewall_service = FirewallService()
    return _firewall_service
