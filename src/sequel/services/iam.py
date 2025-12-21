"""Google Cloud IAM service using IAM API."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.iam import ServiceAccount
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class IAMService(BaseService):
    """Service for interacting with Google Cloud IAM Service Accounts."""

    def __init__(self) -> None:
        """Initialize the IAM service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> Any:
        """Get or create the IAM API client.

        Returns:
            Initialized iam client
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = discovery.build(
                "iam",
                "v1",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )
        return self._client

    async def list_service_accounts(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[ServiceAccount]:
        """List all service accounts in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of ServiceAccount instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"service_accounts:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} service accounts from cache")
                return cast("list[ServiceAccount]", cached)

        async def _list_service_accounts() -> list[ServiceAccount]:
            """Internal function to list service accounts."""
            client = await self._get_client()

            logger.info(f"Listing service accounts in project: {project_id}")

            try:
                # Build resource name
                name = f"projects/{project_id}"

                # Call the API
                request = client.projects().serviceAccounts().list(name=name)
                # Run blocking execute() in thread to avoid blocking event loop
                response = await asyncio.to_thread(request.execute)

                service_accounts: list[ServiceAccount] = []
                for item in response.get("accounts", []):
                    sa = ServiceAccount.from_api_response(item)
                    service_accounts.append(sa)

                logger.info(f"Found {len(service_accounts)} service accounts")
                return service_accounts

            except Exception as e:
                logger.error(f"Failed to list service accounts: {e}")
                return []

        # Execute with retry logic
        service_accounts = await self._execute_with_retry(
            operation=_list_service_accounts,
            operation_name=f"list_service_accounts({project_id})",
        )

        # Cache the results
        if use_cache:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, service_accounts, ttl)

        return service_accounts

    async def get_service_account(
        self,
        project_id: str,
        email: str,
        use_cache: bool = True,
    ) -> ServiceAccount | None:
        """Get a specific service account.

        Args:
            project_id: GCP project ID
            email: Service account email
            use_cache: Whether to use cached results

        Returns:
            ServiceAccount or None if not found

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"service_account:{project_id}:{email}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning service account {email} from cache")
                return cast("ServiceAccount", cached)

        async def _get_service_account() -> ServiceAccount | None:
            """Internal function to get service account."""
            client = await self._get_client()

            logger.info(f"Getting service account: {project_id}/{email}")

            try:
                # Build resource name
                name = f"projects/{project_id}/serviceAccounts/{email}"

                request = client.projects().serviceAccounts().get(name=name)
                response = request.execute()

                sa = ServiceAccount.from_api_response(response)
                logger.info(f"Retrieved service account: {email}")
                return sa

            except Exception as e:
                logger.error(f"Failed to get service account {email}: {e}")
                return None

        # Execute with retry logic
        service_account = await self._execute_with_retry(
            operation=_get_service_account,
            operation_name=f"get_service_account({project_id}, {email})",
        )

        # Cache the result
        if use_cache and service_account is not None:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, service_account, ttl)

        return service_account


# Global service instance
_iam_service: IAMService | None = None


async def get_iam_service() -> IAMService:
    """Get the global IAM service instance.

    Returns:
        Initialized IAMService
    """
    global _iam_service
    if _iam_service is None:
        _iam_service = IAMService()
    return _iam_service


def reset_iam_service() -> None:
    """Reset the global IAM service (mainly for testing)."""
    global _iam_service
    _iam_service = None
