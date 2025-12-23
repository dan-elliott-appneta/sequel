"""Google Cloud Run service using gcloud CLI.

This implementation uses gcloud CLI instead of the API client to avoid
thread-safety issues that caused segfaults with other regional resources.
"""

import asyncio
import json
import subprocess
from typing import Any, cast

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.cloudrun import (
    CloudRunJob as CloudRunJobModel,
)
from sequel.models.cloudrun import (
    CloudRunService as CloudRunServiceModel,
)
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class CloudRunService(BaseService):
    """Service for interacting with Google Cloud Run via gcloud CLI."""

    def __init__(self) -> None:
        """Initialize Cloud Run service."""
        super().__init__()
        self._cache = get_cache()

    async def _run_gcloud_command(
        self, command: list[str], timeout: float = 30.0
    ) -> list[dict[str, Any]]:
        """Run a gcloud command and return parsed JSON output.

        Args:
            command: Command arguments to pass to gcloud
            timeout: Timeout in seconds

        Returns:
            List of parsed JSON objects from gcloud output
        """
        try:
            # Run gcloud command with JSON output
            process = await asyncio.create_subprocess_exec(
                "gcloud",
                *command,
                "--format=json",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            # Check for errors
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error(f"gcloud command failed: {error_msg}")
                return []

            # Parse JSON output
            if stdout:
                result = json.loads(stdout.decode())
                if isinstance(result, list):
                    return cast("list[dict[str, Any]]", result)
            return []

        except TimeoutError:
            logger.error(f"gcloud command timed out after {timeout}s: {' '.join(command)}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse gcloud JSON output: {e}")
            return []
        except Exception as e:
            logger.error(f"gcloud command failed: {e}", exc_info=True)
            return []

    async def list_services(
        self, project_id: str, use_cache: bool = True
    ) -> list[CloudRunServiceModel]:
        """List all Cloud Run services in a project using gcloud CLI.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of CloudRunServiceModel instances
        """
        cache_key = f"cloudrun:services:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} Cloud Run services from cache")
                return cast("list[CloudRunServiceModel]", cached)

        async def _list_services() -> list[CloudRunServiceModel]:
            """Internal function to list Cloud Run services via gcloud."""
            logger.info(f"Listing Cloud Run services in project: {project_id}")

            try:
                # Run gcloud command to list services
                command = [
                    "run",
                    "services",
                    "list",
                    f"--project={project_id}",
                ]

                items = await self._run_gcloud_command(command)

                services: list[CloudRunServiceModel] = []
                for item in items:
                    service = CloudRunServiceModel.from_gcloud_response(item)
                    services.append(service)
                    logger.debug(f"Loaded Cloud Run service: {service.service_name}")

                logger.info(f"Found {len(services)} Cloud Run services")
                return services

            except Exception as e:
                logger.error(f"Failed to list Cloud Run services: {e}", exc_info=True)
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
        """List all Cloud Run jobs in a project using gcloud CLI.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of CloudRunJobModel instances
        """
        cache_key = f"cloudrun:jobs:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} Cloud Run jobs from cache")
                return cast("list[CloudRunJobModel]", cached)

        async def _list_jobs() -> list[CloudRunJobModel]:
            """Internal function to list Cloud Run jobs via gcloud."""
            logger.info(f"Listing Cloud Run jobs in project: {project_id}")

            try:
                # Run gcloud command to list jobs
                command = [
                    "run",
                    "jobs",
                    "list",
                    f"--project={project_id}",
                ]

                items = await self._run_gcloud_command(command)

                jobs: list[CloudRunJobModel] = []
                for item in items:
                    job = CloudRunJobModel.from_gcloud_response(item)
                    jobs.append(job)
                    logger.debug(f"Loaded Cloud Run job: {job.job_name}")

                logger.info(f"Found {len(jobs)} Cloud Run jobs")
                return jobs

            except Exception as e:
                logger.error(f"Failed to list Cloud Run jobs: {e}", exc_info=True)
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
