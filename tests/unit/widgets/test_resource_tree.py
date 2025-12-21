"""Tests for resource tree widget."""

from unittest.mock import AsyncMock, patch

import pytest

from sequel.models.compute import ComputeInstance, InstanceGroup
from sequel.models.gke import GKECluster, GKENode
from sequel.models.iam import IAMRoleBinding, ServiceAccount
from sequel.widgets.resource_tree import ResourceTree, ResourceTreeNode, ResourceType


@pytest.fixture
def resource_tree() -> ResourceTree:
    """Create a resource tree widget for testing."""
    return ResourceTree()


@pytest.fixture
def sample_gke_cluster() -> GKECluster:
    """Create a sample GKE cluster for testing."""
    api_data = {
        "name": "my-cluster",
        "location": "us-central1-a",
        "status": "RUNNING",
        "currentNodeCount": 3,
        "endpoint": "1.2.3.4",
    }
    return GKECluster.from_api_response(api_data)


@pytest.fixture
def sample_instance_group() -> InstanceGroup:
    """Create a sample instance group for testing."""
    api_data = {
        "name": "my-instance-group",
        "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
        "size": 5,
        "creationTimestamp": "2023-01-01T00:00:00Z",
    }
    return InstanceGroup.from_api_response(api_data)


@pytest.fixture
def sample_service_account() -> ServiceAccount:
    """Create a sample service account for testing."""
    api_data = {
        "name": "projects/my-project/serviceAccounts/my-sa@my-project.iam.gserviceaccount.com",
        "email": "my-sa@my-project.iam.gserviceaccount.com",
        "displayName": "My Service Account",
        "disabled": False,
    }
    return ServiceAccount.from_api_response(api_data)


class TestResourceTreeNode:
    """Test suite for ResourceTreeNode."""

    def test_initialization_basic(self) -> None:
        """Test basic resource tree node initialization."""
        node = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="test-project",
        )
        assert node.resource_type == ResourceType.PROJECT
        assert node.resource_id == "test-project"
        assert node.resource_data is None
        assert node.project_id is None
        assert node.location is None
        assert node.zone is None
        assert node.loaded is False

    def test_initialization_with_all_fields(self) -> None:
        """Test resource tree node initialization with all fields."""
        node = ResourceTreeNode(
            resource_type=ResourceType.GKE_NODE,
            resource_id="test-cluster",
            resource_data={"test": "data"},
            project_id="my-project",
            location="us-central1-a",
            zone="us-central1-a",
        )
        assert node.resource_type == ResourceType.GKE_NODE
        assert node.resource_id == "test-cluster"
        assert node.resource_data == {"test": "data"}
        assert node.project_id == "my-project"
        assert node.location == "us-central1-a"
        assert node.zone == "us-central1-a"

    def test_resource_types(self) -> None:
        """Test all resource type constants exist."""
        assert ResourceType.PROJECT == "project"
        assert ResourceType.CLOUDSQL == "cloudsql"
        assert ResourceType.COMPUTE == "compute"
        assert ResourceType.COMPUTE_INSTANCE == "compute_instance"
        assert ResourceType.GKE == "gke"
        assert ResourceType.GKE_NODE == "gke_node"
        assert ResourceType.SECRETS == "secrets"
        assert ResourceType.IAM == "iam"
        assert ResourceType.IAM_ROLE == "iam_role"


