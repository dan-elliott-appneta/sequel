"""Unit tests for LoadBalancer models."""

from typing import Any

from sequel.models.loadbalancer import LoadBalancer


class TestLoadBalancer:
    """Tests for LoadBalancer model."""

    def test_create_loadbalancer(self) -> None:
        """Test creating a load balancer instance."""
        lb = LoadBalancer(
            id="my-lb",
            name="my-lb",
            lb_name="my-lb",
            description="Production load balancer",
            ip_address="34.120.1.1",
            port_range="80-80",
            protocol="TCP",
            load_balancing_scheme="EXTERNAL",
            region="us-central1",
            network_tier="PREMIUM",
        )

        assert lb.id == "my-lb"
        assert lb.lb_name == "my-lb"
        assert lb.description == "Production load balancer"
        assert lb.ip_address == "34.120.1.1"
        assert lb.port_range == "80-80"
        assert lb.protocol == "TCP"
        assert lb.load_balancing_scheme == "EXTERNAL"
        assert lb.region == "us-central1"
        assert lb.network_tier == "PREMIUM"

    def test_from_api_response_full(self) -> None:
        """Test creating load balancer from full API response."""
        data = {
            "name": "my-lb",
            "description": "Production load balancer",
            "IPAddress": "34.120.1.1",
            "IPProtocol": "TCP",
            "portRange": "80-80",
            "target": "projects/my-project/regions/us-central1/targetPools/my-pool",
            "loadBalancingScheme": "EXTERNAL",
            "networkTier": "PREMIUM",
            "region": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1",
            "creationTimestamp": "2023-01-01T00:00:00.000-00:00",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.lb_name == "my-lb"
        assert lb.description == "Production load balancer"
        assert lb.ip_address == "34.120.1.1"
        assert lb.protocol == "TCP"
        assert lb.port_range == "80-80"
        assert lb.load_balancing_scheme == "EXTERNAL"
        assert lb.network_tier == "PREMIUM"
        assert lb.region == "us-central1"
        assert lb.project_id == "my-project"
        assert lb.created_at is not None
        assert lb.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating load balancer from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-lb",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.lb_name == "minimal-lb"
        assert lb.description is None
        assert lb.ip_address is None
        assert lb.protocol is None
        assert lb.port_range is None
        assert lb.load_balancing_scheme is None
        assert lb.region is None
        assert lb.network_tier is None
        assert lb.project_id is None
        assert lb.created_at is None

    def test_from_api_response_regional(self) -> None:
        """Test creating regional load balancer."""
        data = {
            "name": "regional-lb",
            "IPAddress": "10.0.0.5",
            "loadBalancingScheme": "INTERNAL",
            "region": "us-west1",
            "target": "projects/test-project/regions/us-west1/targetPools/pool",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.lb_name == "regional-lb"
        assert lb.load_balancing_scheme == "INTERNAL"
        assert lb.region == "us-west1"
        assert lb.project_id == "test-project"

    def test_from_api_response_global(self) -> None:
        """Test creating global load balancer."""
        data = {
            "name": "global-lb",
            "IPAddress": "35.201.1.1",
            "loadBalancingScheme": "EXTERNAL",
            "target": "projects/my-project/global/targetHttpProxies/my-proxy",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.lb_name == "global-lb"
        assert lb.load_balancing_scheme == "EXTERNAL"
        assert lb.region is None  # Global LBs don't have region
        assert lb.project_id == "my-project"

    def test_from_api_response_region_from_url(self) -> None:
        """Test extracting region from full URL."""
        data = {
            "name": "region-url-lb",
            "region": "https://www.googleapis.com/compute/v1/projects/proj/regions/europe-west1",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.region == "europe-west1"

    def test_from_api_response_region_simple(self) -> None:
        """Test region as simple string."""
        data = {
            "name": "region-simple-lb",
            "region": "asia-southeast1",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.region == "asia-southeast1"

    def test_from_api_response_tcp_protocol(self) -> None:
        """Test TCP load balancer."""
        data = {
            "name": "tcp-lb",
            "IPProtocol": "TCP",
            "portRange": "443-443",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.protocol == "TCP"
        assert lb.port_range == "443-443"

    def test_from_api_response_udp_protocol(self) -> None:
        """Test UDP load balancer."""
        data = {
            "name": "udp-lb",
            "IPProtocol": "UDP",
            "portRange": "53-53",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.protocol == "UDP"

    def test_from_api_response_no_target(self) -> None:
        """Test creating LB without target field."""
        data = {
            "name": "no-target-lb",
            "selfLink": "projects/my-project/regions/us-east1/forwardingRules/no-target-lb",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.project_id == "my-project"

    def test_from_api_response_no_project_info(self) -> None:
        """Test creating LB without project information."""
        data = {
            "name": "no-project-lb",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.project_id is None

    def test_from_api_response_malformed_target(self) -> None:
        """Test creating LB with malformed target path."""
        data = {
            "name": "malformed-target",
            "target": "invalid-target-path",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.project_id is None

    def test_from_api_response_invalid_timestamp(self) -> None:
        """Test creating LB with invalid timestamp."""
        data = {
            "name": "invalid-timestamp",
            "creationTimestamp": "not-a-timestamp",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.created_at is None

    def test_from_api_response_standard_tier(self) -> None:
        """Test creating LB with STANDARD network tier."""
        data = {
            "name": "standard-tier-lb",
            "networkTier": "STANDARD",
        }

        lb = LoadBalancer.from_api_response(data)

        assert lb.network_tier == "STANDARD"

    def test_is_external_true(self) -> None:
        """Test is_external when scheme is EXTERNAL."""
        lb = LoadBalancer(
            id="external-lb",
            name="external-lb",
            lb_name="external-lb",
            load_balancing_scheme="EXTERNAL",
        )

        assert lb.is_external() is True

    def test_is_external_false_internal(self) -> None:
        """Test is_external when scheme is INTERNAL."""
        lb = LoadBalancer(
            id="internal-lb",
            name="internal-lb",
            lb_name="internal-lb",
            load_balancing_scheme="INTERNAL",
        )

        assert lb.is_external() is False

    def test_is_external_false_none(self) -> None:
        """Test is_external when scheme is None."""
        lb = LoadBalancer(
            id="no-scheme-lb",
            name="no-scheme-lb",
            lb_name="no-scheme-lb",
        )

        assert lb.is_external() is False

    def test_is_external_false_other_scheme(self) -> None:
        """Test is_external with other scheme values."""
        lb = LoadBalancer(
            id="other-scheme-lb",
            name="other-scheme-lb",
            lb_name="other-scheme-lb",
            load_balancing_scheme="INTERNAL_MANAGED",
        )

        assert lb.is_external() is False
