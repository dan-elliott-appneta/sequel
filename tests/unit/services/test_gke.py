"""Unit tests for GKE service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.gke import GKECluster, GKENode
from sequel.services.gke import GKEService, get_gke_service, reset_gke_service


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
def mock_gke_client() -> MagicMock:
    """Create mock GKE ClusterManager client."""
    return MagicMock()


@pytest.fixture
def gke_service() -> GKEService:
    """Create GKE service instance."""
    reset_gke_service()
    return GKEService()


class TestGKEService:
    """Tests for GKEService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, gke_service: GKEService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates GKE client."""
        with (
            patch("sequel.services.gke.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.gke.container_v1.ClusterManagerClient") as mock_client_class,
        ):
            mock_client_class.return_value = MagicMock()

            client = await gke_service._get_client()

            mock_client_class.assert_called_once_with(credentials=mock_auth_manager.credentials)
            assert client is not None
            assert gke_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, gke_service: GKEService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        gke_service._client = mock_client

        client = await gke_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_clusters_success(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test listing GKE clusters successfully."""
        # Mock cluster protobuf objects
        mock_cluster_proto1 = MagicMock()
        mock_cluster_proto1.name = "cluster-1"
        mock_cluster_proto1.location = "us-central1-a"
        mock_cluster_proto1.status = "RUNNING"
        mock_cluster_proto1.endpoint = "35.192.0.1"
        mock_cluster_proto1.current_node_count = 3
        mock_cluster_proto1.current_master_version = "1.27.3-gke.100"

        mock_cluster_proto2 = MagicMock()
        mock_cluster_proto2.name = "cluster-2"
        mock_cluster_proto2.location = "us-central1-b"
        mock_cluster_proto2.status = "RUNNING"
        mock_cluster_proto2.endpoint = "35.192.0.2"
        mock_cluster_proto2.current_node_count = 5
        mock_cluster_proto2.current_master_version = "1.27.3-gke.100"

        # Mock response
        mock_response = MagicMock()
        mock_response.clusters = [mock_cluster_proto1, mock_cluster_proto2]

        mock_gke_client.list_clusters.return_value = mock_response
        gke_service._client = mock_gke_client

        clusters = await gke_service.list_clusters("test-project", use_cache=False)

        assert len(clusters) == 2
        assert isinstance(clusters[0], GKECluster)
        assert clusters[0].cluster_name == "cluster-1"
        assert clusters[1].cluster_name == "cluster-2"

    @pytest.mark.asyncio
    async def test_list_clusters_empty(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test listing GKE clusters when none exist."""
        mock_response = MagicMock()
        mock_response.clusters = []

        mock_gke_client.list_clusters.return_value = mock_response
        gke_service._client = mock_gke_client

        clusters = await gke_service.list_clusters("test-project", use_cache=False)

        assert len(clusters) == 0

    @pytest.mark.asyncio
    async def test_list_clusters_error(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test error handling when listing clusters."""
        mock_gke_client.list_clusters.side_effect = Exception("API Error")
        gke_service._client = mock_gke_client

        clusters = await gke_service.list_clusters("test-project", use_cache=False)

        # Should return empty list on error
        assert len(clusters) == 0

    @pytest.mark.asyncio
    async def test_list_clusters_with_cache(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test listing clusters with caching."""
        mock_cluster = GKECluster(
            id="cluster-1",
            name="cluster-1",
            cluster_name="cluster-1",
            location="us-central1-a",
            status="RUNNING",
        )

        with patch.object(gke_service._cache, "get", return_value=[mock_cluster]):
            clusters = await gke_service.list_clusters("test-project", use_cache=True)

            assert len(clusters) == 1
            assert clusters[0] == mock_cluster

    @pytest.mark.asyncio
    async def test_get_cluster_success(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test getting a specific GKE cluster."""
        mock_cluster_proto = MagicMock()
        mock_cluster_proto.name = "test-cluster"
        mock_cluster_proto.location = "us-central1-a"
        mock_cluster_proto.status = "RUNNING"
        mock_cluster_proto.endpoint = "35.192.0.1"
        mock_cluster_proto.current_node_count = 3
        mock_cluster_proto.current_master_version = "1.27.3-gke.100"

        mock_gke_client.get_cluster.return_value = mock_cluster_proto
        gke_service._client = mock_gke_client

        cluster = await gke_service.get_cluster(
            "test-project", "us-central1-a", "test-cluster", use_cache=False
        )

        assert cluster is not None
        assert isinstance(cluster, GKECluster)
        assert cluster.cluster_name == "test-cluster"
        assert cluster.location == "us-central1-a"

    @pytest.mark.asyncio
    async def test_get_cluster_not_found(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test getting a cluster that doesn't exist."""
        mock_gke_client.get_cluster.side_effect = Exception("Not found")
        gke_service._client = mock_gke_client

        cluster = await gke_service.get_cluster(
            "test-project", "us-central1-a", "nonexistent-cluster", use_cache=False
        )

        assert cluster is None

    @pytest.mark.asyncio
    async def test_get_cluster_with_cache(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test getting cluster with caching."""
        mock_cluster = GKECluster(
            id="test-cluster",
            name="test-cluster",
            cluster_name="test-cluster",
            location="us-central1-a",
            status="RUNNING",
        )

        with patch.object(gke_service._cache, "get", return_value=mock_cluster):
            cluster = await gke_service.get_cluster(
                "test-project", "us-central1-a", "test-cluster", use_cache=True
            )

            assert cluster == mock_cluster

    @pytest.mark.asyncio
    async def test_list_nodes_success(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test listing nodes in a GKE cluster."""
        # Mock node pool protobuf objects
        mock_node_pool1 = MagicMock()
        mock_node_pool1.name = "default-pool"
        mock_node_pool1.initial_node_count = 3
        mock_node_pool1.status = "RUNNING"
        mock_node_pool1.version = "1.27.3-gke.100"

        # Mock config
        mock_config = MagicMock()
        mock_config.machine_type = "n1-standard-2"
        mock_node_pool1.config = mock_config

        mock_node_pool2 = MagicMock()
        mock_node_pool2.name = "high-mem-pool"
        mock_node_pool2.initial_node_count = 2
        mock_node_pool2.status = "RUNNING"
        mock_node_pool2.version = "1.27.3-gke.100"

        mock_config2 = MagicMock()
        mock_config2.machine_type = "n1-highmem-4"
        mock_node_pool2.config = mock_config2

        # Mock response
        mock_response = MagicMock()
        mock_response.node_pools = [mock_node_pool1, mock_node_pool2]

        mock_gke_client.list_node_pools.return_value = mock_response
        gke_service._client = mock_gke_client

        nodes = await gke_service.list_nodes(
            "test-project", "us-central1-a", "test-cluster", use_cache=False
        )

        # Should have 5 nodes total (3 from pool1 + 2 from pool2)
        assert len(nodes) == 5
        assert isinstance(nodes[0], GKENode)

        # Check that nodes from first pool have correct machine type
        assert all(node.machine_type == "n1-standard-2" for node in nodes[:3])
        # Check that nodes from second pool have correct machine type
        assert all(node.machine_type == "n1-highmem-4" for node in nodes[3:5])

    @pytest.mark.asyncio
    async def test_list_nodes_empty_cluster(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test listing nodes when cluster has no node pools."""
        mock_response = MagicMock()
        mock_response.node_pools = []

        mock_gke_client.list_node_pools.return_value = mock_response
        gke_service._client = mock_gke_client

        nodes = await gke_service.list_nodes(
            "test-project", "us-central1-a", "empty-cluster", use_cache=False
        )

        assert len(nodes) == 0

    @pytest.mark.asyncio
    async def test_list_nodes_error(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test error handling when listing nodes."""
        mock_gke_client.list_node_pools.side_effect = Exception("API Error")
        gke_service._client = mock_gke_client

        nodes = await gke_service.list_nodes(
            "test-project", "us-central1-a", "test-cluster", use_cache=False
        )

        # Should return empty list on error
        assert len(nodes) == 0

    @pytest.mark.asyncio
    async def test_list_nodes_with_cache(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test listing nodes with caching."""
        mock_node = GKENode(
            id="node-1",
            name="node-1",
            node_name="node-1",
            cluster_name="test-cluster",
            machine_type="n1-standard-2",
            status="READY",
        )

        with patch.object(gke_service._cache, "get", return_value=[mock_node]):
            nodes = await gke_service.list_nodes(
                "test-project", "us-central1-a", "test-cluster", use_cache=True
            )

            assert len(nodes) == 1
            assert nodes[0] == mock_node

    @pytest.mark.asyncio
    async def test_list_nodes_limits_to_10_per_pool(
        self, gke_service: GKEService, mock_gke_client: MagicMock
    ) -> None:
        """Test that list_nodes limits to 10 nodes per pool."""
        # Mock node pool with 15 nodes
        mock_node_pool = MagicMock()
        mock_node_pool.name = "large-pool"
        mock_node_pool.initial_node_count = 15  # More than the limit
        mock_node_pool.status = "RUNNING"
        mock_node_pool.version = "1.27.3-gke.100"

        mock_config = MagicMock()
        mock_config.machine_type = "n1-standard-2"
        mock_node_pool.config = mock_config

        mock_response = MagicMock()
        mock_response.node_pools = [mock_node_pool]

        mock_gke_client.list_node_pools.return_value = mock_response
        gke_service._client = mock_gke_client

        nodes = await gke_service.list_nodes(
            "test-project", "us-central1-a", "test-cluster", use_cache=False
        )

        # Should be limited to 10 nodes
        assert len(nodes) == 10

    def test_proto_to_dict(self, gke_service: GKEService) -> None:
        """Test converting protobuf message to dict."""
        mock_proto = MagicMock()
        mock_proto.name = "test-cluster"
        mock_proto.location = "us-central1-a"
        mock_proto.status = "RUNNING"
        mock_proto.endpoint = "35.192.0.1"
        mock_proto.current_node_count = 3
        mock_proto.current_master_version = "1.27.3-gke.100"
        mock_proto.self_link = "https://container.googleapis.com/v1/projects/test/locations/us-central1-a/clusters/test-cluster"

        result = gke_service._proto_to_dict(mock_proto)

        assert result["name"] == "test-cluster"
        assert result["location"] == "us-central1-a"
        assert result["status"] == "RUNNING"
        assert result["endpoint"] == "35.192.0.1"
        assert result["currentNodeCount"] == 3
        assert result["currentMasterVersion"] == "1.27.3-gke.100"
        assert result["selfLink"].startswith("https://")

    def test_proto_to_dict_minimal(self, gke_service: GKEService) -> None:
        """Test converting protobuf message with minimal fields."""
        mock_proto = MagicMock(spec=[])  # No attributes

        result = gke_service._proto_to_dict(mock_proto)

        # Should return empty dict for proto with no recognized attributes
        assert result == {}


class TestGetGKEService:
    """Tests for get_gke_service function."""

    @pytest.mark.asyncio
    async def test_get_gke_service_creates_instance(self) -> None:
        """Test that get_gke_service creates a global instance."""
        reset_gke_service()

        service1 = await get_gke_service()
        service2 = await get_gke_service()

        assert service1 is service2
        assert isinstance(service1, GKEService)

    @pytest.mark.asyncio
    async def test_reset_gke_service(self) -> None:
        """Test that reset_gke_service clears the global instance."""
        service1 = await get_gke_service()
        reset_gke_service()
        service2 = await get_gke_service()

        assert service1 is not service2
