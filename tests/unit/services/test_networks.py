"""Unit tests for Networks service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.networks import Subnet, VPCNetwork
from sequel.services.networks import (
    NetworksService,
    get_networks_service,
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
    """Create mock Compute API client."""
    return MagicMock()


@pytest.fixture
def networks_service() -> NetworksService:
    """Create Networks service instance."""
    return NetworksService()


class TestNetworksService:
    """Tests for NetworksService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, networks_service: NetworksService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Compute client."""
        with (
            patch("sequel.services.networks.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.networks.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await networks_service._get_client()

            mock_build.assert_called_once_with(
                "compute",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert networks_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, networks_service: NetworksService
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        networks_service._client = mock_client

        client = await networks_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_networks_success(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing networks successfully."""
        mock_response = {
            "items": [
                {
                    "name": "production-vpc",
                    "id": "1234567890",
                    "creationTimestamp": "2023-01-01T00:00:00.000-08:00",
                    "autoCreateSubnetworks": False,
                    "subnetworks": [
                        "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1/subnetworks/subnet-1",
                        "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-east1/subnetworks/subnet-2",
                    ],
                    "routingConfig": {"routingMode": "REGIONAL"},
                    "mtu": 1500,
                    "selfLink": "https://www.googleapis.com/compute/v1/projects/my-project/global/networks/production-vpc"
                },
                {
                    "name": "default",
                    "autoCreateSubnetworks": True,
                    "routingConfig": {"routingMode": "GLOBAL"},
                    "mtu": 1460,
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.networks().list.return_value = mock_request

        networks_service._client = mock_compute_client

        networks = await networks_service.list_networks("test-project", use_cache=False)

        assert len(networks) == 2
        assert isinstance(networks[0], VPCNetwork)
        assert networks[0].network_name == "production-vpc"
        assert networks[0].mode == "CUSTOM"
        assert networks[0].subnet_count == 2
        assert networks[0].mtu == 1500
        assert networks[0].routing_mode == "REGIONAL"
        assert networks[1].network_name == "default"
        assert networks[1].mode == "AUTO"
        assert networks[1].mtu == 1460
        assert networks[1].routing_mode == "GLOBAL"

    @pytest.mark.asyncio
    async def test_list_networks_empty(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing networks when none exist."""
        mock_response: dict[str, Any] = {"items": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.networks().list.return_value = mock_request

        networks_service._client = mock_compute_client

        networks = await networks_service.list_networks("test-project", use_cache=False)

        assert len(networks) == 0

    @pytest.mark.asyncio
    async def test_list_networks_no_items_key(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing networks when response has no items key."""
        mock_response: dict[str, Any] = {}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.networks().list.return_value = mock_request

        networks_service._client = mock_compute_client

        networks = await networks_service.list_networks("test-project", use_cache=False)

        assert len(networks) == 0

    @pytest.mark.asyncio
    async def test_list_networks_error(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test error handling when listing networks."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_compute_client.networks().list.return_value = mock_request

        networks_service._client = mock_compute_client

        networks = await networks_service.list_networks("test-project", use_cache=False)

        # Should return empty list on error
        assert len(networks) == 0

    @pytest.mark.asyncio
    async def test_list_networks_with_cache(
        self, networks_service: NetworksService
    ) -> None:
        """Test listing networks with caching."""
        mock_network = VPCNetwork(
            id="cached-network",
            name="cached-network",
            network_name="cached-network",
            mode="CUSTOM",
        )

        with patch.object(networks_service._cache, "get", return_value=[mock_network]):
            networks = await networks_service.list_networks("test-project", use_cache=True)

            assert len(networks) == 1
            assert networks[0] == mock_network

    @pytest.mark.asyncio
    async def test_list_networks_caching(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test that results are cached."""
        mock_response = {
            "items": [
                {
                    "name": "test-network",
                    "autoCreateSubnetworks": False,
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.networks().list.return_value = mock_request

        networks_service._client = mock_compute_client

        with patch.object(networks_service._cache, "set") as mock_set:
            await networks_service.list_networks("test-project", use_cache=False)

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "networks:test-project"
            # Second argument should be the networks list
            assert len(mock_set.call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_list_subnets_success(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing subnets successfully."""
        mock_response = {
            "items": {
                "regions/us-central1": {
                    "subnetworks": [
                        {
                            "name": "subnet-1",
                            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/production-vpc",
                            "ipCidrRange": "10.128.0.0/20",
                            "gatewayAddress": "10.128.0.1",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                            "privateIpGoogleAccess": True,
                            "enableFlowLogs": True,
                            "purpose": "PRIVATE",
                        },
                    ]
                },
                "regions/us-east1": {
                    "subnetworks": [
                        {
                            "name": "subnet-2",
                            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/default",
                            "ipCidrRange": "10.142.0.0/20",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-east1",
                            "privateIpGoogleAccess": False,
                            "enableFlowLogs": False,
                        },
                    ]
                },
            }
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        subnets = await networks_service.list_subnets("test-project", use_cache=False)

        assert len(subnets) == 2
        assert isinstance(subnets[0], Subnet)
        assert subnets[0].subnet_name == "subnet-1"
        assert subnets[0].network_name == "production-vpc"
        assert subnets[0].region == "us-central1"
        assert subnets[0].ip_cidr_range == "10.128.0.0/20"
        assert subnets[0].private_ip_google_access is True
        assert subnets[0].enable_flow_logs is True
        assert subnets[1].subnet_name == "subnet-2"
        assert subnets[1].network_name == "default"
        assert subnets[1].region == "us-east1"

    @pytest.mark.asyncio
    async def test_list_subnets_filtered_by_network(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing subnets filtered by network name."""
        mock_response = {
            "items": {
                "regions/us-central1": {
                    "subnetworks": [
                        {
                            "name": "subnet-1",
                            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/production-vpc",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                        },
                        {
                            "name": "subnet-2",
                            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/default",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                        },
                    ]
                },
            }
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        subnets = await networks_service.list_subnets(
            "test-project", network_name="production-vpc", use_cache=False
        )

        # Should only return subnet-1 (production-vpc), not subnet-2 (default)
        assert len(subnets) == 1
        assert subnets[0].subnet_name == "subnet-1"
        assert subnets[0].network_name == "production-vpc"

    @pytest.mark.asyncio
    async def test_list_subnets_empty(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing subnets when none exist."""
        mock_response: dict[str, Any] = {"items": {}}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        subnets = await networks_service.list_subnets("test-project", use_cache=False)

        assert len(subnets) == 0

    @pytest.mark.asyncio
    async def test_list_subnets_no_items_key(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing subnets when response has no items key."""
        mock_response: dict[str, Any] = {}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        subnets = await networks_service.list_subnets("test-project", use_cache=False)

        assert len(subnets) == 0

    @pytest.mark.asyncio
    async def test_list_subnets_error(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test error handling when listing subnets."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        subnets = await networks_service.list_subnets("test-project", use_cache=False)

        # Should return empty list on error
        assert len(subnets) == 0

    @pytest.mark.asyncio
    async def test_list_subnets_with_cache(
        self, networks_service: NetworksService
    ) -> None:
        """Test listing subnets with caching."""
        mock_subnet = Subnet(
            id="us-central1:cached-subnet",
            name="cached-subnet",
            subnet_name="cached-subnet",
            network_name="default",
            region="us-central1",
        )

        with patch.object(networks_service._cache, "get", return_value=[mock_subnet]):
            subnets = await networks_service.list_subnets("test-project", use_cache=True)

            assert len(subnets) == 1
            assert subnets[0] == mock_subnet

    @pytest.mark.asyncio
    async def test_list_subnets_caching_all_subnets(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test that results are cached when listing all subnets."""
        mock_response = {
            "items": {
                "regions/us-central1": {
                    "subnetworks": [
                        {
                            "name": "test-subnet",
                            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/default",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                        },
                    ]
                },
            }
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        with patch.object(networks_service._cache, "set") as mock_set:
            await networks_service.list_subnets("test-project", use_cache=False)

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "subnets:test-project"
            # Second argument should be the subnets list
            assert len(mock_set.call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_list_subnets_caching_filtered(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test that results are cached when filtering by network."""
        mock_response = {
            "items": {
                "regions/us-central1": {
                    "subnetworks": [
                        {
                            "name": "test-subnet",
                            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/production-vpc",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                        },
                    ]
                },
            }
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        with patch.object(networks_service._cache, "set") as mock_set:
            await networks_service.list_subnets(
                "test-project", network_name="production-vpc", use_cache=False
            )

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key with network name
            assert mock_set.call_args[0][0] == "subnets:test-project:production-vpc"
            # Second argument should be the subnets list
            assert len(mock_set.call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_list_subnets_region_without_subnetworks(
        self, networks_service: NetworksService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing subnets when a region has no subnetworks."""
        mock_response = {
            "items": {
                "regions/us-central1": {
                    "subnetworks": [
                        {
                            "name": "subnet-1",
                            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/default",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                        },
                    ]
                },
                "regions/us-east1": {
                    # No subnetworks key
                },
            }
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.subnetworks().aggregatedList.return_value = mock_request

        networks_service._client = mock_compute_client

        subnets = await networks_service.list_subnets("test-project", use_cache=False)

        # Should only return subnet-1 from us-central1, skip us-east1
        assert len(subnets) == 1
        assert subnets[0].subnet_name == "subnet-1"


class TestGetNetworksService:
    """Tests for get_networks_service function."""

    @pytest.mark.asyncio
    async def test_get_networks_service_creates_instance(self) -> None:
        """Test that get_networks_service creates a global instance."""
        service1 = await get_networks_service()
        service2 = await get_networks_service()

        assert service1 is service2
        assert isinstance(service1, NetworksService)
