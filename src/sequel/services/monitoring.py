"""Google Cloud Monitoring service."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.monitoring import AlertPolicy
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class MonitoringService(BaseService):
    """Service for interacting with Google Cloud Monitoring API."""

    def __init__(self) -> None:
        """Initialize the Monitoring service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> Any:
        """Get or create the Cloud Monitoring API client.

        Returns:
            Initialized monitoring client
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = discovery.build(
                "monitoring",
                "v3",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )
        return self._client

    async def list_alert_policies(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[AlertPolicy]:
        """List all alert policies in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of AlertPolicy instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"monitoring:alert_policies:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} alert policies from cache")
                return cast("list[AlertPolicy]", cached)

        async def _list_policies() -> list[AlertPolicy]:
            """Internal function to list alert policies."""
            client = await self._get_client()

            logger.info(f"Listing alert policies in project: {project_id}")

            try:
                # The Cloud Monitoring API requires the parent in the format:
                # projects/[PROJECT_ID]
                parent = f"projects/{project_id}"

                # Call the API
                request = client.projects().alertPolicies().list(name=parent)
                # Run blocking execute() in thread to avoid blocking event loop
                response = await asyncio.to_thread(request.execute)

                policies: list[AlertPolicy] = []
                for item in response.get("alertPolicies", []):
                    policy = AlertPolicy.from_api_response(item)
                    policies.append(policy)

                logger.info(f"Found {len(policies)} alert policies")
                return policies

            except Exception as e:
                logger.error(f"Failed to list alert policies: {e}")
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        policies = await self._execute_with_retry(
            operation=_list_policies,
            operation_name=f"list_alert_policies({project_id})",
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
_monitoring_service: MonitoringService | None = None


async def get_monitoring_service() -> MonitoringService:
    """Get the singleton MonitoringService instance.

    Returns:
        MonitoringService instance
    """
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
