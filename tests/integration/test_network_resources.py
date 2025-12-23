"""Integration tests for network resources (firewalls).

These tests verify that firewall policies work correctly
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


