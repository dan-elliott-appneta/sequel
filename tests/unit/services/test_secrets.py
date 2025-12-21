"""Unit tests for Secret Manager service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.secrets import Secret
from sequel.services.secrets import (
    SecretManagerService,
    get_secret_manager_service,
    reset_secret_manager_service,
)


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Create mock credentials."""
    creds = MagicMock()
    creds.valid = True
    return creds


@pytest.fixture
def mock_auth_manager(mock_credentials: MagicMock) -> AsyncMock:
    """Create mock auth manager."""
    manager = AsyncMock()
    manager.credentials = mock_credentials
    manager.project_id = "test-project"
    return manager


@pytest.fixture
def mock_secretmanager_client() -> MagicMock:
    """Create mock Secret Manager client."""
    return MagicMock()


@pytest.fixture
def secrets_service() -> SecretManagerService:
    """Create Secret Manager service instance."""
    reset_secret_manager_service()
    return SecretManagerService()


class TestSecretManagerService:
    """Tests for SecretManagerService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, secrets_service: SecretManagerService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Secret Manager client."""
        with (
            patch("sequel.services.secrets.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.secrets.secretmanager_v1.SecretManagerServiceClient") as mock_client_class,
        ):
            mock_client_class.return_value = MagicMock()

            client = await secrets_service._get_client()

            mock_client_class.assert_called_once_with(credentials=mock_auth_manager.credentials)
            assert client is not None
            assert secrets_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, secrets_service: SecretManagerService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        secrets_service._client = mock_client

        client = await secrets_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_secrets_success(
        self, secrets_service: SecretManagerService, mock_secretmanager_client: MagicMock
    ) -> None:
        """Test listing secrets successfully."""
        # Mock secret protobuf objects
        mock_secret_proto1 = MagicMock()
        mock_secret_proto1.name = "projects/test-project/secrets/api-key"
        mock_secret_proto1.replication = MagicMock()
        mock_secret_proto1.replication.automatic = MagicMock()
        mock_secret_proto1.create_time = MagicMock()
        mock_secret_proto1.create_time.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_secret_proto1.labels = {"env": "prod"}

        mock_secret_proto2 = MagicMock()
        mock_secret_proto2.name = "projects/test-project/secrets/db-password"
        mock_secret_proto2.replication = MagicMock()
        mock_secret_proto2.replication.automatic = MagicMock()
        mock_secret_proto2.create_time = MagicMock()
        mock_secret_proto2.create_time.isoformat.return_value = "2023-02-01T00:00:00Z"
        mock_secret_proto2.labels = {}

        # Mock list_secrets to return iterator
        mock_secretmanager_client.list_secrets.return_value = [
            mock_secret_proto1,
            mock_secret_proto2,
        ]
        secrets_service._client = mock_secretmanager_client

        secrets = await secrets_service.list_secrets("test-project", use_cache=False)

        assert len(secrets) == 2
        assert isinstance(secrets[0], Secret)
        assert secrets[0].secret_name == "api-key"
        assert secrets[1].secret_name == "db-password"

    @pytest.mark.asyncio
    async def test_list_secrets_empty(
        self, secrets_service: SecretManagerService, mock_secretmanager_client: MagicMock
    ) -> None:
        """Test listing secrets when none exist."""
        mock_secretmanager_client.list_secrets.return_value = []
        secrets_service._client = mock_secretmanager_client

        secrets = await secrets_service.list_secrets("test-project", use_cache=False)

        assert len(secrets) == 0

    @pytest.mark.asyncio
    async def test_list_secrets_error(
        self, secrets_service: SecretManagerService, mock_secretmanager_client: MagicMock
    ) -> None:
        """Test error handling when listing secrets."""
        mock_secretmanager_client.list_secrets.side_effect = Exception("API Error")
        secrets_service._client = mock_secretmanager_client

        secrets = await secrets_service.list_secrets("test-project", use_cache=False)

        # Should return empty list on error
        assert len(secrets) == 0

    @pytest.mark.asyncio
    async def test_list_secrets_with_cache(
        self, secrets_service: SecretManagerService, mock_secretmanager_client: MagicMock
    ) -> None:
        """Test listing secrets with caching."""
        mock_secret = Secret(
            id="cached-secret",
            name="cached-secret",
            secret_name="cached-secret",
            replication_policy="automatic",
        )

        with patch.object(secrets_service._cache, "get", return_value=[mock_secret]):
            secrets = await secrets_service.list_secrets("test-project", use_cache=True)

            assert len(secrets) == 1
            assert secrets[0] == mock_secret

    @pytest.mark.asyncio
    async def test_get_secret_success(
        self, secrets_service: SecretManagerService, mock_secretmanager_client: MagicMock
    ) -> None:
        """Test getting a specific secret."""
        mock_secret_proto = MagicMock()
        mock_secret_proto.name = "projects/test-project/secrets/my-secret"
        mock_secret_proto.replication = MagicMock()
        mock_secret_proto.replication.automatic = MagicMock()
        mock_secret_proto.create_time = MagicMock()
        mock_secret_proto.create_time.isoformat.return_value = "2023-03-15T12:00:00Z"
        mock_secret_proto.labels = {"team": "backend"}

        mock_secretmanager_client.get_secret.return_value = mock_secret_proto
        secrets_service._client = mock_secretmanager_client

        secret = await secrets_service.get_secret("test-project", "my-secret", use_cache=False)

        assert secret is not None
        assert isinstance(secret, Secret)
        assert secret.secret_name == "my-secret"
        assert secret.replication_policy == "automatic"

    @pytest.mark.asyncio
    async def test_get_secret_not_found(
        self, secrets_service: SecretManagerService, mock_secretmanager_client: MagicMock
    ) -> None:
        """Test getting a secret that doesn't exist."""
        mock_secretmanager_client.get_secret.side_effect = Exception("Not found")
        secrets_service._client = mock_secretmanager_client

        secret = await secrets_service.get_secret("test-project", "nonexistent", use_cache=False)

        assert secret is None

    @pytest.mark.asyncio
    async def test_get_secret_with_cache(
        self, secrets_service: SecretManagerService, mock_secretmanager_client: MagicMock
    ) -> None:
        """Test getting secret with caching."""
        mock_secret = Secret(
            id="cached-secret",
            name="cached-secret",
            secret_name="cached-secret",
            replication_policy="automatic",
        )

        with patch.object(secrets_service._cache, "get", return_value=mock_secret):
            secret = await secrets_service.get_secret(
                "test-project", "cached-secret", use_cache=True
            )

            assert secret == mock_secret

    def test_proto_to_dict_automatic_replication(
        self, secrets_service: SecretManagerService
    ) -> None:
        """Test converting protobuf with automatic replication to dict."""
        mock_proto = MagicMock()
        mock_proto.name = "projects/123/secrets/test-secret"

        mock_replication = MagicMock()
        mock_replication.automatic = MagicMock()
        mock_proto.replication = mock_replication

        mock_create_time = MagicMock()
        mock_create_time.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_proto.create_time = mock_create_time

        mock_proto.labels = {"env": "production"}

        result = secrets_service._proto_to_dict(mock_proto)

        assert result["name"] == "projects/123/secrets/test-secret"
        assert "automatic" in result["replication"]
        assert result["createTime"] == "2023-01-01T00:00:00Z"
        assert result["labels"] == {"env": "production"}

    def test_proto_to_dict_user_managed_replication(
        self, secrets_service: SecretManagerService
    ) -> None:
        """Test converting protobuf with user-managed replication to dict."""
        mock_proto = MagicMock()
        mock_proto.name = "projects/456/secrets/another-secret"

        mock_replication = MagicMock()
        mock_replication.user_managed = MagicMock()
        # Remove automatic attribute
        delattr(mock_replication, "automatic")
        mock_proto.replication = mock_replication

        mock_create_time = MagicMock()
        mock_create_time.isoformat.return_value = "2023-02-01T00:00:00Z"
        mock_proto.create_time = mock_create_time

        mock_proto.labels = {}

        result = secrets_service._proto_to_dict(mock_proto)

        assert result["name"] == "projects/456/secrets/another-secret"
        assert "userManaged" in result["replication"]

    def test_proto_to_dict_minimal(self, secrets_service: SecretManagerService) -> None:
        """Test converting protobuf with minimal fields."""
        mock_proto = MagicMock(spec=[])  # No attributes

        result = secrets_service._proto_to_dict(mock_proto)

        # Should return empty dict for proto with no recognized attributes
        assert result == {}


class TestGetSecretManagerService:
    """Tests for get_secret_manager_service function."""

    @pytest.mark.asyncio
    async def test_get_secret_manager_service_creates_instance(self) -> None:
        """Test that get_secret_manager_service creates a global instance."""
        reset_secret_manager_service()

        service1 = await get_secret_manager_service()
        service2 = await get_secret_manager_service()

        assert service1 is service2
        assert isinstance(service1, SecretManagerService)

    @pytest.mark.asyncio
    async def test_reset_secret_manager_service(self) -> None:
        """Test that reset_secret_manager_service clears the global instance."""
        service1 = await get_secret_manager_service()
        reset_secret_manager_service()
        service2 = await get_secret_manager_service()

        assert service1 is not service2
