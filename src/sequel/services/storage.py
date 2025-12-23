"""Google Cloud Storage service."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.storage import Bucket, StorageObject
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService(BaseService):
    """Service for interacting with Google Cloud Storage buckets."""

    def __init__(self) -> None:
        """Initialize the Storage service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> Any:
        """Get or create the Cloud Storage API client.

        Returns:
            Initialized storage client
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = discovery.build(
                "storage",
                "v1",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )
        return self._client

    async def list_buckets(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[Bucket]:
        """List all Cloud Storage buckets in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of Bucket instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"storage:buckets:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} buckets from cache")
                return cast("list[Bucket]", cached)

        async def _list_buckets() -> list[Bucket]:
            """Internal function to list buckets."""
            client = await self._get_client()

            logger.info(f"Listing Cloud Storage buckets in project: {project_id}")

            try:
                # Call the API
                request = client.buckets().list(project=project_id)
                # Run blocking execute() in thread to avoid blocking event loop
                response = await asyncio.to_thread(request.execute)

                buckets: list[Bucket] = []
                for item in response.get("items", []):
                    bucket = Bucket.from_api_response(item)
                    buckets.append(bucket)

                logger.info(f"Found {len(buckets)} buckets")
                return buckets

            except Exception as e:
                logger.error(f"Failed to list buckets: {e}")
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        buckets = await self._execute_with_retry(
            operation=_list_buckets,
            operation_name=f"list_buckets({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            buckets,
            ttl=config.cache_ttl_resources,
        )

        return buckets

    async def list_objects(
        self,
        project_id: str,
        bucket_name: str,
        use_cache: bool = True,
        max_results: int = 100,
    ) -> list[StorageObject]:
        """List objects in a Cloud Storage bucket.

        Args:
            project_id: GCP project ID
            bucket_name: Name of the bucket
            use_cache: Whether to use cached results
            max_results: Maximum number of objects to return (default: 100)

        Returns:
            List of StorageObject instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"storage:objects:{project_id}:{bucket_name}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(
                    f"Returning {len(cached)} objects from cache for bucket: {bucket_name}"
                )
                return cast("list[StorageObject]", cached)

        async def _list_objects() -> list[StorageObject]:
            """Internal function to list objects."""
            client = await self._get_client()

            logger.info(f"Listing objects in bucket: {bucket_name} (max: {max_results})")

            try:
                # Call the API with pagination limit
                request = client.objects().list(
                    bucket=bucket_name,
                    maxResults=max_results,
                )
                # Run blocking execute() in thread to avoid blocking event loop
                response = await asyncio.to_thread(request.execute)

                objects: list[StorageObject] = []
                for item in response.get("items", []):
                    storage_object = StorageObject.from_api_response(item)
                    # Set the project_id from the parameter
                    storage_object.project_id = project_id
                    objects.append(storage_object)

                logger.info(f"Found {len(objects)} objects in bucket: {bucket_name}")
                return objects

            except Exception as e:
                logger.error(f"Failed to list objects in bucket {bucket_name}: {e}")
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        objects = await self._execute_with_retry(
            operation=_list_objects,
            operation_name=f"list_objects({bucket_name})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            objects,
            ttl=config.cache_ttl_resources,
        )

        return objects


# Singleton instance
_storage_service: StorageService | None = None


async def get_storage_service() -> StorageService:
    """Get the singleton StorageService instance.

    Returns:
        StorageService instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
