"""Unit tests for Compute Engine service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.compute import ComputeInstance, InstanceGroup
from sequel.services.compute import ComputeService, get_compute_service, reset_compute_service


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
def compute_service() -> ComputeService:
    """Create Compute service instance."""
    reset_compute_service()
    return ComputeService()


class TestComputeService:
    """Tests for ComputeService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, compute_service: ComputeService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Compute client."""
        with (
            patch("sequel.services.compute.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.compute.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await compute_service._get_client()

            mock_build.assert_called_once_with(
                "compute",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert compute_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, compute_service: ComputeService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        compute_service._client = mock_client

        client = await compute_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_instance_groups_success(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instance groups successfully."""
        mock_response = {
            "items": {
                "zones/us-central1-a": {
                    "instanceGroups": [
                        {
                            "name": "zonal-group",
                            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
                            "size": 3,
                            "creationTimestamp": "2023-01-01T00:00:00Z",
                        }
                    ]
                },
                "regions/us-central1": {
                    "instanceGroups": [
                        {
                            "name": "regional-group",
                            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-central1",
                            "size": 5,
                            "creationTimestamp": "2023-01-02T00:00:00Z",
                        }
                    ]
                },
            }
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.instanceGroups().aggregatedList.return_value = mock_request

        compute_service._client = mock_compute_client

        groups = await compute_service.list_instance_groups("test-project", use_cache=False)

        assert len(groups) == 2
        assert isinstance(groups[0], InstanceGroup)
        # Check that we have one zonal and one regional group
        group_names = {g.group_name for g in groups}
        assert "zonal-group" in group_names
        assert "regional-group" in group_names

    @pytest.mark.asyncio
    async def test_list_instance_groups_empty(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instance groups when none exist."""
        mock_response: dict[str, Any] = {"items": {}}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.instanceGroups().aggregatedList.return_value = mock_request

        compute_service._client = mock_compute_client

        groups = await compute_service.list_instance_groups("test-project", use_cache=False)

        assert len(groups) == 0

    @pytest.mark.asyncio
    async def test_list_instances_in_group_success(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instances in a zonal managed instance group."""
        # Mock managed instance references response (different format than unmanaged)
        mock_refs_response = {
            "managedInstances": [
                {"instance": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/instances/instance-1"},
                {"instance": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/instances/instance-2"},
            ]
        }

        # Mock instance details responses
        mock_instance_1 = {
            "name": "instance-1",
            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
            "status": "RUNNING",
            "machineType": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/machineTypes/n1-standard-1",
        }

        mock_instance_2 = {
            "name": "instance-2",
            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
            "status": "RUNNING",
            "machineType": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/machineTypes/n1-standard-1",
        }

        # Mock the API calls for managed instance groups
        mock_list_request = MagicMock()
        mock_list_request.execute = MagicMock(return_value=mock_refs_response)

        mock_get_request_1 = MagicMock()
        mock_get_request_1.execute = MagicMock(return_value=mock_instance_1)

        mock_get_request_2 = MagicMock()
        mock_get_request_2.execute = MagicMock(return_value=mock_instance_2)

        mock_compute_client.instanceGroupManagers().listManagedInstances.return_value = mock_list_request
        mock_compute_client.instances().get.side_effect = [mock_get_request_1, mock_get_request_2]

        compute_service._client = mock_compute_client

        instances = await compute_service.list_instances_in_group(
            "test-project", "us-central1-a", "test-group", use_cache=False
        )

        assert len(instances) == 2
        assert isinstance(instances[0], ComputeInstance)
        assert instances[0].name == "instance-1"
        assert instances[1].name == "instance-2"

    @pytest.mark.asyncio
    async def test_list_instances_in_regional_group_success(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instances in a regional managed instance group."""
        # Mock managed instance references response (different format than unmanaged)
        mock_refs_response = {
            "managedInstances": [
                {"instance": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/instances/regional-instance-1"},
                {"instance": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-b/instances/regional-instance-2"},
            ]
        }

        # Mock instance details responses
        mock_instance_1 = {
            "name": "regional-instance-1",
            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
            "status": "RUNNING",
            "machineType": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/machineTypes/n1-standard-1",
        }

        mock_instance_2 = {
            "name": "regional-instance-2",
            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-b",
            "status": "RUNNING",
            "machineType": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-b/machineTypes/n1-standard-1",
        }

        # Mock the API calls for managed instance groups
        mock_list_request = MagicMock()
        mock_list_request.execute = MagicMock(return_value=mock_refs_response)

        mock_get_request_1 = MagicMock()
        mock_get_request_1.execute = MagicMock(return_value=mock_instance_1)

        mock_get_request_2 = MagicMock()
        mock_get_request_2.execute = MagicMock(return_value=mock_instance_2)

        mock_compute_client.regionInstanceGroupManagers().listManagedInstances.return_value = mock_list_request
        mock_compute_client.instances().get.side_effect = [mock_get_request_1, mock_get_request_2]

        compute_service._client = mock_compute_client

        instances = await compute_service.list_instances_in_regional_group(
            "test-project", "us-central1", "test-regional-group", use_cache=False
        )

        assert len(instances) == 2
        assert isinstance(instances[0], ComputeInstance)
        assert instances[0].name == "regional-instance-1"
        assert instances[1].name == "regional-instance-2"
        # Verify instances are from different zones
        assert "us-central1-a" in instances[0].zone
        assert "us-central1-b" in instances[1].zone

    @pytest.mark.asyncio
    async def test_list_instances_in_group_empty(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instances when group is empty."""
        mock_response: dict[str, Any] = {"items": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.instanceGroups().listInstances.return_value = mock_request

        compute_service._client = mock_compute_client

        instances = await compute_service.list_instances_in_group(
            "test-project", "us-central1-a", "empty-group", use_cache=False
        )

        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_list_instances_in_group_error(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test error handling when listing instances."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_compute_client.instanceGroups().listInstances.return_value = mock_request

        compute_service._client = mock_compute_client

        instances = await compute_service.list_instances_in_group(
            "test-project", "us-central1-a", "test-group", use_cache=False
        )

        # Should return empty list on error
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_list_instances_in_regional_group_with_cache(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instances in regional group with caching."""
        mock_instance = ComputeInstance(
            id="instance-1",
            name="instance-1",
            instance_name="instance-1",
            zone="us-central1-a",
            status="RUNNING",
            machine_type="n1-standard-1",
        )

        with patch.object(compute_service._cache, "get", return_value=[mock_instance]):
            instances = await compute_service.list_instances_in_regional_group(
                "test-project", "us-central1", "test-group", use_cache=True
            )

            assert len(instances) == 1
            assert instances[0] == mock_instance

    @pytest.mark.asyncio
    async def test_list_instance_groups_with_cache(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instance groups with caching."""
        mock_group = InstanceGroup(
            id="group-1",
            name="Test Group",
            group_name="test-group",
            zone="us-central1-a",
            size=5,
            is_managed=True,
        )

        with patch.object(compute_service._cache, "get", return_value=[mock_group]):
            groups = await compute_service.list_instance_groups("test-project", use_cache=True)

            assert len(groups) == 1
            assert groups[0] == mock_group

    @pytest.mark.asyncio
    async def test_list_instance_groups_specific_zone(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instance groups in a specific zone."""
        mock_response = {
            "items": [
                {
                    "name": "zone-specific-group",
                    "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
                    "targetSize": 3,
                }
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.instanceGroupManagers().list.return_value = mock_request

        # Mock unmanaged groups (empty)
        mock_unmanaged_request = MagicMock()
        mock_unmanaged_request.execute = MagicMock(return_value={"items": []})
        mock_compute_client.instanceGroups().list.return_value = mock_unmanaged_request

        compute_service._client = mock_compute_client

        groups = await compute_service.list_instance_groups("test-project", zone="us-central1-a", use_cache=False)

        assert len(groups) == 1
        assert groups[0].group_name == "zone-specific-group"
        mock_compute_client.instanceGroupManagers().list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_instance_groups_error_handling(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test error handling when listing instance groups fails."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_compute_client.instanceGroupManagers().aggregatedList.return_value = mock_request
        mock_compute_client.instanceGroups().aggregatedList.return_value = mock_request

        compute_service._client = mock_compute_client

        # Should return empty list on error
        groups = await compute_service.list_instance_groups("test-project", use_cache=False)

        assert len(groups) == 0

    @pytest.mark.asyncio
    async def test_list_instance_groups_cache_set(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test that results are cached when use_cache=True."""
        mock_response = {
            "items": {
                "zones/us-central1-a": {
                    "instanceGroupManagers": [
                        {
                            "name": "test-group",
                            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
                            "targetSize": 1,
                        }
                    ]
                }
            }
        }

        mock_managed_request = MagicMock()
        mock_managed_request.execute = MagicMock(return_value=mock_response)
        mock_compute_client.instanceGroupManagers().aggregatedList.return_value = mock_managed_request

        mock_unmanaged_request = MagicMock()
        mock_unmanaged_request.execute = MagicMock(return_value={"items": {}})
        mock_compute_client.instanceGroups().aggregatedList.return_value = mock_unmanaged_request

        compute_service._client = mock_compute_client

        with patch.object(compute_service._cache, "set") as mock_cache_set:
            groups = await compute_service.list_instance_groups("test-project", use_cache=True)

            assert len(groups) == 1
            # Verify cache.set was called
            mock_cache_set.assert_called_once()
            # Verify the cached value is the groups list
            assert mock_cache_set.call_args[0][1] == groups

    @pytest.mark.asyncio
    async def test_list_instances_in_group_unmanaged(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instances in an unmanaged instance group."""
        mock_refs_response = {
            "items": [
                {"instance": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/instances/instance-1"},
            ]
        }

        mock_instance = {
            "name": "instance-1",
            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
            "status": "RUNNING",
            "machineType": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/machineTypes/n1-standard-1",
        }

        mock_list_request = MagicMock()
        mock_list_request.execute = MagicMock(return_value=mock_refs_response)

        mock_get_request = MagicMock()
        mock_get_request.execute = MagicMock(return_value=mock_instance)

        mock_compute_client.instanceGroups().listInstances.return_value = mock_list_request
        mock_compute_client.instances().get.return_value = mock_get_request

        compute_service._client = mock_compute_client

        instances = await compute_service.list_instances_in_group(
            "test-project", "us-central1-a", "unmanaged-group", is_managed=False, use_cache=False
        )

        assert len(instances) == 1
        assert instances[0].name == "instance-1"
        mock_compute_client.instanceGroups().listInstances.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_instances_in_regional_group_unmanaged(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test listing instances in an unmanaged regional instance group."""
        mock_refs_response = {
            "items": [
                {"instance": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/instances/regional-instance-1"},
            ]
        }

        mock_instance = {
            "name": "regional-instance-1",
            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
            "status": "RUNNING",
            "machineType": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/machineTypes/n1-standard-1",
        }

        mock_list_request = MagicMock()
        mock_list_request.execute = MagicMock(return_value=mock_refs_response)

        mock_get_request = MagicMock()
        mock_get_request.execute = MagicMock(return_value=mock_instance)

        mock_compute_client.regionInstanceGroups().listInstances.return_value = mock_list_request
        mock_compute_client.instances().get.return_value = mock_get_request

        compute_service._client = mock_compute_client

        instances = await compute_service.list_instances_in_regional_group(
            "test-project", "us-central1", "unmanaged-regional-group", is_managed=False, use_cache=False
        )

        assert len(instances) == 1
        assert instances[0].name == "regional-instance-1"
        mock_compute_client.regionInstanceGroups().listInstances.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_instances_in_regional_group_error_extracting_zone(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test error handling when zone cannot be extracted from instance URL."""
        mock_refs_response = {
            "managedInstances": [
                {"instance": "invalid-url-without-zones"},
            ]
        }

        mock_list_request = MagicMock()
        mock_list_request.execute = MagicMock(return_value=mock_refs_response)

        mock_compute_client.regionInstanceGroupManagers().listManagedInstances.return_value = mock_list_request

        compute_service._client = mock_compute_client

        instances = await compute_service.list_instances_in_regional_group(
            "test-project", "us-central1", "test-group", use_cache=False
        )

        # Should skip instances with invalid URLs
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_list_instances_cache_set(
        self, compute_service: ComputeService, mock_compute_client: MagicMock
    ) -> None:
        """Test that instance results are cached."""
        mock_refs_response = {
            "managedInstances": [
                {"instance": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/instances/instance-1"},
            ]
        }

        mock_instance = {
            "name": "instance-1",
            "zone": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a",
            "status": "RUNNING",
            "machineType": "https://www.googleapis.com/compute/v1/projects/test-project/zones/us-central1-a/machineTypes/n1-standard-1",
        }

        mock_list_request = MagicMock()
        mock_list_request.execute = MagicMock(return_value=mock_refs_response)

        mock_get_request = MagicMock()
        mock_get_request.execute = MagicMock(return_value=mock_instance)

        mock_compute_client.instanceGroupManagers().listManagedInstances.return_value = mock_list_request
        mock_compute_client.instances().get.return_value = mock_get_request

        compute_service._client = mock_compute_client

        with patch.object(compute_service._cache, "set") as mock_cache_set:
            instances = await compute_service.list_instances_in_group(
                "test-project", "us-central1-a", "test-group", use_cache=True
            )

            assert len(instances) == 1
            # Verify cache.set was called
            mock_cache_set.assert_called_once()
            assert mock_cache_set.call_args[0][1] == instances


class TestGetComputeService:
    """Tests for get_compute_service function."""

    @pytest.mark.asyncio
    async def test_get_compute_service_creates_instance(self) -> None:
        """Test that get_compute_service creates a global instance."""
        reset_compute_service()

        service1 = await get_compute_service()
        service2 = await get_compute_service()

        assert service1 is service2
        assert isinstance(service1, ComputeService)

    @pytest.mark.asyncio
    async def test_reset_compute_service(self) -> None:
        """Test that reset_compute_service clears the global instance."""
        service1 = await get_compute_service()
        reset_compute_service()
        service2 = await get_compute_service()

        assert service1 is not service2
