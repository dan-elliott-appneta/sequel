"""Unit tests for IAM service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.iam import IAMRoleBinding, ServiceAccount
from sequel.services.iam import IAMService, get_iam_service, reset_iam_service


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
def mock_iam_client() -> MagicMock:
    """Create mock IAM API client."""
    return MagicMock()


@pytest.fixture
def mock_crm_client() -> MagicMock:
    """Create mock Cloud Resource Manager API client."""
    return MagicMock()


@pytest.fixture
def iam_service() -> IAMService:
    """Create IAM service instance."""
    reset_iam_service()
    return IAMService()


class TestIAMService:
    """Tests for IAMService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, iam_service: IAMService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates IAM client."""
        with (
            patch("sequel.services.iam.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.iam.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await iam_service._get_client()

            mock_build.assert_called_once_with(
                "iam",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert iam_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, iam_service: IAMService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        iam_service._client = mock_client

        client = await iam_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_get_crm_client_creates_client(
        self, iam_service: IAMService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_crm_client creates Cloud Resource Manager client."""
        with (
            patch("sequel.services.iam.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.iam.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await iam_service._get_crm_client()

            mock_build.assert_called_once_with(
                "cloudresourcemanager",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert iam_service._crm_client is not None

    @pytest.mark.asyncio
    async def test_get_crm_client_returns_cached(
        self, iam_service: IAMService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_crm_client returns cached client."""
        mock_client = MagicMock()
        iam_service._crm_client = mock_client

        client = await iam_service._get_crm_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_service_accounts_success(
        self, iam_service: IAMService, mock_iam_client: MagicMock
    ) -> None:
        """Test listing service accounts successfully."""
        # Mock the API response
        mock_response = {
            "accounts": [
                {
                    "name": "projects/test-project/serviceAccounts/sa1@test.iam.gserviceaccount.com",
                    "email": "sa1@test.iam.gserviceaccount.com",
                    "displayName": "Service Account 1",
                    "uniqueId": "12345",
                },
                {
                    "name": "projects/test-project/serviceAccounts/sa2@test.iam.gserviceaccount.com",
                    "email": "sa2@test.iam.gserviceaccount.com",
                    "displayName": "Service Account 2",
                    "uniqueId": "67890",
                },
            ]
        }

        # Mock the API call chain
        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_iam_client.projects().serviceAccounts().list.return_value = mock_request

        iam_service._client = mock_iam_client

        # Execute
        service_accounts = await iam_service.list_service_accounts("test-project", use_cache=False)

        # Verify
        assert len(service_accounts) == 2
        assert isinstance(service_accounts[0], ServiceAccount)
        assert service_accounts[0].email == "sa1@test.iam.gserviceaccount.com"
        assert service_accounts[1].email == "sa2@test.iam.gserviceaccount.com"

    @pytest.mark.asyncio
    async def test_list_service_accounts_empty(
        self, iam_service: IAMService, mock_iam_client: MagicMock
    ) -> None:
        """Test listing service accounts when none exist."""
        mock_response: dict[str, Any] = {"accounts": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_iam_client.projects().serviceAccounts().list.return_value = mock_request

        iam_service._client = mock_iam_client

        service_accounts = await iam_service.list_service_accounts("test-project", use_cache=False)

        assert len(service_accounts) == 0

    @pytest.mark.asyncio
    async def test_list_service_accounts_with_cache(
        self, iam_service: IAMService, mock_iam_client: MagicMock
    ) -> None:
        """Test listing service accounts with caching."""
        mock_sa = ServiceAccount(
            id="test@test.iam.gserviceaccount.com",
            name="test",
            email="test@test.iam.gserviceaccount.com",
            unique_id="12345",
        )

        # Mock cache to return cached data
        with patch.object(iam_service._cache, "get", return_value=[mock_sa]):
            service_accounts = await iam_service.list_service_accounts("test-project", use_cache=True)

            assert len(service_accounts) == 1
            assert service_accounts[0] == mock_sa

    @pytest.mark.asyncio
    async def test_get_service_account_success(
        self, iam_service: IAMService, mock_iam_client: MagicMock
    ) -> None:
        """Test getting a specific service account."""
        mock_response = {
            "name": "projects/test-project/serviceAccounts/sa@test.iam.gserviceaccount.com",
            "email": "sa@test.iam.gserviceaccount.com",
            "displayName": "Test SA",
            "uniqueId": "12345",
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_iam_client.projects().serviceAccounts().get.return_value = mock_request

        iam_service._client = mock_iam_client

        sa = await iam_service.get_service_account(
            "test-project", "sa@test.iam.gserviceaccount.com", use_cache=False
        )

        assert sa is not None
        assert isinstance(sa, ServiceAccount)
        assert sa.email == "sa@test.iam.gserviceaccount.com"

    @pytest.mark.asyncio
    async def test_get_service_account_not_found(
        self, iam_service: IAMService, mock_iam_client: MagicMock
    ) -> None:
        """Test getting a service account that doesn't exist."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("Not found"))
        mock_iam_client.projects().serviceAccounts().get.return_value = mock_request

        iam_service._client = mock_iam_client

        sa = await iam_service.get_service_account(
            "test-project", "nonexistent@test.iam.gserviceaccount.com", use_cache=False
        )

        assert sa is None

    @pytest.mark.asyncio
    async def test_get_service_account_roles_success(
        self, iam_service: IAMService, mock_crm_client: MagicMock
    ) -> None:
        """Test getting IAM roles for a service account."""
        mock_response = {
            "bindings": [
                {
                    "role": "roles/editor",
                    "members": [
                        "serviceAccount:sa@test.iam.gserviceaccount.com",
                        "user:test@example.com",
                    ],
                },
                {
                    "role": "roles/viewer",
                    "members": [
                        "serviceAccount:sa@test.iam.gserviceaccount.com",
                    ],
                },
                {
                    "role": "roles/owner",
                    "members": [
                        "user:admin@example.com",
                    ],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_crm_client.projects().getIamPolicy.return_value = mock_request

        iam_service._crm_client = mock_crm_client

        roles = await iam_service.get_service_account_roles(
            "test-project", "sa@test.iam.gserviceaccount.com", use_cache=False
        )

        # Should find 2 roles (editor and viewer, not owner)
        assert len(roles) == 2
        assert isinstance(roles[0], IAMRoleBinding)
        role_names = {r.role for r in roles}
        assert "roles/editor" in role_names
        assert "roles/viewer" in role_names
        assert "roles/owner" not in role_names

    @pytest.mark.asyncio
    async def test_get_service_account_roles_no_roles(
        self, iam_service: IAMService, mock_crm_client: MagicMock
    ) -> None:
        """Test getting IAM roles for service account with no roles."""
        mock_response = {
            "bindings": [
                {
                    "role": "roles/owner",
                    "members": [
                        "user:admin@example.com",
                    ],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_crm_client.projects().getIamPolicy.return_value = mock_request

        iam_service._crm_client = mock_crm_client

        roles = await iam_service.get_service_account_roles(
            "test-project", "sa@test.iam.gserviceaccount.com", use_cache=False
        )

        assert len(roles) == 0

    @pytest.mark.asyncio
    async def test_get_service_account_roles_empty_policy(
        self, iam_service: IAMService, mock_crm_client: MagicMock
    ) -> None:
        """Test getting IAM roles when policy has no bindings."""
        mock_response: dict[str, Any] = {"bindings": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_crm_client.projects().getIamPolicy.return_value = mock_request

        iam_service._crm_client = mock_crm_client

        roles = await iam_service.get_service_account_roles(
            "test-project", "sa@test.iam.gserviceaccount.com", use_cache=False
        )

        assert len(roles) == 0

    @pytest.mark.asyncio
    async def test_get_service_account_roles_error(
        self, iam_service: IAMService, mock_crm_client: MagicMock
    ) -> None:
        """Test error handling when getting IAM roles."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_crm_client.projects().getIamPolicy.return_value = mock_request

        iam_service._crm_client = mock_crm_client

        roles = await iam_service.get_service_account_roles(
            "test-project", "sa@test.iam.gserviceaccount.com", use_cache=False
        )

        # Should return empty list on error
        assert len(roles) == 0

    @pytest.mark.asyncio
    async def test_get_service_account_roles_with_cache(
        self, iam_service: IAMService, mock_crm_client: MagicMock
    ) -> None:
        """Test getting IAM roles with caching."""
        mock_role = IAMRoleBinding(
            id="roles/editor:sa@test.iam.gserviceaccount.com",
            name="roles/editor",
            role="roles/editor",
            member="sa@test.iam.gserviceaccount.com",
            resource="projects/test-project",
        )

        with patch.object(iam_service._cache, "get", return_value=[mock_role]):
            roles = await iam_service.get_service_account_roles(
                "test-project", "sa@test.iam.gserviceaccount.com", use_cache=True
            )

            assert len(roles) == 1
            assert roles[0] == mock_role


class TestGetIAMService:
    """Tests for get_iam_service function."""

    @pytest.mark.asyncio
    async def test_get_iam_service_creates_instance(self) -> None:
        """Test that get_iam_service creates a global instance."""
        reset_iam_service()

        service1 = await get_iam_service()
        service2 = await get_iam_service()

        assert service1 is service2
        assert isinstance(service1, IAMService)

    @pytest.mark.asyncio
    async def test_reset_iam_service(self) -> None:
        """Test that reset_iam_service clears the global instance."""
        service1 = await get_iam_service()
        reset_iam_service()
        service2 = await get_iam_service()

        assert service1 is not service2
