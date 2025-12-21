"""Unit tests for Compute Engine models."""

from typing import Any

from sequel.models.compute import ComputeInstance, InstanceGroup


class TestComputeInstance:
    """Tests for ComputeInstance model."""

    def test_create_compute_instance(self) -> None:
        """Test creating a Compute instance."""
        instance = ComputeInstance(
            id="instance-1",
            name="instance-1",
            instance_name="instance-1",
            instance_id="12345",
            zone="us-central1-a",
            machine_type="n1-standard-1",
            status="RUNNING",
            internal_ip="10.0.0.1",
            external_ip="35.192.0.1",
        )

        assert instance.id == "instance-1"
        assert instance.instance_name == "instance-1"
        assert instance.instance_id == "12345"
        assert instance.zone == "us-central1-a"
        assert instance.machine_type == "n1-standard-1"
        assert instance.status == "RUNNING"
        assert instance.internal_ip == "10.0.0.1"
        assert instance.external_ip == "35.192.0.1"

    def test_from_api_response_full(self) -> None:
        """Test creating instance from full API response."""
        data = {
            "name": "my-instance",
            "id": "1234567890",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "machineType": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a/machineTypes/n1-standard-1",
            "status": "RUNNING",
            "networkInterfaces": [
                {
                    "networkIP": "10.128.0.2",
                    "accessConfigs": [
                        {
                            "natIP": "35.192.0.1",
                        }
                    ],
                }
            ],
            "creationTimestamp": "2023-01-01T00:00:00.000-08:00",
        }

        instance = ComputeInstance.from_api_response(data)

        assert instance.instance_name == "my-instance"
        assert instance.instance_id == "1234567890"
        assert instance.zone == "us-central1-a"
        assert instance.machine_type == "n1-standard-1"
        assert instance.status == "RUNNING"
        assert instance.internal_ip == "10.128.0.2"
        assert instance.external_ip == "35.192.0.1"
        assert instance.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating instance from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-instance",
        }

        instance = ComputeInstance.from_api_response(data)

        assert instance.instance_name == "minimal-instance"
        assert instance.instance_id is None
        assert instance.zone is None
        assert instance.machine_type is None
        assert instance.status is None
        assert instance.internal_ip is None
        assert instance.external_ip is None

    def test_from_api_response_no_external_ip(self) -> None:
        """Test creating instance without external IP."""
        data = {
            "name": "private-instance",
            "networkInterfaces": [
                {
                    "networkIP": "10.128.0.5",
                }
            ],
        }

        instance = ComputeInstance.from_api_response(data)

        assert instance.internal_ip == "10.128.0.5"
        assert instance.external_ip is None

    def test_is_running_true(self) -> None:
        """Test is_running when instance is running."""
        instance = ComputeInstance(
            id="instance",
            name="instance",
            instance_name="instance",
            status="RUNNING",
        )

        assert instance.is_running() is True

    def test_is_running_false(self) -> None:
        """Test is_running when instance is not running."""
        instance = ComputeInstance(
            id="instance",
            name="instance",
            instance_name="instance",
            status="TERMINATED",
        )

        assert instance.is_running() is False


class TestInstanceGroup:
    """Tests for InstanceGroup model."""

    def test_create_instance_group(self) -> None:
        """Test creating an instance group."""
        group = InstanceGroup(
            id="group-1",
            name="group-1",
            group_name="group-1",
            zone="us-central1-a",
            size=5,
            is_managed=True,
        )

        assert group.id == "group-1"
        assert group.group_name == "group-1"
        assert group.zone == "us-central1-a"
        assert group.size == 5
        assert group.is_managed is True

    def test_from_api_response_zonal(self) -> None:
        """Test creating instance group from zonal group API response."""
        data = {
            "name": "my-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "size": 10,
            "kind": "compute#instanceGroupManager",
            "creationTimestamp": "2023-01-01T00:00:00.000-08:00",
        }

        group = InstanceGroup.from_api_response(data)

        assert group.group_name == "my-group"
        assert group.zone == "us-central1-a"
        assert group.size == 10
        assert group.is_managed is True
        assert group.raw_data == data

    def test_from_api_response_regional(self) -> None:
        """Test creating instance group from regional group API response."""
        data = {
            "name": "regional-group",
            "region": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1",
            "size": 15,
            "kind": "compute#regionInstanceGroupManager",
            "creationTimestamp": "2023-01-02T00:00:00.000-08:00",
        }

        group = InstanceGroup.from_api_response(data)

        assert group.group_name == "regional-group"
        assert group.region == "us-central1"  # Region extracted from region URL
        assert group.zone is None  # Regional groups don't have a zone
        assert group.size == 15
        assert group.is_managed is True

    def test_from_api_response_unmanaged(self) -> None:
        """Test creating unmanaged instance group."""
        data = {
            "name": "unmanaged-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-west1-a",
            "size": 3,
            "kind": "compute#instanceGroup",
        }

        group = InstanceGroup.from_api_response(data, is_managed=False)

        assert group.group_name == "unmanaged-group"
        assert group.is_managed is False

    def test_from_api_response_minimal(self) -> None:
        """Test creating instance group from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-group",
        }

        group = InstanceGroup.from_api_response(data)

        assert group.group_name == "minimal-group"
        assert group.zone is None
        assert group.size == 0
        assert group.is_managed is True  # Default is True
