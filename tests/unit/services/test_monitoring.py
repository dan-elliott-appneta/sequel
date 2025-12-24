"""Unit tests for Monitoring service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.monitoring import AlertPolicy
from sequel.services.monitoring import (
    MonitoringService,
    get_monitoring_service,
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
def mock_monitoring_client() -> MagicMock:
    """Create mock Cloud Monitoring API client."""
    return MagicMock()


@pytest.fixture
def monitoring_service() -> MonitoringService:
    """Create Monitoring service instance."""
    return MonitoringService()


class TestMonitoringService:
    """Tests for MonitoringService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, monitoring_service: MonitoringService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Cloud Monitoring client."""
        with (
            patch("sequel.services.monitoring.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.monitoring.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await monitoring_service._get_client()

            mock_build.assert_called_once_with(
                "monitoring",
                "v3",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert monitoring_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, monitoring_service: MonitoringService
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        monitoring_service._client = mock_client

        client = await monitoring_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_alert_policies_success(
        self, monitoring_service: MonitoringService, mock_monitoring_client: MagicMock
    ) -> None:
        """Test listing alert policies successfully."""
        mock_response = {
            "alertPolicies": [
                {
                    "name": "projects/test-project/alertPolicies/1234567890",
                    "displayName": "High CPU Usage",
                    "enabled": True,
                    "conditions": [
                        {
                            "name": "projects/test-project/alertPolicies/1234567890/conditions/5678",
                            "displayName": "CPU usage above 80%",
                            "conditionThreshold": {
                                "filter": 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
                                "comparison": "COMPARISON_GT",
                                "thresholdValue": 0.8,
                                "duration": "60s",
                            },
                        }
                    ],
                    "combiner": "OR",
                    "notificationChannels": [
                        "projects/test-project/notificationChannels/9876543210",
                        "projects/test-project/notificationChannels/9876543211",
                    ],
                    "documentation": {
                        "content": "Check the instance and consider scaling.",
                        "mimeType": "text/markdown",
                    },
                },
                {
                    "name": "projects/test-project/alertPolicies/9999999999",
                    "displayName": "Low Disk Space",
                    "enabled": False,
                    "conditions": [
                        {
                            "name": "projects/test-project/alertPolicies/9999999999/conditions/1111",
                            "displayName": "Disk usage above 90%",
                        }
                    ],
                    "combiner": "AND",
                    "notificationChannels": [
                        "projects/test-project/notificationChannels/3333333333",
                    ],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_monitoring_client.projects().alertPolicies().list.return_value = mock_request

        monitoring_service._client = mock_monitoring_client

        policies = await monitoring_service.list_alert_policies("test-project", use_cache=False)

        assert len(policies) == 2
        assert isinstance(policies[0], AlertPolicy)
        assert policies[0].policy_name == "1234567890"
        assert policies[0].display_name == "High CPU Usage"
        assert policies[0].enabled is True
        assert policies[0].condition_count == 1
        assert policies[0].notification_channel_count == 2
        assert policies[1].policy_name == "9999999999"
        assert policies[1].display_name == "Low Disk Space"
        assert policies[1].enabled is False

    @pytest.mark.asyncio
    async def test_list_alert_policies_empty(
        self, monitoring_service: MonitoringService, mock_monitoring_client: MagicMock
    ) -> None:
        """Test listing policies when none exist."""
        mock_response: dict[str, Any] = {"alertPolicies": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_monitoring_client.projects().alertPolicies().list.return_value = mock_request

        monitoring_service._client = mock_monitoring_client

        policies = await monitoring_service.list_alert_policies("test-project", use_cache=False)

        assert len(policies) == 0

    @pytest.mark.asyncio
    async def test_list_alert_policies_no_alert_policies_key(
        self, monitoring_service: MonitoringService, mock_monitoring_client: MagicMock
    ) -> None:
        """Test listing policies when response has no alertPolicies key."""
        mock_response: dict[str, Any] = {}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_monitoring_client.projects().alertPolicies().list.return_value = mock_request

        monitoring_service._client = mock_monitoring_client

        policies = await monitoring_service.list_alert_policies("test-project", use_cache=False)

        assert len(policies) == 0

    @pytest.mark.asyncio
    async def test_list_alert_policies_error(
        self, monitoring_service: MonitoringService, mock_monitoring_client: MagicMock
    ) -> None:
        """Test error handling when listing policies."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_monitoring_client.projects().alertPolicies().list.return_value = mock_request

        monitoring_service._client = mock_monitoring_client

        policies = await monitoring_service.list_alert_policies("test-project", use_cache=False)

        # Should return empty list on error
        assert len(policies) == 0

    @pytest.mark.asyncio
    async def test_list_alert_policies_with_cache(
        self, monitoring_service: MonitoringService
    ) -> None:
        """Test listing policies with caching."""
        mock_policy = AlertPolicy(
            id="cached-policy",
            name="cached-policy",
            policy_name="cached-policy",
            display_name="Cached Alert",
            condition_count=1,
        )

        with patch.object(monitoring_service._cache, "get", return_value=[mock_policy]):
            policies = await monitoring_service.list_alert_policies("test-project", use_cache=True)

            assert len(policies) == 1
            assert policies[0] == mock_policy

    @pytest.mark.asyncio
    async def test_list_alert_policies_disabled(
        self, monitoring_service: MonitoringService, mock_monitoring_client: MagicMock
    ) -> None:
        """Test listing disabled alert policies."""
        mock_response = {
            "alertPolicies": [
                {
                    "name": "projects/test-project/alertPolicies/disabled-alert",
                    "displayName": "Disabled Alert",
                    "enabled": False,
                    "conditions": [],
                    "notificationChannels": [],
                }
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_monitoring_client.projects().alertPolicies().list.return_value = mock_request

        monitoring_service._client = mock_monitoring_client

        policies = await monitoring_service.list_alert_policies("test-project", use_cache=False)

        assert len(policies) == 1
        assert policies[0].enabled is False

    @pytest.mark.asyncio
    async def test_list_alert_policies_multiple_conditions(
        self, monitoring_service: MonitoringService, mock_monitoring_client: MagicMock
    ) -> None:
        """Test listing policies with multiple conditions."""
        mock_response = {
            "alertPolicies": [
                {
                    "name": "projects/test-project/alertPolicies/multi-condition",
                    "displayName": "Multi-Condition Alert",
                    "enabled": True,
                    "conditions": [
                        {"name": "condition1"},
                        {"name": "condition2"},
                        {"name": "condition3"},
                    ],
                    "combiner": "AND",
                    "notificationChannels": [],
                }
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_monitoring_client.projects().alertPolicies().list.return_value = mock_request

        monitoring_service._client = mock_monitoring_client

        policies = await monitoring_service.list_alert_policies("test-project", use_cache=False)

        assert len(policies) == 1
        assert policies[0].condition_count == 3
        assert policies[0].combiner == "AND"

    @pytest.mark.asyncio
    async def test_list_alert_policies_project_id_format(
        self, monitoring_service: MonitoringService, mock_monitoring_client: MagicMock
    ) -> None:
        """Test that project ID is correctly formatted in API call."""
        mock_response: dict[str, Any] = {"alertPolicies": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_monitoring_client.projects().alertPolicies().list.return_value = mock_request

        monitoring_service._client = mock_monitoring_client

        await monitoring_service.list_alert_policies("my-project-123", use_cache=False)

        # Verify the API was called with correct parent format
        mock_monitoring_client.projects().alertPolicies().list.assert_called_once_with(
            name="projects/my-project-123"
        )


class TestGetMonitoringService:
    """Tests for get_monitoring_service function."""

    @pytest.mark.asyncio
    async def test_get_monitoring_service_singleton(self) -> None:
        """Test that get_monitoring_service returns singleton."""
        # Reset the singleton
        import sequel.services.monitoring

        sequel.services.monitoring._monitoring_service = None

        service1 = await get_monitoring_service()
        service2 = await get_monitoring_service()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_get_monitoring_service_returns_instance(self) -> None:
        """Test that get_monitoring_service returns MonitoringService instance."""
        service = await get_monitoring_service()

        assert isinstance(service, MonitoringService)
