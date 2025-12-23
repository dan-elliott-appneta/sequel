"""Integration tests for network resources (firewalls and load balancers).

These tests verify that firewall policies and load balancers work correctly
through the full stack from service layer through state management.
"""

from unittest.mock import MagicMock, patch

import pytest

from sequel.cache.memory import reset_cache
from sequel.services.auth import reset_auth_manager
from sequel.state.resource_state import get_resource_state, reset_resource_state


@pytest.fixture(autouse=True)
def reset_all_services():
    """Reset all service singletons before each test."""
    reset_auth_manager()
    reset_cache()
    reset_resource_state()
    yield
    # Cleanup after test
    reset_auth_manager()
    reset_cache()
    reset_resource_state()


@pytest.fixture
def mock_gcp_credentials():
    """Mock Google Cloud credentials."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh = MagicMock()
    return creds


@pytest.fixture
def mock_firewall_data():
    """Mock firewall policies API response."""
    return {
        "items": [
            {
                "name": "allow-ssh",
                "description": "Allow SSH from anywhere",
                "network": "projects/test-project/global/networks/default",
                "priority": 1000,
                "direction": "INGRESS",
                "disabled": False,
                "sourceRanges": ["0.0.0.0/0"],
                "allowed": [
                    {"IPProtocol": "tcp", "ports": ["22"]}
                ],
                "creationTimestamp": "2024-01-01T00:00:00.000-00:00",
            },
            {
                "name": "allow-https",
                "description": "Allow HTTPS",
                "network": "projects/test-project/global/networks/default",
                "priority": 1000,
                "direction": "INGRESS",
                "disabled": False,
                "allowed": [
                    {"IPProtocol": "tcp", "ports": ["443"]}
                ],
                "creationTimestamp": "2024-01-02T00:00:00.000-00:00",
            },
            {
                "name": "deny-all",
                "description": "Deny all traffic",
                "network": "projects/test-project/global/networks/default",
                "priority": 65535,
                "direction": "INGRESS",
                "disabled": True,
                "denied": [
                    {"IPProtocol": "all"}
                ],
                "creationTimestamp": "2024-01-03T00:00:00.000-00:00",
            },
        ]
    }


@pytest.fixture
def mock_loadbalancer_data_global():
    """Mock global load balancers API response."""
    return {
        "items": [
            {
                "name": "global-https-lb",
                "description": "Global HTTPS load balancer",
                "IPAddress": "35.201.1.1",
                "IPProtocol": "TCP",
                "portRange": "443-443",
                "target": "projects/test-project/global/targetHttpProxies/https-proxy",
                "loadBalancingScheme": "EXTERNAL",
                "networkTier": "PREMIUM",
                "creationTimestamp": "2024-01-01T00:00:00.000-00:00",
            },
        ]
    }


@pytest.fixture
def mock_loadbalancer_data_regional():
    """Mock regional load balancers API response."""
    return {
        "items": [
            {
                "name": "regional-internal-lb",
                "description": "Internal load balancer",
                "IPAddress": "10.0.0.5",
                "IPProtocol": "TCP",
                "portRange": "80-80",
                "target": "projects/test-project/regions/us-central1/targetPools/internal-pool",
                "loadBalancingScheme": "INTERNAL",
                "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                "creationTimestamp": "2024-01-02T00:00:00.000-00:00",
            },
        ]
    }


@pytest.fixture
def mock_regions_data():
    """Mock regions API response."""
    return {
        "items": [
            {"name": "us-central1"},
            {"name": "us-east1"},
        ]
    }


@pytest.mark.asyncio
@pytest.mark.integration
async def test_load_firewall_policies_through_state(
    mock_gcp_credentials,
    mock_firewall_data,
):
    """Test loading firewall policies through resource state layer.

    This verifies:
    1. Service can fetch firewall policies from GCP API
    2. State layer correctly stores and retrieves policies
    3. Caching works properly
    4. Model conversion works correctly
    """
    from sequel.services.auth import get_auth_manager

    # Mock authentication
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        auth_manager = await get_auth_manager()
        assert auth_manager.credentials.valid

    # Mock Compute API for firewall listing
    with patch("sequel.services.firewall.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_firewall_data)
        mock_client.firewalls().list.return_value = mock_request

        # Load firewalls through state layer
        state = get_resource_state()
        firewalls = await state.load_firewalls("test-project", force_refresh=False)

        # Verify we got the correct number of policies
        assert len(firewalls) == 3

        # Verify model conversion worked
        assert firewalls[0].policy_name == "allow-ssh"
        assert firewalls[0].description == "Allow SSH from anywhere"
        assert firewalls[0].priority == 1000
        assert firewalls[0].direction == "INGRESS"
        assert firewalls[0].disabled is False
        assert firewalls[0].rule_count == 1
        assert firewalls[0].is_enabled() is True

        assert firewalls[1].policy_name == "allow-https"
        assert firewalls[1].rule_count == 1

        assert firewalls[2].policy_name == "deny-all"
        assert firewalls[2].disabled is True
        assert firewalls[2].is_enabled() is False

        # Verify state caching works
        assert state.is_loaded("test-project", "firewalls")
        cached_firewalls = state.get_firewalls("test-project")
        assert len(cached_firewalls) == 3
        assert cached_firewalls[0].policy_name == "allow-ssh"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_load_loadbalancers_through_state(
    mock_gcp_credentials,
    mock_loadbalancer_data_global,
    mock_loadbalancer_data_regional,
    mock_regions_data,
):
    """Test loading load balancers through resource state layer.

    This verifies:
    1. Service can fetch both global and regional load balancers
    2. State layer correctly aggregates and stores LBs
    3. Caching works properly
    4. Model conversion works correctly for both types
    """
    from sequel.services.auth import get_auth_manager

    # Mock authentication
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "test-project")
        auth_manager = await get_auth_manager()
        assert auth_manager.credentials.valid

    # Mock Compute API for load balancer listing
    with patch("sequel.services.loadbalancer.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client

        # Mock global forwarding rules
        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_loadbalancer_data_global)
        mock_client.globalForwardingRules().list.return_value = mock_global_request

        # Mock regions list
        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value=mock_regions_data)
        mock_client.regions().list.return_value = mock_regions_request

        # Mock regional forwarding rules - return empty for first region, data for second
        mock_regional_request1 = MagicMock()
        mock_regional_request1.execute = MagicMock(return_value={"items": []})
        mock_regional_request2 = MagicMock()
        mock_regional_request2.execute = MagicMock(return_value=mock_loadbalancer_data_regional)

        mock_client.forwardingRules().list.side_effect = [
            mock_regional_request1,
            mock_regional_request2,
        ]

        # Load load balancers through state layer
        state = get_resource_state()
        lbs = await state.load_loadbalancers("test-project", force_refresh=False)

        # Verify we got both global and regional LBs
        assert len(lbs) == 2

        # Verify global LB
        global_lb = next(lb for lb in lbs if lb.lb_name == "global-https-lb")
        assert global_lb.description == "Global HTTPS load balancer"
        assert global_lb.ip_address == "35.201.1.1"
        assert global_lb.protocol == "TCP"
        assert global_lb.port_range == "443-443"
        assert global_lb.load_balancing_scheme == "EXTERNAL"
        assert global_lb.network_tier == "PREMIUM"
        assert global_lb.is_external() is True
        assert global_lb.region is None  # Global LBs don't have region

        # Verify regional LB
        regional_lb = next(lb for lb in lbs if lb.lb_name == "regional-internal-lb")
        assert regional_lb.description == "Internal load balancer"
        assert regional_lb.ip_address == "10.0.0.5"
        assert regional_lb.load_balancing_scheme == "INTERNAL"
        assert regional_lb.region == "us-central1"
        assert regional_lb.is_external() is False

        # Verify state caching works
        assert state.is_loaded("test-project", "loadbalancers")
        cached_lbs = state.get_loadbalancers("test-project")
        assert len(cached_lbs) == 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_firewall_state_caching(
    mock_gcp_credentials,
    mock_firewall_data,
):
    """Test that state layer caching works correctly for firewalls."""
    from sequel.services.auth import get_auth_manager

    # Mock authentication
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "cache-test-project")
        await get_auth_manager()

    with patch("sequel.services.firewall.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_firewall_data)
        mock_client.firewalls().list.return_value = mock_request

        state = get_resource_state()

        # First load - loads from API
        firewalls1 = await state.load_firewalls("cache-test-project", force_refresh=False)
        assert len(firewalls1) == 3

        # Second load - should return from state cache (not call API again)
        firewalls2 = await state.load_firewalls("cache-test-project", force_refresh=False)
        assert len(firewalls2) == 3
        assert firewalls2 is firewalls1  # Should be same cached list from state

        # Verify state tracking works
        assert state.is_loaded("cache-test-project", "firewalls")
        cached = state.get_firewalls("cache-test-project")
        assert len(cached) == 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_loadbalancer_state_caching(
    mock_gcp_credentials,
    mock_loadbalancer_data_global,
):
    """Test that state layer caching works correctly for load balancers."""
    from sequel.services.auth import get_auth_manager

    # Mock authentication
    with patch("google.auth.default") as mock_auth_default:
        mock_auth_default.return_value = (mock_gcp_credentials, "lb-cache-test-project")
        await get_auth_manager()

    with patch("sequel.services.loadbalancer.discovery.build") as mock_discovery:
        mock_client = MagicMock()
        mock_discovery.return_value = mock_client

        mock_global_request = MagicMock()
        mock_global_request.execute = MagicMock(return_value=mock_loadbalancer_data_global)
        mock_client.globalForwardingRules().list.return_value = mock_global_request

        # Mock regions
        mock_regions_request = MagicMock()
        mock_regions_request.execute = MagicMock(return_value={"items": []})
        mock_client.regions().list.return_value = mock_regions_request

        state = get_resource_state()

        # First load - loads from API
        lbs1 = await state.load_loadbalancers("lb-cache-test-project", force_refresh=False)
        assert len(lbs1) == 1

        # Second load - should return from state cache (not call API again)
        lbs2 = await state.load_loadbalancers("lb-cache-test-project", force_refresh=False)
        assert len(lbs2) == 1
        assert lbs2 is lbs1  # Should be same cached list from state

        # Verify state tracking works
        assert state.is_loaded("lb-cache-test-project", "loadbalancers")
        cached = state.get_loadbalancers("lb-cache-test-project")
        assert len(cached) == 1


