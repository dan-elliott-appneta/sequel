"""Unit tests for Networks models."""

from typing import Any

from sequel.models.networks import Subnet, VPCNetwork


class TestVPCNetwork:
    """Tests for VPCNetwork model."""

    def test_create_network(self) -> None:
        """Test creating a VPC network instance."""
        network = VPCNetwork(
            id="my-network",
            name="my-network",
            network_name="my-network",
            mode="CUSTOM",
            subnet_count=3,
            mtu=1460,
            auto_create_subnets=False,
            routing_mode="REGIONAL",
        )

        assert network.id == "my-network"
        assert network.network_name == "my-network"
        assert network.mode == "CUSTOM"
        assert network.subnet_count == 3
        assert network.mtu == 1460
        assert network.auto_create_subnets is False
        assert network.routing_mode == "REGIONAL"

    def test_from_api_response_full(self) -> None:
        """Test creating network from full API response."""
        data = {
            "name": "production-vpc",
            "id": "1234567890",
            "creationTimestamp": "2023-01-01T00:00:00.000-08:00",
            "autoCreateSubnetworks": False,
            "subnetworks": [
                "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1/subnetworks/subnet-1",
                "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-east1/subnetworks/subnet-2",
                "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/subnetworks/subnet-3",
            ],
            "routingConfig": {
                "routingMode": "REGIONAL"
            },
            "mtu": 1500,
            "selfLink": "https://www.googleapis.com/compute/v1/projects/my-project/global/networks/production-vpc"
        }

        network = VPCNetwork.from_api_response(data)

        assert network.network_name == "production-vpc"
        assert network.project_id == "my-project"
        assert network.mode == "CUSTOM"
        assert network.subnet_count == 3
        assert network.mtu == 1500
        assert network.auto_create_subnets is False
        assert network.routing_mode == "REGIONAL"
        assert network.created_at is not None
        assert network.raw_data == data

    def test_from_api_response_auto_mode(self) -> None:
        """Test creating network with auto mode."""
        data = {
            "name": "default",
            "autoCreateSubnetworks": True,
            "routingConfig": {
                "routingMode": "GLOBAL"
            },
            "mtu": 1460,
        }

        network = VPCNetwork.from_api_response(data)

        assert network.network_name == "default"
        assert network.mode == "AUTO"
        assert network.auto_create_subnets is True
        assert network.routing_mode == "GLOBAL"
        assert network.mtu == 1460

    def test_from_api_response_minimal(self) -> None:
        """Test creating network from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-network",
        }

        network = VPCNetwork.from_api_response(data)

        assert network.network_name == "minimal-network"
        assert network.mode == "CUSTOM"  # Default when autoCreateSubnetworks is missing/false
        assert network.subnet_count == 0
        assert network.mtu == 1460  # Default
        assert network.auto_create_subnets is False
        assert network.routing_mode is None
        assert network.project_id is None
        assert network.created_at is None


class TestSubnet:
    """Tests for Subnet model."""

    def test_create_subnet(self) -> None:
        """Test creating a subnet instance."""
        subnet = Subnet(
            id="us-central1:my-subnet",
            name="my-subnet",
            subnet_name="my-subnet",
            network_name="my-network",
            region="us-central1",
            ip_cidr_range="10.0.0.0/24",
            gateway_address="10.0.0.1",
            private_ip_google_access=True,
            enable_flow_logs=True,
            purpose="PRIVATE",
        )

        assert subnet.id == "us-central1:my-subnet"
        assert subnet.subnet_name == "my-subnet"
        assert subnet.network_name == "my-network"
        assert subnet.region == "us-central1"
        assert subnet.ip_cidr_range == "10.0.0.0/24"
        assert subnet.gateway_address == "10.0.0.1"
        assert subnet.private_ip_google_access is True
        assert subnet.enable_flow_logs is True
        assert subnet.purpose == "PRIVATE"

    def test_from_api_response_full(self) -> None:
        """Test creating subnet from full API response."""
        data = {
            "name": "production-subnet",
            "id": "9876543210",
            "creationTimestamp": "2023-01-01T00:00:00.000-08:00",
            "network": "https://www.googleapis.com/compute/v1/projects/my-project/global/networks/production-vpc",
            "ipCidrRange": "10.128.0.0/20",
            "gatewayAddress": "10.128.0.1",
            "region": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1",
            "privateIpGoogleAccess": True,
            "enableFlowLogs": True,
            "purpose": "PRIVATE",
            "selfLink": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1/subnetworks/production-subnet"
        }

        subnet = Subnet.from_api_response(data)

        assert subnet.subnet_name == "production-subnet"
        assert subnet.network_name == "production-vpc"
        assert subnet.region == "us-central1"
        assert subnet.ip_cidr_range == "10.128.0.0/20"
        assert subnet.gateway_address == "10.128.0.1"
        assert subnet.private_ip_google_access is True
        assert subnet.enable_flow_logs is True
        assert subnet.purpose == "PRIVATE"
        assert subnet.project_id == "my-project"
        assert subnet.created_at is not None
        assert subnet.id == "us-central1:production-subnet"
        assert subnet.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating subnet from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-subnet",
        }

        subnet = Subnet.from_api_response(data)

        assert subnet.subnet_name == "minimal-subnet"
        assert subnet.network_name is None
        assert subnet.region is None
        assert subnet.ip_cidr_range is None
        assert subnet.gateway_address is None
        assert subnet.private_ip_google_access is False
        assert subnet.enable_flow_logs is False
        assert subnet.purpose is None
        assert subnet.project_id is None
        assert subnet.created_at is None
        assert subnet.id == "minimal-subnet"  # No region, so just the name

    def test_from_api_response_without_private_google_access(self) -> None:
        """Test creating subnet without private Google access."""
        data = {
            "name": "no-private-access-subnet",
            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/default",
            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/us-west1",
            "privateIpGoogleAccess": False,
        }

        subnet = Subnet.from_api_response(data)

        assert subnet.subnet_name == "no-private-access-subnet"
        assert subnet.network_name == "default"
        assert subnet.region == "us-west1"
        assert subnet.private_ip_google_access is False

    def test_from_api_response_without_flow_logs(self) -> None:
        """Test creating subnet without flow logs."""
        data = {
            "name": "no-flow-logs-subnet",
            "network": "https://www.googleapis.com/compute/v1/projects/test-project/global/networks/default",
            "region": "https://www.googleapis.com/compute/v1/projects/test-project/regions/europe-west1",
            "enableFlowLogs": False,
        }

        subnet = Subnet.from_api_response(data)

        assert subnet.subnet_name == "no-flow-logs-subnet"
        assert subnet.network_name == "default"
        assert subnet.region == "europe-west1"
        assert subnet.enable_flow_logs is False
