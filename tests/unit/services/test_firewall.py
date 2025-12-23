"""Unit tests for Firewall service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.firewall import FirewallPolicy
from sequel.services.firewall import (
    FirewallService,
    get_firewall_service,
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
def mock_compute_client() -> MagicMock:
    """Create mock Compute Engine API client."""
    return MagicMock()


@pytest.fixture
def firewall_service() -> FirewallService:
    """Create Firewall service instance."""
    # Note: No reset function for firewall service, create fresh instance
    return FirewallService()


class TestFirewallService:
    """Tests for FirewallService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, firewall_service: FirewallService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Compute Engine client."""
        with (
            patch("sequel.services.firewall.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.firewall.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await firewall_service._get_client()

            mock_build.assert_called_once_with(
                "compute",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert firewall_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, firewall_service: FirewallService
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        firewall_service._client = mock_client

        client = await firewall_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_firewall_policies_success(
        self, firewall_service: FirewallService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing firewall policies successfully."""
        mock_response = {
            "items": [
                {
                    "name": "allow-ssh",
                    "description": "Allow SSH",
                    "network": "projects/test-project/global/networks/default",
                    "priority": 1000,
                    "direction": "INGRESS",
                    "disabled": False,
                    "allowed": [
                        {"IPProtocol": "tcp", "ports": ["22"]}
                    ],
                },
                {
                    "name": "deny-all",
                    "description": "Deny all traffic",
                    "network": "projects/test-project/global/networks/default",
                    "priority": 65535,
                    "direction": "INGRESS",
                    "disabled": False,
                    "denied": [
                        {"IPProtocol": "all"}
                    ],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.firewalls().list.return_value = mock_request

        firewall_service._client = mock_compute_client

        policies = await firewall_service.list_firewall_policies("test-project", use_cache=False)

        assert len(policies) == 2
        assert isinstance(policies[0], FirewallPolicy)
        assert policies[0].policy_name == "allow-ssh"
        assert policies[0].rule_count == 1
        assert policies[1].policy_name == "deny-all"
        assert policies[1].rule_count == 1

    @pytest.mark.asyncio
    async def test_list_firewall_policies_empty(
        self, firewall_service: FirewallService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing policies when none exist."""
        mock_response: dict[str, Any] = {"items": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.firewalls().list.return_value = mock_request

        firewall_service._client = mock_compute_client

        policies = await firewall_service.list_firewall_policies("test-project", use_cache=False)

        assert len(policies) == 0

    @pytest.mark.asyncio
    async def test_list_firewall_policies_no_items_key(
        self, firewall_service: FirewallService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing policies when response has no items key."""
        mock_response: dict[str, Any] = {}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.firewalls().list.return_value = mock_request

        firewall_service._client = mock_compute_client

        policies = await firewall_service.list_firewall_policies("test-project", use_cache=False)

        assert len(policies) == 0

    @pytest.mark.asyncio
    async def test_list_firewall_policies_error(
        self, firewall_service: FirewallService, mock_compute_client: MagicMock
    ) -> None:
        """Test error handling when listing policies."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_compute_client.firewalls().list.return_value = mock_request

        firewall_service._client = mock_compute_client

        policies = await firewall_service.list_firewall_policies("test-project", use_cache=False)

        # Should return empty list on error
        assert len(policies) == 0

    @pytest.mark.asyncio
    async def test_list_firewall_policies_with_cache(
        self, firewall_service: FirewallService
    ) -> None:
        """Test listing policies with caching."""
        mock_policy = FirewallPolicy(
            id="cached-policy",
            name="cached-policy",
            policy_name="cached-policy",
            priority=1000,
        )

        with patch.object(firewall_service._cache, "get", return_value=[mock_policy]):
            policies = await firewall_service.list_firewall_policies("test-project", use_cache=True)

            assert len(policies) == 1
            assert policies[0] == mock_policy

    @pytest.mark.asyncio
    async def test_list_firewall_policies_disabled(
        self, firewall_service: FirewallService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing firewall policies including disabled ones."""
        mock_response = {
            "items": [
                {
                    "name": "disabled-policy",
                    "disabled": True,
                    "priority": 1000,
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.firewalls().list.return_value = mock_request

        firewall_service._client = mock_compute_client

        policies = await firewall_service.list_firewall_policies("test-project", use_cache=False)

        assert len(policies) == 1
        assert policies[0].disabled is True

    @pytest.mark.asyncio
    async def test_list_firewall_policies_caching(
        self, firewall_service: FirewallService, mock_compute_client: MagicMock
    ) -> None:
        """Test that results are cached."""
        mock_response = {
            "items": [
                {
                    "name": "test-policy",
                    "priority": 1000,
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.firewalls().list.return_value = mock_request

        firewall_service._client = mock_compute_client

        with patch.object(firewall_service._cache, "set") as mock_set:
            await firewall_service.list_firewall_policies("test-project", use_cache=False)

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "firewall:test-project"
            # Second argument should be the policies list
            assert len(mock_set.call_args[0][1]) == 1


class TestGetFirewallService:
    """Tests for get_firewall_service function."""

    @pytest.mark.asyncio
    async def test_get_firewall_service_creates_instance(self) -> None:
        """Test that get_firewall_service creates a global instance."""
        service1 = await get_firewall_service()
        service2 = await get_firewall_service()

        assert service1 is service2
        assert isinstance(service1, FirewallService)