class TestResourceTree:
    """Test suite for ResourceTree widget."""

    def test_initialization(self, resource_tree: ResourceTree) -> None:
        """Test resource tree initialization."""
        assert resource_tree.root is not None
        assert resource_tree.root.label.plain == "GCP Resources"

    @pytest.mark.asyncio
    async def test_load_cluster_nodes_with_nodes(
        self, resource_tree: ResourceTree, sample_gke_cluster: GKECluster
    ) -> None:
        """Test loading cluster nodes when cluster has nodes."""
        # Create mock nodes to return
        mock_nodes = [
            GKENode.from_api_response(
                {"name": f"node-pool-1-{i}", "status": "READY", "machineType": "n1-standard-1"},
                "my-cluster"
            )
            for i in range(1, 4)
        ]

        # Create a parent node for the cluster
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_NODE,
            resource_id="my-cluster",
            resource_data=sample_gke_cluster,
            project_id="my-project",
            location="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Test Cluster", data=parent_node_data, allow_expand=True
        )

        # Mock the GKE service
        with patch("sequel.widgets.resource_tree.get_gke_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_nodes = AsyncMock(return_value=mock_nodes)
            mock_get_service.return_value = mock_service

            # Load the cluster nodes
            await resource_tree._load_cluster_nodes(parent_node)

        # Should have 3 nodes with real names
        assert len(parent_node.children) == 3
        assert "node-pool-1-1" in parent_node.children[0].label.plain
        assert "node-pool-1-2" in parent_node.children[1].label.plain
        assert "node-pool-1-3" in parent_node.children[2].label.plain

    @pytest.mark.asyncio
    async def test_load_cluster_nodes_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading cluster nodes when cluster has no nodes."""
        # Create a cluster with 0 nodes
        cluster_data = {
            "name": "empty-cluster",
            "location": "us-central1-a",
            "status": "RUNNING",
            "currentNodeCount": 0,
        }
        cluster = GKECluster.from_api_response(cluster_data)

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_NODE,
            resource_id="empty-cluster",
            resource_data=cluster,
            project_id="my-project",
            location="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Empty Cluster", data=parent_node_data, allow_expand=True
        )

        # Mock the GKE service to return empty list
        with patch("sequel.widgets.resource_tree.get_gke_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_nodes = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            # Load the cluster nodes
            await resource_tree._load_cluster_nodes(parent_node)

        # Node should be removed since it has no children
        assert parent_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_load_instances_in_group_with_instances(
        self, resource_tree: ResourceTree, sample_instance_group: InstanceGroup
    ) -> None:
        """Test loading instances when group has instances."""
        # Create mock instances to return
        mock_instances = [
            ComputeInstance.from_api_response({
                "name": f"instance-{i}",
                "zone": "us-central1-a",
                "status": "RUNNING",
                "machineType": "n1-standard-1",
            })
            for i in range(1, 6)
        ]

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE,
            resource_id="my-instance-group",
            resource_data=sample_instance_group,
            project_id="my-project",
            zone="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Test Instance Group", data=parent_node_data, allow_expand=True
        )

        # Mock the Compute service
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_group = AsyncMock(return_value=mock_instances)
            mock_get_service.return_value = mock_service

            # Load the instances
            await resource_tree._load_instances_in_group(parent_node)

        # Should have 5 instances with real names
        assert len(parent_node.children) == 5
        assert "instance-1" in parent_node.children[0].label.plain
        assert "instance-5" in parent_node.children[4].label.plain

    @pytest.mark.asyncio
    async def test_load_instances_in_group_over_limit(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading instances when group has more than 10 instances."""
        # Create a group with 15 instances
        group_data = {
            "name": "large-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "size": 15,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        # Mock service returns only 10 instances (API limit)
        mock_instances = [
            ComputeInstance.from_api_response({
                "name": f"instance-{i}",
                "zone": "us-central1-a",
                "status": "RUNNING",
            })
            for i in range(1, 11)
        ]

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE,
            resource_id="large-group",
            resource_data=group,
            project_id="my-project",
            zone="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Large Group", data=parent_node_data, allow_expand=True
        )

        # Mock the Compute service
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_group = AsyncMock(return_value=mock_instances)
            mock_get_service.return_value = mock_service

            # Load the instances
            await resource_tree._load_instances_in_group(parent_node)

        # Should have 10 instances + 1 "and more" message
        assert len(parent_node.children) == 11
        assert "instance-10" in parent_node.children[9].label.plain
        assert "and 5 more" in parent_node.children[10].label.plain

    @pytest.mark.asyncio
    async def test_load_instances_in_group_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading instances when group is empty."""
        # Create an empty group
        group_data = {
            "name": "empty-group",
            "zone": "us-central1-a",
            "size": 0,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE,
            resource_id="empty-group",
            resource_data=group,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "Empty Group", data=parent_node_data, allow_expand=True
        )

        # Load the instances
        await resource_tree._load_instances_in_group(parent_node)

        # Node should be removed since it has no children
        assert parent_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_load_service_account_roles(
        self, resource_tree: ResourceTree, sample_service_account: ServiceAccount
    ) -> None:
        """Test loading IAM roles for a service account."""
        # Create mock role bindings
        mock_roles = [
            IAMRoleBinding.from_api_response(
                role="roles/editor",
                member=sample_service_account.email,
                resource="projects/my-project"
            )
        ]

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.IAM_ROLE,
            resource_id=sample_service_account.email,
            resource_data=sample_service_account,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            sample_service_account.email, data=parent_node_data, allow_expand=True
        )

        # Mock the IAM service
        with patch("sequel.widgets.resource_tree.get_iam_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_service_account_roles = AsyncMock(return_value=mock_roles)
            mock_get_service.return_value = mock_service

            # Load the roles
            await resource_tree._load_service_account_roles(parent_node)

        # Should have 1 role
        assert len(parent_node.children) == 1
        assert "editor" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_service_account_roles_no_data(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading roles when node has no resource data."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.IAM_ROLE,
            resource_id="test-account",
            resource_data=None,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "Test Account", data=parent_node_data, allow_expand=True
        )

        # Should handle gracefully (no resource_data means we can't fetch roles)
        await resource_tree._load_service_account_roles(parent_node)

        # Node should be removed since we can't fetch roles without resource data
        assert len(parent_node.children) == 0

    def test_zone_extraction_from_instance_group(self) -> None:
        """Test zone extraction from instance group zone URL."""
        zone_url = "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a"
        zone_parts = zone_url.split('/')
        zone = zone_parts[-1]
        assert zone == "us-central1-a"

    def test_location_storage_in_node(self, sample_gke_cluster: GKECluster) -> None:
        """Test that location is properly stored in node."""
        node = ResourceTreeNode(
            resource_type=ResourceType.GKE_NODE,
            resource_id="test-cluster",
            resource_data=sample_gke_cluster,
            location="us-central1-a",
        )
        assert node.location == "us-central1-a"

    @pytest.mark.asyncio
    async def test_load_cluster_nodes_no_resource_data(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading cluster nodes when node has no resource data."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_NODE,
            resource_id="test-cluster",
            resource_data=None,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "Test Cluster", data=parent_node_data, allow_expand=True
        )

        # Should handle gracefully
        await resource_tree._load_cluster_nodes(parent_node)

        # Children should be removed
        assert len(parent_node.children) == 0

    @pytest.mark.asyncio
    async def test_load_instances_in_group_no_resource_data(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading instances when node has no resource data."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE,
            resource_id="test-group",
            resource_data=None,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "Test Group", data=parent_node_data, allow_expand=True
        )

        # Should handle gracefully
        await resource_tree._load_instances_in_group(parent_node)

        # Children should be removed
        assert len(parent_node.children) == 0

    @pytest.mark.asyncio
    async def test_load_instances_single_instance(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading instances when group has exactly 1 instance."""
        group_data = {
            "name": "single-instance-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "size": 1,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        # Mock service returns 1 instance
        mock_instances = [
            ComputeInstance.from_api_response({
                "name": "single-instance",
                "zone": "us-central1-a",
                "status": "RUNNING",
            })
        ]

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE,
            resource_id="single-instance-group",
            resource_data=group,
            project_id="my-project",
            zone="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Single Instance Group", data=parent_node_data, allow_expand=True
        )

        # Mock the Compute service
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_group = AsyncMock(return_value=mock_instances)
            mock_get_service.return_value = mock_service

            # Load the instances
            await resource_tree._load_instances_in_group(parent_node)

        # Should have exactly 1 instance
        assert len(parent_node.children) == 1
        assert "single-instance" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_cluster_nodes_single_node(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading cluster nodes when cluster has exactly 1 node."""
        cluster_data = {
            "name": "single-node-cluster",
            "location": "us-central1-a",
            "status": "RUNNING",
            "currentNodeCount": 1,
        }
        cluster = GKECluster.from_api_response(cluster_data)

        # Mock service returns 1 node
        mock_nodes = [
            GKENode.from_api_response(
                {"name": "node-pool-1", "status": "READY", "machineType": "n1-standard-1"},
                "single-node-cluster"
            )
        ]

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_NODE,
            resource_id="single-node-cluster",
            resource_data=cluster,
            project_id="my-project",
            location="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Single Node Cluster", data=parent_node_data, allow_expand=True
        )

        # Mock the GKE service
        with patch("sequel.widgets.resource_tree.get_gke_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_nodes = AsyncMock(return_value=mock_nodes)
            mock_get_service.return_value = mock_service

            # Load the cluster nodes
            await resource_tree._load_cluster_nodes(parent_node)

        # Should have exactly 1 node
        assert len(parent_node.children) == 1
        assert "node-pool-1" in parent_node.children[0].label.plain

    def test_node_loaded_flag(self) -> None:
        """Test that loaded flag defaults to False."""
        node = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="test-project",
        )
        assert node.loaded is False

        # Simulate loading
        node.loaded = True
        assert node.loaded is True
