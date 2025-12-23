"""Unit tests for LoadBalancer service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.loadbalancer import LoadBalancer
from sequel.services.loadbalancer import (
    LoadBalancerService,
    get_loadbalancer_service,
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
def loadbalancer_service() -> LoadBalancerService:
    """Create LoadBalancer service instance."""
    return LoadBalancerService()


class TestLoadBalancerService:
    """Tests for LoadBalancerService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, loadbalancer_service: LoadBalancerService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Compute Engine client."""
        with (
            patch("sequel.services.loadbalancer.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.loadbalancer.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await loadbalancer_service._get_client()

            mock_build.assert_called_once_with(
                "compute",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert loadbalancer_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, loadbalancer_service: LoadBalancerService
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        loadbalancer_service._client = mock_client

        client = await loadbalancer_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_load_balancers_global(
        self, loadbalancer_service: LoadBalancerService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing global load balancers."""
        mock_global_response = {
            "items": [
                {
                    "name": "global-lb",
                    "IPAddress": "35.201.1.1",
                    "IPProtocol": "TCP",
                    "portRange": "443-443",
                    "loadBalancingScheme": "EXTERNAL",
                    "target": "projects/test-project/global/targetHttpProxies/proxy",
                },
            ]
        }
        mock_regions_response = {
            "items": []
        }

        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_global_response)
        mock_compute_client.globalForwardingRules().list.return_value = mock_global_request

        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value=mock_regions_response)
        mock_compute_client.regions().list.return_value = mock_regions_request

        loadbalancer_service._client = mock_compute_client

        lbs = await loadbalancer_service.list_load_balancers("test-project", use_cache=False)

        assert len(lbs) == 1
        assert isinstance(lbs[0], LoadBalancer)
        assert lbs[0].lb_name == "global-lb"
        assert lbs[0].load_balancing_scheme == "EXTERNAL"

    @pytest.mark.asyncio
    async def test_list_load_balancers_regional(
        self, loadbalancer_service: LoadBalancerService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing regional load balancers."""
        mock_global_response: dict[str, Any] = {"items": []}
        mock_regions_response = {
            "items": [
                {"name": "us-central1"},
                {"name": "us-east1"},
            ]
        }
        mock_regional_response1 = {
            "items": [
                {
                    "name": "regional-lb-1",
                    "IPAddress": "10.0.0.5",
                    "loadBalancingScheme": "INTERNAL",
                    "region": "us-central1",
                },
            ]
        }
        mock_regional_response2 = {
            "items": [
                {
                    "name": "regional-lb-2",
                    "IPAddress": "10.0.1.5",
                    "loadBalancingScheme": "INTERNAL",
                    "region": "us-east1",
                },
            ]
        }

        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_global_response)
        mock_compute_client.globalForwardingRules().list.return_value = mock_global_request

        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value=mock_regions_response)
        mock_compute_client.regions().list.return_value = mock_regions_request

        # Mock regional forwarding rules responses
        mock_regional_request1 = MagicMock()
        mock_regional_request1.execute = MagicMock(return_value=mock_regional_response1)
        mock_regional_request2 = MagicMock()
        mock_regional_request2.execute = MagicMock(return_value=mock_regional_response2)

        mock_compute_client.forwardingRules().list.side_effect = [
            mock_regional_request1,
            mock_regional_request2,
        ]

        loadbalancer_service._client = mock_compute_client

        lbs = await loadbalancer_service.list_load_balancers("test-project", use_cache=False)

        assert len(lbs) == 2
        assert lbs[0].lb_name == "regional-lb-1"
        assert lbs[1].lb_name == "regional-lb-2"

    @pytest.mark.asyncio
    async def test_list_load_balancers_mixed(
        self, loadbalancer_service: LoadBalancerService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing both global and regional load balancers."""
        mock_global_response = {
            "items": [
                {
                    "name": "global-lb",
                    "loadBalancingScheme": "EXTERNAL",
                },
            ]
        }
        mock_regions_response = {
            "items": [
                {"name": "us-west1"},
            ]
        }
        mock_regional_response = {
            "items": [
                {
                    "name": "regional-lb",
                    "loadBalancingScheme": "INTERNAL",
                },
            ]
        }

        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_global_response)
        mock_compute_client.globalForwardingRules().list.return_value = mock_global_request

        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value=mock_regions_response)
        mock_compute_client.regions().list.return_value = mock_regions_request

        mock_regional_request = MagicMock()
        mock_regional_request.execute = MagicMock(return_value=mock_regional_response)
        mock_compute_client.forwardingRules().list.return_value = mock_regional_request

        loadbalancer_service._client = mock_compute_client

        lbs = await loadbalancer_service.list_load_balancers("test-project", use_cache=False)

        assert len(lbs) == 2
        assert lbs[0].lb_name == "global-lb"
        assert lbs[1].lb_name == "regional-lb"

    @pytest.mark.asyncio
    async def test_list_load_balancers_empty(
        self, loadbalancer_service: LoadBalancerService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing load balancers when none exist."""
        mock_global_response: dict[str, Any] = {"items": []}
        mock_regions_response: dict[str, Any] = {"items": []}

        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_global_response)
        mock_compute_client.globalForwardingRules().list.return_value = mock_global_request

        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value=mock_regions_response)
        mock_compute_client.regions().list.return_value = mock_regions_request

        loadbalancer_service._client = mock_compute_client

        lbs = await loadbalancer_service.list_load_balancers("test-project", use_cache=False)

        assert len(lbs) == 0

    @pytest.mark.asyncio
    async def test_list_load_balancers_global_error(
        self, loadbalancer_service: LoadBalancerService, mock_compute_client: MagicMock
    ) -> None:
        """Test handling error in global forwarding rules."""
        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_compute_client.globalForwardingRules().list.return_value = mock_global_request

        mock_regions_response: dict[str, Any] = {"items": []}
        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value=mock_regions_response)
        mock_compute_client.regions().list.return_value = mock_regions_request

        loadbalancer_service._client = mock_compute_client

        lbs = await loadbalancer_service.list_load_balancers("test-project", use_cache=False)

        # Should still succeed with empty global results
        assert len(lbs) == 0

    @pytest.mark.asyncio
    async def test_list_load_balancers_regional_error(
        self, loadbalancer_service: LoadBalancerService, mock_compute_client: MagicMock
    ) -> None:
        """Test handling error in regional forwarding rules."""
        mock_global_response: dict[str, Any] = {"items": []}
        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_global_response)
        mock_compute_client.globalForwardingRules().list.return_value = mock_global_request

        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_compute_client.regions().list.return_value = mock_regions_request

        loadbalancer_service._client = mock_compute_client

        lbs = await loadbalancer_service.list_load_balancers("test-project", use_cache=False)

        # Should still succeed with empty regional results
        assert len(lbs) == 0

    @pytest.mark.asyncio
    async def test_list_load_balancers_with_cache(
        self, loadbalancer_service: LoadBalancerService
    ) -> None:
        """Test listing load balancers with caching."""
        mock_lb = LoadBalancer(
            id="cached-lb",
            name="cached-lb",
            lb_name="cached-lb",
            load_balancing_scheme="EXTERNAL",
        )

        with patch.object(loadbalancer_service._cache, "get", return_value=[mock_lb]):
            lbs = await loadbalancer_service.list_load_balancers("test-project", use_cache=True)

            assert len(lbs) == 1
            assert lbs[0] == mock_lb

    @pytest.mark.asyncio
    async def test_list_load_balancers_caching(
        self, loadbalancer_service: LoadBalancerService, mock_compute_client: MagicMock
    ) -> None:
        """Test that results are cached."""
        mock_global_response = {
            "items": [
                {"name": "test-lb"},
            ]
        }
        mock_regions_response: dict[str, Any] = {"items": []}

        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_global_response)
        mock_compute_client.globalForwardingRules().list.return_value = mock_global_request

        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value=mock_regions_response)
        mock_compute_client.regions().list.return_value = mock_regions_request

        loadbalancer_service._client = mock_compute_client

        with patch.object(loadbalancer_service._cache, "set") as mock_set:
            await loadbalancer_service.list_load_balancers("test-project", use_cache=False)

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "loadbalancer:test-project"
            # Second argument should be the load balancers list
            assert len(mock_set.call_args[0][1]) == 1


class TestGetLoadBalancerService:
    """Tests for get_loadbalancer_service function."""

    @pytest.mark.asyncio
    async def test_get_loadbalancer_service_creates_instance(self) -> None:
        """Test that get_loadbalancer_service creates a global instance."""
        service1 = await get_loadbalancer_service()
        service2 = await get_loadbalancer_service()

        assert service1 is service2
        assert isinstance(service1, LoadBalancerService)
