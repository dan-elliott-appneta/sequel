"""Google Secret Manager service using Secret Manager API."""

from typing import Any, cast

from google.cloud import secretmanager_v1

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.secrets import Secret
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class SecretManagerService(BaseService):
    """Service for interacting with Google Secret Manager.

    SECURITY: This service only retrieves secret metadata, never secret values.
    """

    def __init__(self) -> None:
        """Initialize the Secret Manager service."""
        super().__init__()
        self._client: secretmanager_v1.SecretManagerServiceClient | None = None
        self._cache = get_cache()

    async def _get_client(self) -> secretmanager_v1.SecretManagerServiceClient:
        """Get or create the Secret Manager client.

        Returns:
            Initialized SecretManagerServiceClient
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = secretmanager_v1.SecretManagerServiceClient(
                credentials=auth_manager.credentials
            )
        return self._client

    async def list_secrets(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[Secret]:
        """List all secrets in a project (metadata only).

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of Secret instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails

        Note:
            Secret values are never retrieved, only metadata.
        """
        cache_key = f"secrets:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} secrets from cache")
                return cast("list[Secret]", cached)

        async def _list_secrets() -> list[Secret]:
            """Internal function to list secrets."""
            client = await self._get_client()

            logger.info(f"Listing secrets (metadata only) in project: {project_id}")

            try:
                # Build parent path
                parent = f"projects/{project_id}"

                # Call the API
                request = secretmanager_v1.ListSecretsRequest(parent=parent)

                secrets: list[Secret] = []
                # The client.list_secrets returns an iterator
                for secret_proto in client.list_secrets(request=request):
                    secret_dict = self._proto_to_dict(secret_proto)
                    secret = Secret.from_api_response(secret_dict)
                    secrets.append(secret)

                logger.info(f"Found {len(secrets)} secrets")
                return secrets

            except Exception as e:
                logger.error(f"Failed to list secrets: {e}")
                return []

        # Execute with retry logic
        secrets = await self._execute_with_retry(
            operation=_list_secrets,
            operation_name=f"list_secrets({project_id})",
        )

        # Cache the results
        if use_cache:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, secrets, ttl)

        return secrets

    async def get_secret(
        self,
        project_id: str,
        secret_name: str,
        use_cache: bool = True,
    ) -> Secret | None:
        """Get a specific secret's metadata (not the secret value).

        Args:
            project_id: GCP project ID
            secret_name: Secret name
            use_cache: Whether to use cached results

        Returns:
            Secret or None if not found

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails

        Note:
            Secret value is never retrieved, only metadata.
        """
        cache_key = f"secret:{project_id}:{secret_name}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning secret {secret_name} from cache")
                return cast("Secret", cached)

        async def _get_secret() -> Secret | None:
            """Internal function to get secret."""
            client = await self._get_client()

            logger.info(f"Getting secret metadata (not value): {project_id}/{secret_name}")

            try:
                # Build secret path
                name = f"projects/{project_id}/secrets/{secret_name}"

                request = secretmanager_v1.GetSecretRequest(name=name)
                secret_proto = client.get_secret(request=request)

                secret_dict = self._proto_to_dict(secret_proto)
                secret = Secret.from_api_response(secret_dict)

                logger.info(f"Retrieved secret metadata: {secret_name}")
                return secret

            except Exception as e:
                logger.error(f"Failed to get secret {secret_name}: {e}")
                return None

        # Execute with retry logic
        secret = await self._execute_with_retry(
            operation=_get_secret,
            operation_name=f"get_secret({project_id}, {secret_name})",
        )

        # Cache the result
        if use_cache and secret is not None:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, secret, ttl)

        return secret

    def _proto_to_dict(self, proto_message: Any) -> dict[str, Any]:
        """Convert protobuf message to dictionary.

        Args:
            proto_message: Protobuf message

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {}

        if hasattr(proto_message, "name"):
            result["name"] = proto_message.name
        if hasattr(proto_message, "replication"):
            # Convert replication to dict
            replication: dict[str, Any] = {}
            repl = proto_message.replication
            if hasattr(repl, "automatic"):
                replication["automatic"] = {}
            elif hasattr(repl, "user_managed"):
                replication["userManaged"] = {}
            result["replication"] = replication
        if hasattr(proto_message, "create_time"):
            result["createTime"] = proto_message.create_time.isoformat()
        if hasattr(proto_message, "labels"):
            result["labels"] = dict(proto_message.labels)

        return result


# Global service instance
_secret_manager_service: SecretManagerService | None = None


async def get_secret_manager_service() -> SecretManagerService:
    """Get the global Secret Manager service instance.

    Returns:
        Initialized SecretManagerService
    """
    global _secret_manager_service
    if _secret_manager_service is None:
        _secret_manager_service = SecretManagerService()
    return _secret_manager_service


def reset_secret_manager_service() -> None:
    """Reset the global Secret Manager service (mainly for testing)."""
    global _secret_manager_service
    _secret_manager_service = None
