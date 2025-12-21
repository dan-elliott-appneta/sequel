"""Unit tests for CloudSQL service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.cloudsql import CloudSQLInstance
from sequel.services.cloudsql import (
    CloudSQLService,
    get_cloudsql_service,
    reset_cloudsql_service,
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
def mock_cloudsql_client() -> MagicMock:
    """Create mock Cloud SQL Admin API client."""
    return MagicMock()


@pytest.fixture
def cloudsql_service() -> CloudSQLService:
    """Create CloudSQL service instance."""
    reset_cloudsql_service()
    return CloudSQLService()


class TestCloudSQLService:
    """Tests for CloudSQLService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, cloudsql_service: CloudSQLService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Cloud SQL Admin client."""
        with (
            patch("sequel.services.cloudsql.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.cloudsql.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await cloudsql_service._get_client()

            mock_build.assert_called_once_with(
                "sqladmin",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert cloudsql_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, cloudsql_service: CloudSQLService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        cloudsql_service._client = mock_client

        client = await cloudsql_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_instances_success(
        self, cloudsql_service: CloudSQLService, mock_cloudsql_client: MagicMock
    ) -> None:
        """Test listing Cloud SQL instances successfully."""
        mock_response = {
            "items": [
                {
                    "name": "production-db",
                    "project": "test-project",
                    "databaseVersion": "POSTGRES_14",
                    "state": "RUNNABLE",
                    "region": "us-central1",
                    "settings": {"tier": "db-n1-standard-1"},
                    "ipAddresses": [{"ipAddress": "10.0.0.1"}],
                },
                {
                    "name": "staging-db",
                    "project": "test-project",
                    "databaseVersion": "MYSQL_8_0",
                    "state": "RUNNABLE",
                    "region": "us-west1",
                    "settings": {"tier": "db-f1-micro"},
                    "ipAddresses": [{"ipAddress": "10.0.0.2"}],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_cloudsql_client.instances().list.return_value = mock_request

        cloudsql_service._client = mock_cloudsql_client

        instances = await cloudsql_service.list_instances("test-project", use_cache=False)

        assert len(instances) == 2
        assert isinstance(instances[0], CloudSQLInstance)
        assert instances[0].instance_name == "production-db"
        assert instances[1].instance_name == "staging-db"

    @pytest.mark.asyncio
    async def test_list_instances_empty(
        self, cloudsql_service: CloudSQLService, mock_cloudsql_client: MagicMock
    ) -> None:
        """Test listing instances when none exist."""
        mock_response: dict[str, Any] = {"items": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_cloudsql_client.instances().list.return_value = mock_request

        cloudsql_service._client = mock_cloudsql_client

        instances = await cloudsql_service.list_instances("test-project", use_cache=False)

        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_list_instances_error(
        self, cloudsql_service: CloudSQLService, mock_cloudsql_client: MagicMock
    ) -> None:
        """Test error handling when listing instances."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_cloudsql_client.instances().list.return_value = mock_request

        cloudsql_service._client = mock_cloudsql_client

        instances = await cloudsql_service.list_instances("test-project", use_cache=False)

        # Should return empty list on error
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_list_instances_with_cache(
        self, cloudsql_service: CloudSQLService, mock_cloudsql_client: MagicMock
    ) -> None:
        """Test listing instances with caching."""
        mock_instance = CloudSQLInstance(
            id="cached-db",
            name="cached-db",
            instance_name="cached-db",
            database_version="POSTGRES_13",
            tier="db-f1-micro",
            state="RUNNABLE",
        )

        with patch.object(cloudsql_service._cache, "get", return_value=[mock_instance]):
            instances = await cloudsql_service.list_instances("test-project", use_cache=True)

            assert len(instances) == 1
            assert instances[0] == mock_instance

    @pytest.mark.asyncio
    async def test_get_instance_success(
        self, cloudsql_service: CloudSQLService, mock_cloudsql_client: MagicMock
    ) -> None:
        """Test getting a specific Cloud SQL instance."""
        mock_response = {
            "name": "my-database",
            "project": "test-project",
            "databaseVersion": "MYSQL_8_0",
            "state": "RUNNABLE",
            "region": "europe-west1",
            "settings": {"tier": "db-n1-standard-2"},
            "ipAddresses": [{"ipAddress": "10.128.0.5"}],
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_cloudsql_client.instances().get.return_value = mock_request

        cloudsql_service._client = mock_cloudsql_client

        instance = await cloudsql_service.get_instance(
            "test-project", "my-database", use_cache=False
        )

        assert instance is not None
        assert isinstance(instance, CloudSQLInstance)
        assert instance.instance_name == "my-database"
        assert instance.database_version == "MYSQL_8_0"

    @pytest.mark.asyncio
    async def test_get_instance_not_found(
        self, cloudsql_service: CloudSQLService, mock_cloudsql_client: MagicMock
    ) -> None:
        """Test getting an instance that doesn't exist."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("Not found"))
        mock_cloudsql_client.instances().get.return_value = mock_request

        cloudsql_service._client = mock_cloudsql_client

        instance = await cloudsql_service.get_instance(
            "test-project", "nonexistent-db", use_cache=False
        )

        assert instance is None

    @pytest.mark.asyncio
    async def test_get_instance_with_cache(
        self, cloudsql_service: CloudSQLService, mock_cloudsql_client: MagicMock
    ) -> None:
        """Test getting instance with caching."""
        mock_instance = CloudSQLInstance(
            id="cached-instance",
            name="cached-instance",
            instance_name="cached-instance",
            database_version="POSTGRES_14",
            tier="db-n1-standard-1",
            state="RUNNABLE",
        )

        with patch.object(cloudsql_service._cache, "get", return_value=mock_instance):
            instance = await cloudsql_service.get_instance(
                "test-project", "cached-instance", use_cache=True
            )

            assert instance == mock_instance


class TestGetCloudSQLService:
    """Tests for get_cloudsql_service function."""

    @pytest.mark.asyncio
    async def test_get_cloudsql_service_creates_instance(self) -> None:
        """Test that get_cloudsql_service creates a global instance."""
        reset_cloudsql_service()

        service1 = await get_cloudsql_service()
        service2 = await get_cloudsql_service()

        assert service1 is service2
        assert isinstance(service1, CloudSQLService)

    @pytest.mark.asyncio
    async def test_reset_cloudsql_service(self) -> None:
        """Test that reset_cloudsql_service clears the global instance."""
        service1 = await get_cloudsql_service()
        reset_cloudsql_service()
        service2 = await get_cloudsql_service()

        assert service1 is not service2
