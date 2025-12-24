"""Google Cloud SQL service using Cloud SQL Admin API."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.cloudsql import CloudSQLInstance
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class CloudSQLService(BaseService):
    """Service for interacting with Google Cloud SQL instances."""

    def __init__(self) -> None:
        """Initialize the CloudSQL service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> Any:
        """Get or create the Cloud SQL Admin API client.

        Returns:
            Initialized sqladmin client
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = discovery.build(
                "sqladmin",
                "v1",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )
        return self._client

    async def list_instances(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[CloudSQLInstance]:
        """List all Cloud SQL instances in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of CloudSQLInstance instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"cloudsql:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} Cloud SQL instances from cache")
                return cast("list[CloudSQLInstance]", cached)

        async def _list_instances() -> list[CloudSQLInstance]:
            """Internal function to list instances."""
            client = await self._get_client()

            logger.info(f"Listing Cloud SQL instances in project: {project_id}")

            try:
                # Call the API
                request = client.instances().list(project=project_id)
                # Run blocking execute() in thread to avoid blocking event loop
                response = await asyncio.to_thread(request.execute)

                instances: list[CloudSQLInstance] = []
                for item in response.get("items", []):
                    instance = CloudSQLInstance.from_api_response(item)
                    instances.append(instance)

                logger.info(f"Found {len(instances)} Cloud SQL instances")
                return instances

            except Exception as e:
                logger.error(f"Failed to list Cloud SQL instances: {e}")
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        instances = await self._execute_with_retry(
            operation=_list_instances,
            operation_name=f"list_cloudsql_instances({project_id})",
        )

        # Cache the results
        if use_cache:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, instances, ttl)

        return instances

    async def get_instance(
        self,
        project_id: str,
        instance_name: str,
        use_cache: bool = True,
    ) -> CloudSQLInstance | None:
        """Get a specific Cloud SQL instance.

        Args:
            project_id: GCP project ID
            instance_name: Instance name
            use_cache: Whether to use cached results

        Returns:
            CloudSQLInstance or None if not found

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"cloudsql:{project_id}:{instance_name}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning Cloud SQL instance {instance_name} from cache")
                return cast("CloudSQLInstance", cached)

        async def _get_instance() -> CloudSQLInstance | None:
            """Internal function to get instance."""
            client = await self._get_client()

            logger.info(f"Getting Cloud SQL instance: {project_id}/{instance_name}")

            try:
                request = client.instances().get(
                    project=project_id,
                    instance=instance_name,
                )
                response = await asyncio.to_thread(request.execute)

                instance = CloudSQLInstance.from_api_response(response)
                logger.info(f"Retrieved Cloud SQL instance: {instance_name}")
                return instance

            except Exception as e:
                logger.error(f"Failed to get Cloud SQL instance {instance_name}: {e}")
                return None

        # Execute with retry logic
        instance = await self._execute_with_retry(
            operation=_get_instance,
            operation_name=f"get_cloudsql_instance({project_id}, {instance_name})",
        )

        # Cache the result
        if use_cache and instance is not None:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, instance, ttl)

        return instance


# Global service instance
_cloudsql_service: CloudSQLService | None = None


async def get_cloudsql_service() -> CloudSQLService:
    """Get the global CloudSQL service instance.

    Returns:
        Initialized CloudSQLService
    """
    global _cloudsql_service
    if _cloudsql_service is None:
        _cloudsql_service = CloudSQLService()
    return _cloudsql_service


def reset_cloudsql_service() -> None:
    """Reset the global CloudSQL service (mainly for testing)."""
    global _cloudsql_service
    _cloudsql_service = None
