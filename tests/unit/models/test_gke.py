"""Unit tests for GKE models."""

from typing import Any

from sequel.models.gke import GKECluster, GKENode


class TestGKECluster:
    """Tests for GKECluster model."""

    def test_create_gke_cluster(self) -> None:
        """Test creating a GKE cluster instance."""
        cluster = GKECluster(
            id="my-cluster",
            name="my-cluster",
            cluster_name="my-cluster",
            location="us-central1-a",
            status="RUNNING",
            endpoint="35.192.0.1",
            node_count=3,
            version="1.27.3-gke.100",
        )

        assert cluster.id == "my-cluster"
        assert cluster.cluster_name == "my-cluster"
        assert cluster.location == "us-central1-a"
        assert cluster.status == "RUNNING"
        assert cluster.endpoint == "35.192.0.1"
        assert cluster.node_count == 3
        assert cluster.version == "1.27.3-gke.100"

    def test_from_api_response_full(self) -> None:
        """Test creating cluster from full API response."""
        data = {
            "name": "production-cluster",
            "location": "us-central1",
            "status": "RUNNING",
            "endpoint": "35.192.0.1",
            "currentMasterVersion": "1.27.3-gke.100",
            "currentNodeCount": 5,
            "selfLink": "https://container.googleapis.com/v1/projects/my-project/locations/us-central1/clusters/production-cluster",
        }

        cluster = GKECluster.from_api_response(data)

        assert cluster.cluster_name == "production-cluster"
        assert cluster.location == "us-central1"
        assert cluster.status == "RUNNING"
        assert cluster.endpoint == "35.192.0.1"
        assert cluster.version == "1.27.3-gke.100"
        assert cluster.node_count == 5
        assert cluster.project_id == "my-project"
        assert cluster.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating cluster from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-cluster",
        }

        cluster = GKECluster.from_api_response(data)

        assert cluster.cluster_name == "minimal-cluster"
        assert cluster.location is None
        assert cluster.status == "UNKNOWN"
        assert cluster.endpoint is None
        assert cluster.version is None
        assert cluster.node_count == 0
        assert cluster.project_id is None

    def test_from_api_response_without_selflink(self) -> None:
        """Test creating cluster without selfLink."""
        data = {
            "name": "test-cluster",
            "location": "us-west1-a",
            "status": "RUNNING",
        }

        cluster = GKECluster.from_api_response(data)

        assert cluster.project_id is None

    def test_is_running_true(self) -> None:
        """Test is_running when cluster is running."""
        cluster = GKECluster(
            id="cluster",
            name="cluster",
            cluster_name="cluster",
            status="RUNNING",
        )

        assert cluster.is_running() is True

    def test_is_running_false(self) -> None:
        """Test is_running when cluster is not running."""
        cluster = GKECluster(
            id="cluster",
            name="cluster",
            cluster_name="cluster",
            status="STOPPING",
        )

        assert cluster.is_running() is False


class TestGKENode:
    """Tests for GKENode model."""

    def test_create_gke_node(self) -> None:
        """Test creating a GKE node instance."""
        node = GKENode(
            id="node-1",
            name="node-1",
            node_name="node-1",
            cluster_name="my-cluster",
            machine_type="n1-standard-2",
            status="READY",
            version="1.27.3-gke.100",
        )

        assert node.id == "node-1"
        assert node.node_name == "node-1"
        assert node.cluster_name == "my-cluster"
        assert node.machine_type == "n1-standard-2"
        assert node.status == "READY"
        assert node.version == "1.27.3-gke.100"

    def test_from_api_response_full(self) -> None:
        """Test creating node from full API response."""
        data = {
            "name": "default-pool-node-1",
            "machineType": "n1-standard-4",
            "status": "READY",
            "version": "1.27.3-gke.100",
        }

        node = GKENode.from_api_response(data, "production-cluster")

        assert node.node_name == "default-pool-node-1"
        assert node.cluster_name == "production-cluster"
        assert node.machine_type == "n1-standard-4"
        assert node.status == "READY"
        assert node.version == "1.27.3-gke.100"
        assert node.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating node from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-node",
        }

        node = GKENode.from_api_response(data, "test-cluster")

        assert node.node_name == "minimal-node"
        assert node.cluster_name == "test-cluster"
        assert node.machine_type is None
        assert node.status == "UNKNOWN"
        assert node.version is None
        assert node.project_id is None
