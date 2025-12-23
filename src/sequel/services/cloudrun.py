"""Google Cloud Run service for managing services and jobs."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.cloudrun import (
    CloudRunJob as CloudRunJobModel,
)
from sequel.models.cloudrun import (
    CloudRunService as CloudRunServiceModel,
)
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class CloudRunService(BaseService):
    """Service for interacting with Google Cloud Run API."""

    def __init__(self) -> None:
        """Initialize Cloud Run service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> Any:
        """Get or create Cloud Run API client.

        Returns:
            Cloud Run API client
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = discovery.build(
                "run",
                "v2",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )
        return self._client

    async def list_services(
        self, project_id: str, use_cache: bool = True
    ) -> list[CloudRunServiceModel]:
        """List all Cloud Run services in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of CloudRunServiceModel instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"cloudrun:services:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} Cloud Run services from cache")
                return cast("list[CloudRunServiceModel]", cached)

        async def _list_services() -> list[CloudRunServiceModel]:
            """Internal function to list Cloud Run services."""
            client = await self._get_client()

            logger.info(f"Listing Cloud Run services in project: {project_id}")

            try:
                # Use wildcard location to get all services across all regions
                # Format: projects/{project}/locations/-
                parent = f"projects/{project_id}/locations/-"

                services: list[CloudRunServiceModel] = []
                next_page_token = None

                # Handle pagination
                while True:
                    # Call the API with pagination token
                    request = client.projects().locations().services().list(
                        parent=parent, pageToken=next_page_token
                    )
                    # Run blocking execute() in thread with timeout to prevent UI hangs
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(request.execute),
                            timeout=10.0  # 10 second timeout per API call
                        )
                    except asyncio.TimeoutError:
                        logger.error(
                            f"Timeout listing Cloud Run services for {project_id} "
                            f"(pageToken={next_page_token})"
                        )
                        # Return what we have so far on timeout
                        return services

                    # Process services from this page
                    for item in response.get("services", []):
                        service = CloudRunServiceModel.from_api_response(item)
                        services.append(service)
                        logger.debug(f"Loaded Cloud Run service: {service.service_name}")

                    # Check for more pages
                    next_page_token = response.get("nextPageToken")
                    if not next_page_token:
                        break

                    logger.debug(
                        f"Fetching next page of services (current count: {len(services)})"
                    )

                logger.info(f"Found {len(services)} Cloud Run services")
                return services

            except Exception as e:
                logger.error(f"Failed to list Cloud Run services: {e}", exc_info=True)
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        services = await self._execute_with_retry(
            operation=_list_services,
            operation_name=f"list_services({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            services,
            ttl=config.cache_ttl_resources,
        )

        return services

    async def list_jobs(
        self, project_id: str, use_cache: bool = True
    ) -> list[CloudRunJobModel]:
        """List all Cloud Run jobs in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of CloudRunJobModel instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"cloudrun:jobs:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} Cloud Run jobs from cache")
                return cast("list[CloudRunJobModel]", cached)

        async def _list_jobs() -> list[CloudRunJobModel]:
            """Internal function to list Cloud Run jobs."""
            client = await self._get_client()

            logger.info(f"Listing Cloud Run jobs in project: {project_id}")

            try:
                # Use wildcard location to get all jobs across all regions
                # Format: projects/{project}/locations/-
                parent = f"projects/{project_id}/locations/-"

                jobs: list[CloudRunJobModel] = []
                next_page_token = None

                # Handle pagination
                while True:
                    # Call the API with pagination token
                    request = client.projects().locations().jobs().list(
                        parent=parent, pageToken=next_page_token
                    )
                    # Run blocking execute() in thread with timeout to prevent UI hangs
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(request.execute),
                            timeout=10.0  # 10 second timeout per API call
                        )
                    except asyncio.TimeoutError:
                        logger.error(
                            f"Timeout listing Cloud Run jobs for {project_id} "
                            f"(pageToken={next_page_token})"
                        )
                        # Return what we have so far on timeout
                        return jobs

                    # Process jobs from this page
                    for item in response.get("jobs", []):
                        job = CloudRunJobModel.from_api_response(item)
                        jobs.append(job)
                        logger.debug(f"Loaded Cloud Run job: {job.job_name}")

                    # Check for more pages
                    next_page_token = response.get("nextPageToken")
                    if not next_page_token:
                        break

                    logger.debug(
                        f"Fetching next page of jobs (current count: {len(jobs)})"
                    )

                logger.info(f"Found {len(jobs)} Cloud Run jobs")
                return jobs

            except Exception as e:
                logger.error(f"Failed to list Cloud Run jobs: {e}", exc_info=True)
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        jobs = await self._execute_with_retry(
            operation=_list_jobs,
            operation_name=f"list_jobs({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            jobs,
            ttl=config.cache_ttl_resources,
        )

        return jobs


# Singleton instance
_cloudrun_service: CloudRunService | None = None


async def get_cloudrun_service() -> CloudRunService:
    """Get the singleton CloudRunService instance.

    Returns:
        CloudRunService instance
    """
    global _cloudrun_service
    if _cloudrun_service is None:
        _cloudrun_service = CloudRunService()
    return _cloudrun_service
