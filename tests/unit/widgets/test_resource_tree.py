"""Tests for resource tree widget."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.clouddns import DNSRecord, ManagedZone
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


@pytest.fixture
def sample_dns_zone() -> ManagedZone:
    """Create a sample DNS zone for testing."""
    api_data = {
        "name": "my-zone",
        "dnsName": "example.com.",
        "description": "Example zone",
        "visibility": "public",
        "nameServers": ["ns1.example.com", "ns2.example.com"],
    }
    return ManagedZone.from_api_response(api_data)


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
            resource_type=ResourceType.GKE_CLUSTER,
            resource_id="test-cluster",
            resource_data={"test": "data"},
            project_id="my-project",
            location="us-central1-a",
            zone="us-central1-a",
        )
        assert node.resource_type == ResourceType.GKE_CLUSTER
        assert node.resource_id == "test-cluster"
        assert node.resource_data == {"test": "data"}
        assert node.project_id == "my-project"
        assert node.location == "us-central1-a"
        assert node.zone == "us-central1-a"

    def test_resource_types(self) -> None:
        """Test all resource type constants exist."""
        assert ResourceType.PROJECT == "project"
        assert ResourceType.CLOUDDNS == "clouddns"
        assert ResourceType.CLOUDDNS_ZONE == "clouddns_zone"
        assert ResourceType.CLOUDDNS_RECORD == "clouddns_record"
        assert ResourceType.CLOUDSQL == "cloudsql"
        assert ResourceType.COMPUTE == "compute"
        assert ResourceType.COMPUTE_INSTANCE_GROUP == "compute_instance_group"
        assert ResourceType.COMPUTE_INSTANCE == "compute_instance"
        assert ResourceType.GKE == "gke"
        assert ResourceType.GKE_CLUSTER == "gke_cluster"
        assert ResourceType.GKE_NODE == "gke_node"
        assert ResourceType.SECRETS == "secrets"
        assert ResourceType.IAM == "iam"
        assert ResourceType.IAM_SERVICE_ACCOUNT == "iam_service_account"
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
            resource_type=ResourceType.GKE_CLUSTER,
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
            resource_type=ResourceType.GKE_CLUSTER,
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

        # Node should remain with a message instead of being removed
        assert parent_node in resource_tree.root.children
        assert len(parent_node.children) == 1
        assert "No nodes found" in parent_node.children[0].label.plain

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
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
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
        """Test loading instances when group exceeds display limit."""
        from sequel.widgets.resource_tree import MAX_CHILDREN_PER_NODE

        # Create a group with size > MAX_CHILDREN_PER_NODE
        group_data = {
            "name": "large-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "size": MAX_CHILDREN_PER_NODE + 10,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        # Mock service returns instances exceeding the display limit
        num_instances = MAX_CHILDREN_PER_NODE + 10
        mock_instances = [
            ComputeInstance.from_api_response({
                "name": f"instance-{i}",
                "zone": "us-central1-a",
                "status": "RUNNING",
            })
            for i in range(1, num_instances + 1)
        ]

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
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

        # Should have MAX_CHILDREN_PER_NODE instances + 1 "and more" message
        assert len(parent_node.children) == MAX_CHILDREN_PER_NODE + 1
        assert f"instance-{MAX_CHILDREN_PER_NODE}" in parent_node.children[MAX_CHILDREN_PER_NODE - 1].label.plain
        assert "and 10 more" in parent_node.children[MAX_CHILDREN_PER_NODE].label.plain

    @pytest.mark.asyncio
    async def test_load_instances_in_group_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading instances when group is empty."""
        # Create an empty group
        group_data = {
            "name": "empty-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "size": 0,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
            resource_id="empty-group",
            resource_data=group,
            project_id="my-project",
            zone="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Empty Group", data=parent_node_data, allow_expand=True
        )

        # Mock the Compute service to return empty list
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_group = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            # Load the instances
            await resource_tree._load_instances_in_group(parent_node)

        # Node should remain with a message instead of being removed
        assert parent_node in resource_tree.root.children
        assert len(parent_node.children) == 1
        assert "No instances found" in parent_node.children[0].label.plain

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
            resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
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
            resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
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
            resource_type=ResourceType.GKE_CLUSTER,
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
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
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
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
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
            resource_type=ResourceType.GKE_CLUSTER,
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

    @pytest.mark.asyncio
    async def test_load_service_account_roles_empty(
        self, resource_tree: ResourceTree, sample_service_account: ServiceAccount
    ) -> None:
        """Test loading roles when service account has no roles."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
            resource_id=sample_service_account.email,
            resource_data=sample_service_account,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            sample_service_account.email, data=parent_node_data, allow_expand=True
        )

        # Mock the IAM service to return empty list
        with patch("sequel.widgets.resource_tree.get_iam_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_service_account_roles = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            # Load the roles
            await resource_tree._load_service_account_roles(parent_node)

        # Node should remain with a message instead of being removed
        assert parent_node in resource_tree.root.children
        assert len(parent_node.children) == 1
        assert "No roles assigned" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_service_account_roles_missing_project_id(
        self, resource_tree: ResourceTree, sample_service_account: ServiceAccount
    ) -> None:
        """Test loading roles when parent node has no project_id."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
            resource_id=sample_service_account.email,
            resource_data=sample_service_account,
            project_id=None,  # No project ID
        )
        parent_node = resource_tree.root.add(
            sample_service_account.email, data=parent_node_data, allow_expand=True
        )

        # Load the roles
        await resource_tree._load_service_account_roles(parent_node)

        # Should show warning message
        assert len(parent_node.children) == 1
        assert "Missing project ID" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_service_account_roles_error(
        self, resource_tree: ResourceTree, sample_service_account: ServiceAccount
    ) -> None:
        """Test loading roles when IAM service raises an exception."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
            resource_id=sample_service_account.email,
            resource_data=sample_service_account,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            sample_service_account.email, data=parent_node_data, allow_expand=True
        )

        # Mock the IAM service to raise an exception
        with patch("sequel.widgets.resource_tree.get_iam_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_service_account_roles = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_get_service.return_value = mock_service

            # Load the roles
            await resource_tree._load_service_account_roles(parent_node)

        # Node should remain with error message
        assert parent_node in resource_tree.root.children
        assert len(parent_node.children) == 1
        assert "Error loading roles" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_cluster_nodes_missing_project_id(
        self, resource_tree: ResourceTree, sample_gke_cluster: GKECluster
    ) -> None:
        """Test loading cluster nodes when parent node has no project_id."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_CLUSTER,
            resource_id="my-cluster",
            resource_data=sample_gke_cluster,
            project_id=None,  # No project ID
            location="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Test Cluster", data=parent_node_data, allow_expand=True
        )

        # Load the cluster nodes
        await resource_tree._load_cluster_nodes(parent_node)

        # Should show warning message
        assert len(parent_node.children) == 1
        assert "Missing project ID or location" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_cluster_nodes_missing_location(
        self, resource_tree: ResourceTree, sample_gke_cluster: GKECluster
    ) -> None:
        """Test loading cluster nodes when parent node has no location."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_CLUSTER,
            resource_id="my-cluster",
            resource_data=sample_gke_cluster,
            project_id="my-project",
            location=None,  # No location
        )
        parent_node = resource_tree.root.add(
            "Test Cluster", data=parent_node_data, allow_expand=True
        )

        # Load the cluster nodes
        await resource_tree._load_cluster_nodes(parent_node)

        # Should show warning message
        assert len(parent_node.children) == 1
        assert "Missing project ID or location" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_cluster_nodes_error(
        self, resource_tree: ResourceTree, sample_gke_cluster: GKECluster
    ) -> None:
        """Test loading cluster nodes when GKE service raises an exception."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_CLUSTER,
            resource_id="my-cluster",
            resource_data=sample_gke_cluster,
            project_id="my-project",
            location="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Test Cluster", data=parent_node_data, allow_expand=True
        )

        # Mock the GKE service to raise an exception
        with patch("sequel.widgets.resource_tree.get_gke_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_nodes = AsyncMock(side_effect=Exception("API Error"))
            mock_get_service.return_value = mock_service

            # Load the cluster nodes
            await resource_tree._load_cluster_nodes(parent_node)

        # Node should remain with error message
        assert parent_node in resource_tree.root.children
        assert len(parent_node.children) == 1
        assert "Error loading nodes" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_instances_in_group_missing_project_id(
        self, resource_tree: ResourceTree, sample_instance_group: InstanceGroup
    ) -> None:
        """Test loading instances when parent node has no project_id."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
            resource_id="my-instance-group",
            resource_data=sample_instance_group,
            project_id=None,  # No project ID
            zone="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Test Instance Group", data=parent_node_data, allow_expand=True
        )

        # Load the instances
        await resource_tree._load_instances_in_group(parent_node)

        # Should show warning message
        assert len(parent_node.children) == 1
        assert "Missing project ID" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_instances_in_group_missing_zone(
        self, resource_tree: ResourceTree, sample_instance_group: InstanceGroup
    ) -> None:
        """Test loading instances when parent node has no zone or region."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
            resource_id="my-instance-group",
            resource_data=sample_instance_group,
            project_id="my-project",
            zone=None,  # No zone
            location=None,  # No region either
        )
        parent_node = resource_tree.root.add(
            "Test Instance Group", data=parent_node_data, allow_expand=True
        )

        # Load the instances
        await resource_tree._load_instances_in_group(parent_node)

        # Should show warning message
        assert len(parent_node.children) == 1
        assert "Missing zone or region" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_instances_in_regional_group(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading instances from a regional instance group."""
        # Create a regional instance group
        group_data = {
            "name": "regional-group",
            "region": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1",
            "size": 2,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
            resource_id="regional-group",
            resource_data=group,
            project_id="my-project",
            zone=None,  # Regional groups don't have a zone
            location="us-central1",  # They have a region in location
        )
        parent_node = resource_tree.root.add(
            "Regional Group", data=parent_node_data, allow_expand=True
        )

        # Mock instances to return
        mock_instances = [
            ComputeInstance.from_api_response({
                "name": "regional-instance-1",
                "zone": "us-central1-a",
                "status": "RUNNING",
            }),
            ComputeInstance.from_api_response({
                "name": "regional-instance-2",
                "zone": "us-central1-b",
                "status": "RUNNING",
            })
        ]

        # Mock the Compute service
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_regional_group = AsyncMock(return_value=mock_instances)
            mock_get_service.return_value = mock_service

            # Load the instances
            await resource_tree._load_instances_in_group(parent_node)

        # Should have loaded instances from the regional group
        assert len(parent_node.children) == 2
        assert "regional-instance-1" in parent_node.children[0].label.plain
        assert "regional-instance-2" in parent_node.children[1].label.plain

    @pytest.mark.asyncio
    async def test_load_instances_in_group_error(
        self, resource_tree: ResourceTree, sample_instance_group: InstanceGroup
    ) -> None:
        """Test loading instances when Compute service raises an exception."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
            resource_id="my-instance-group",
            resource_data=sample_instance_group,
            project_id="my-project",
            zone="us-central1-a",
        )
        parent_node = resource_tree.root.add(
            "Test Instance Group", data=parent_node_data, allow_expand=True
        )

        # Mock the Compute service to raise an exception
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_group = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_get_service.return_value = mock_service

            # Load the instances
            await resource_tree._load_instances_in_group(parent_node)

        # Node should remain with error message
        assert parent_node in resource_tree.root.children
        assert len(parent_node.children) == 1
        assert "Error loading instances" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_on_tree_node_expanded_already_loaded(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that node expansion skips already loaded nodes."""
        # Create a node that's already loaded
        node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE,
            resource_id="test-gke",
            project_id="my-project",
        )
        node_data.loaded = True  # Mark as already loaded

        node = resource_tree.root.add(
            "GKE Clusters", data=node_data, allow_expand=True
        )

        # Create mock event with just the node attribute
        from unittest.mock import Mock
        event = Mock()
        event.node = node

        # Should skip loading since already loaded
        await resource_tree._on_tree_node_expanded(event)

        # Node should have no children (loading was skipped)
        assert len(node.children) == 0
        assert node_data.loaded is True

    @pytest.mark.asyncio
    async def test_on_tree_node_expanded_no_data(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that node expansion handles nodes with no data."""
        # Create a node with no data
        node = resource_tree.root.add(
            "Test Node", data=None, allow_expand=True
        )

        # Create mock event
        from unittest.mock import Mock
        event = Mock()
        event.node = node

        # Should handle gracefully
        await resource_tree._on_tree_node_expanded(event)

        # Node should remain unchanged
        assert len(node.children) == 0

    @pytest.mark.asyncio
    async def test_on_tree_node_expanded_instance_group(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test node expansion for instance groups."""
        group_data = {
            "name": "my-instance-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "size": 2,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
            resource_id="my-instance-group",
            resource_data=group,
            project_id="my-project",
            zone="us-central1-a",
        )

        node = resource_tree.root.add(
            "Test Group", data=node_data, allow_expand=True
        )

        # Mock the Compute service
        mock_instances = [
            ComputeInstance.from_api_response({
                "name": "instance-1",
                "zone": "us-central1-a",
                "status": "RUNNING",
            }),
            ComputeInstance.from_api_response({
                "name": "instance-2",
                "zone": "us-central1-a",
                "status": "RUNNING",
            })
        ]

        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_group = AsyncMock(return_value=mock_instances)
            mock_get_service.return_value = mock_service

            # Create mock event
            from unittest.mock import Mock
            event = Mock()
            event.node = node
            await resource_tree._on_tree_node_expanded(event)

        # Should have loaded instances
        assert len(node.children) == 2
        assert "instance-1" in node.children[0].label.plain
        assert "instance-2" in node.children[1].label.plain
        assert node_data.loaded is True

    @pytest.mark.asyncio
    async def test_on_tree_node_expanded_gke_cluster(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test node expansion for GKE clusters."""
        cluster_data = {
            "name": "my-cluster",
            "location": "us-central1-a",
            "status": "RUNNING",
            "currentNodeCount": 1,
        }
        cluster = GKECluster.from_api_response(cluster_data)

        node_data = ResourceTreeNode(
            resource_type=ResourceType.GKE_CLUSTER,
            resource_id="my-cluster",
            resource_data=cluster,
            project_id="my-project",
            location="us-central1-a",
        )

        node = resource_tree.root.add(
            "Test Cluster", data=node_data, allow_expand=True
        )

        # Mock the GKE service
        mock_nodes = [
            GKENode.from_api_response(
                {"name": "node-1", "status": "READY", "machineType": "n1-standard-1"},
                "my-cluster"
            )
        ]

        with patch("sequel.widgets.resource_tree.get_gke_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_nodes = AsyncMock(return_value=mock_nodes)
            mock_get_service.return_value = mock_service

            # Create mock event
            from unittest.mock import Mock
            event = Mock()
            event.node = node
            await resource_tree._on_tree_node_expanded(event)

        # Should have loaded nodes
        assert len(node.children) == 1
        assert "node-1" in node.children[0].label.plain
        assert node_data.loaded is True

    @pytest.mark.asyncio
    async def test_on_tree_node_expanded_service_account(
        self, resource_tree: ResourceTree, sample_service_account: ServiceAccount
    ) -> None:
        """Test node expansion for service accounts."""
        node_data = ResourceTreeNode(
            resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
            resource_id=sample_service_account.email,
            resource_data=sample_service_account,
            project_id="my-project",
        )

        node = resource_tree.root.add(
            sample_service_account.email, data=node_data, allow_expand=True
        )

        # Mock the IAM service
        mock_roles = [
            IAMRoleBinding.from_api_response(
                role="roles/viewer",
                member=sample_service_account.email,
            )
        ]

        with patch("sequel.widgets.resource_tree.get_iam_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_service_account_roles = AsyncMock(return_value=mock_roles)
            mock_get_service.return_value = mock_service

            # Create mock event
            from unittest.mock import Mock
            event = Mock()
            event.node = node
            await resource_tree._on_tree_node_expanded(event)

        # Should have loaded roles
        assert len(node.children) == 1
        assert "viewer" in node.children[0].label.plain
        assert node_data.loaded is True

    @pytest.mark.asyncio
    async def test_on_tree_node_expanded_error_handling(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that node expansion handles errors gracefully."""
        group_data = {
            "name": "error-group",
            "zone": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a",
            "size": 1,
            "creationTimestamp": "2023-01-01T00:00:00Z",
        }
        group = InstanceGroup.from_api_response(group_data)

        node_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
            resource_id="error-group",
            resource_data=group,
            project_id="my-project",
            zone="us-central1-a",
        )

        node = resource_tree.root.add(
            "Error Group", data=node_data, allow_expand=True
        )

        # Mock the Compute service to raise an exception
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instances_in_group = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_get_service.return_value = mock_service

            # Create mock event
            from unittest.mock import Mock
            event = Mock()
            event.node = node
            await resource_tree._on_tree_node_expanded(event)

        # Should have error child node
        assert len(node.children) == 1
        assert "Error loading instances" in node.children[0].label.plain
        # loaded flag should still be set to True to prevent re-trying
        assert node_data.loaded is True

    @pytest.mark.asyncio
    async def test_load_dns_zones_with_zones(
        self, resource_tree: ResourceTree, sample_dns_zone: ManagedZone
    ) -> None:
        """Test loading DNS zones when zones exist."""
        # Create mock zones to return
        mock_zones = [
            sample_dns_zone,
            ManagedZone.from_api_response({
                "name": "private-zone",
                "dnsName": "internal.example.com.",
                "visibility": "private",
            }),
        ]

        # Create a parent node for DNS
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS,
            resource_id="my-project:clouddns",
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "Cloud DNS", data=parent_node_data, allow_expand=True
        )

        # Mock the ResourceState to return zones
        with patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = mock_zones

            # Load the DNS zones
            await resource_tree._load_dns_zones(parent_node)

        # Should have 2 zones
        assert len(parent_node.children) == 2
        assert "example.com." in parent_node.children[0].label.plain
        assert "internal.example.com." in parent_node.children[1].label.plain
        # Public zone should have globe icon, private should have lock icon
        assert "🌍" in parent_node.children[0].label.plain
        assert "🔒" in parent_node.children[1].label.plain

    @pytest.mark.asyncio
    async def test_load_dns_zones_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test loading DNS zones when none exist."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS,
            resource_id="my-project:clouddns",
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "Cloud DNS", data=parent_node_data, allow_expand=True
        )

        # Mock the ResourceState to return empty list
        with patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []

            # Load the DNS zones
            await resource_tree._load_dns_zones(parent_node)

        # Node should be removed if there are no zones
        assert parent_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_load_dns_records_with_records(
        self, resource_tree: ResourceTree, sample_dns_zone: ManagedZone
    ) -> None:
        """Test loading DNS records when records exist."""
        # Create mock DNS records to return
        mock_records = [
            DNSRecord.from_api_response({
                "name": "example.com.",
                "type": "A",
                "ttl": 300,
                "rrdatas": ["192.0.2.1"],
            }),
            DNSRecord.from_api_response({
                "name": "www.example.com.",
                "type": "CNAME",
                "ttl": 600,
                "rrdatas": ["example.com."],
            }),
            DNSRecord.from_api_response({
                "name": "example.com.",
                "type": "MX",
                "ttl": 3600,
                "rrdatas": ["10 mail.example.com.", "20 mail2.example.com."],
            }),
        ]

        # Create a parent node for the DNS zone
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS_ZONE,
            resource_id="my-zone",
            resource_data=sample_dns_zone,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "example.com.", data=parent_node_data, allow_expand=True
        )

        # Mock the ResourceState to return records
        with patch.object(resource_tree._state, "load_dns_records", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = mock_records

            # Load the DNS records
            await resource_tree._load_dns_records(parent_node)

        # Should have 3 records
        assert len(parent_node.children) == 3
        # Check record types appear in labels
        assert "A:" in parent_node.children[0].label.plain
        assert "CNAME:" in parent_node.children[1].label.plain
        assert "MX:" in parent_node.children[2].label.plain

    @pytest.mark.asyncio
    async def test_load_dns_records_empty(
        self, resource_tree: ResourceTree, sample_dns_zone: ManagedZone
    ) -> None:
        """Test loading DNS records when none exist."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS_ZONE,
            resource_id="my-zone",
            resource_data=sample_dns_zone,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "example.com.", data=parent_node_data, allow_expand=True
        )

        # Mock the ResourceState to return empty list
        with patch.object(resource_tree._state, "load_dns_records", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []

            # Load the DNS records
            await resource_tree._load_dns_records(parent_node)

        # Node should remain with a message instead of being removed
        assert parent_node in resource_tree.root.children
        assert len(parent_node.children) == 1
        assert "No DNS records" in parent_node.children[0].label.plain

    @pytest.mark.asyncio
    async def test_load_dns_records_error(
        self, resource_tree: ResourceTree, sample_dns_zone: ManagedZone
    ) -> None:
        """Test error handling when loading DNS records."""
        parent_node_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS_ZONE,
            resource_id="my-zone",
            resource_data=sample_dns_zone,
            project_id="my-project",
        )
        parent_node = resource_tree.root.add(
            "example.com.", data=parent_node_data, allow_expand=True
        )

        # Mock the ResourceState to raise an exception
        with patch.object(resource_tree._state, "load_dns_records", new_callable=AsyncMock) as mock_load:
            mock_load.side_effect = Exception("API Error")

            # Load the DNS records
            await resource_tree._load_dns_records(parent_node)

        # Should have error child node
        assert len(parent_node.children) == 1
        assert "Error loading records" in parent_node.children[0].label.plain

    def test_add_resource_type_nodes_creates_categories(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that _add_resource_type_nodes creates all resource category nodes."""
        project_node = resource_tree.root.add(
            "Test Project", allow_expand=True
        )

        resource_tree._add_resource_type_nodes(project_node, "test-project")

        # Should have 8 resource categories
        assert len(project_node.children) == 8

        # Check all categories exist
        labels = [child.label.plain for child in project_node.children]
        assert any("Cloud DNS" in label for label in labels)
        assert any("Cloud SQL" in label for label in labels)
        assert any("Instance Groups" in label for label in labels)
        assert any("Firewall Policies" in label for label in labels)
        assert any("Load Balancers" in label for label in labels)
        assert any("GKE Clusters" in label for label in labels)
        assert any("Secrets" in label for label in labels)
        assert any("Service Accounts" in label for label in labels)

    def test_add_resource_type_nodes_sets_correct_types(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that _add_resource_type_nodes sets correct resource types for categories."""
        project_node = resource_tree.root.add(
            "Test Project", allow_expand=True
        )

        resource_tree._add_resource_type_nodes(project_node, "test-project")

        # Collect all resource types
        resource_types = [
            child.data.resource_type
            for child in project_node.children
            if child.data is not None
        ]

        # Should have all expected resource types
        assert ResourceType.CLOUDDNS in resource_types
        assert ResourceType.CLOUDSQL in resource_types
        assert ResourceType.COMPUTE in resource_types
        assert ResourceType.GKE in resource_types
        assert ResourceType.SECRETS in resource_types
        assert ResourceType.IAM in resource_types

    def test_add_resource_type_nodes_sets_project_id(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that _add_resource_type_nodes sets project_id for all categories."""
        project_node = resource_tree.root.add(
            "Test Project", allow_expand=True
        )

        resource_tree._add_resource_type_nodes(project_node, "my-test-project")

        # All children should have the correct project_id
        for child in project_node.children:
            if child.data is not None:
                assert child.data.project_id == "my-test-project"


class TestEmptyProjectCleanup:
    """Tests for automatic cleanup of empty project nodes."""

    @pytest.mark.asyncio
    async def test_remove_empty_project_after_clouddns_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that project is removed when CloudDNS is empty and it's the last resource type."""
        # Create a project node with only CloudDNS category
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Empty Project", data=project_node_data, allow_expand=True
        )

        # Add only CloudDNS category node
        clouddns_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS,
            resource_id="empty-project:clouddns",
            project_id="empty-project",
        )
        clouddns_node = project_node.add(
            "🌐 Cloud DNS", data=clouddns_data, allow_expand=True
        )

        # Mock the ResourceState to return empty list
        with patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []

            # Load the DNS zones (should remove CloudDNS node and then project node)
            await resource_tree._load_dns_zones(clouddns_node)

        # Verify both CloudDNS node and project node were removed
        assert clouddns_node not in project_node.children
        assert project_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_remove_empty_project_after_cloudsql_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that project is removed when CloudSQL is empty and it's the last resource type."""
        # Create a project node with only CloudSQL category
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Empty Project", data=project_node_data, allow_expand=True
        )

        # Add only CloudSQL category node
        cloudsql_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDSQL,
            resource_id="empty-project:cloudsql",
            project_id="empty-project",
        )
        cloudsql_node = project_node.add(
            "☁️  Cloud SQL", data=cloudsql_data, allow_expand=True
        )

        # Mock the ResourceState to return empty list
        with patch.object(resource_tree._state, "load_cloudsql_instances", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []

            # Load the instances (should remove CloudSQL node and then project node)
            await resource_tree._load_cloudsql_instances(cloudsql_node)

        # Verify both CloudSQL node and project node were removed
        assert cloudsql_node not in project_node.children
        assert project_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_remove_empty_project_after_compute_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that project is removed when Compute is empty and it's the last resource type."""
        # Create a project node with only Compute category
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Empty Project", data=project_node_data, allow_expand=True
        )

        # Add only Compute category node
        compute_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE,
            resource_id="empty-project:compute",
            project_id="empty-project",
        )
        compute_node = project_node.add(
            "💻 Instance Groups", data=compute_data, allow_expand=True
        )

        # Mock the Compute service to return empty list
        with patch("sequel.widgets.resource_tree.get_compute_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_instance_groups = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            # Load the instance groups (should remove Compute node and then project node)
            await resource_tree._load_instance_groups(compute_node)

        # Verify both Compute node and project node were removed
        assert compute_node not in project_node.children
        assert project_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_remove_empty_project_after_gke_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that project is removed when GKE is empty and it's the last resource type."""
        # Create a project node with only GKE category
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Empty Project", data=project_node_data, allow_expand=True
        )

        # Add only GKE category node
        gke_data = ResourceTreeNode(
            resource_type=ResourceType.GKE,
            resource_id="empty-project:gke",
            project_id="empty-project",
        )
        gke_node = project_node.add(
            "⎈  GKE Clusters", data=gke_data, allow_expand=True
        )

        # Mock the GKE service to return empty list
        with patch("sequel.widgets.resource_tree.get_gke_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_clusters = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            # Load the clusters (should remove GKE node and then project node)
            await resource_tree._load_gke_clusters(gke_node)

        # Verify both GKE node and project node were removed
        assert gke_node not in project_node.children
        assert project_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_remove_empty_project_after_secrets_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that project is removed when Secrets is empty and it's the last resource type."""
        # Create a project node with only Secrets category
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Empty Project", data=project_node_data, allow_expand=True
        )

        # Add only Secrets category node
        secrets_data = ResourceTreeNode(
            resource_type=ResourceType.SECRETS,
            resource_id="empty-project:secrets",
            project_id="empty-project",
        )
        secrets_node = project_node.add(
            "🔐 Secrets", data=secrets_data, allow_expand=True
        )

        # Mock the ResourceState to return empty list
        with patch.object(resource_tree._state, "load_secrets", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []

            # Load the secrets (should remove Secrets node and then project node)
            await resource_tree._load_secrets(secrets_node)

        # Verify both Secrets node and project node were removed
        assert secrets_node not in project_node.children
        assert project_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_remove_empty_project_after_iam_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that project is removed when IAM is empty and it's the last resource type."""
        # Create a project node with only IAM category
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Empty Project", data=project_node_data, allow_expand=True
        )

        # Add only IAM category node
        iam_data = ResourceTreeNode(
            resource_type=ResourceType.IAM,
            resource_id="empty-project:iam",
            project_id="empty-project",
        )
        iam_node = project_node.add(
            "👤 Service Accounts", data=iam_data, allow_expand=True
        )

        # Mock the IAM service to return empty list
        with patch("sequel.widgets.resource_tree.get_iam_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_service_accounts = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            # Load the service accounts (should remove IAM node and then project node)
            await resource_tree._load_service_accounts(iam_node)

        # Verify both IAM node and project node were removed
        assert iam_node not in project_node.children
        assert project_node not in resource_tree.root.children

    @pytest.mark.asyncio
    async def test_keep_project_with_some_resources(
        self, resource_tree: ResourceTree, sample_dns_zone: ManagedZone
    ) -> None:
        """Test that project is kept when at least one resource type has resources."""
        # Create a project node with two categories
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="mixed-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Mixed Project", data=project_node_data, allow_expand=True
        )

        # Add CloudDNS category node (will have resources)
        clouddns_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS,
            resource_id="mixed-project:clouddns",
            project_id="mixed-project",
        )
        clouddns_node = project_node.add(
            "🌐 Cloud DNS", data=clouddns_data, allow_expand=True
        )

        # Add CloudSQL category node (will be empty)
        cloudsql_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDSQL,
            resource_id="mixed-project:cloudsql",
            project_id="mixed-project",
        )
        cloudsql_node = project_node.add(
            "☁️  Cloud SQL", data=cloudsql_data, allow_expand=True
        )

        # Mock ResourceState to return zones
        with patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_load_dns:
            mock_load_dns.return_value = [sample_dns_zone]

            # Load DNS zones (should add zones)
            await resource_tree._load_dns_zones(clouddns_node)

        # Mock ResourceState to return empty list
        with patch.object(resource_tree._state, "load_cloudsql_instances", new_callable=AsyncMock) as mock_load_sql:
            mock_load_sql.return_value = []

            # Load CloudSQL instances (should remove CloudSQL node but keep project)
            await resource_tree._load_cloudsql_instances(cloudsql_node)

        # Verify CloudSQL node was removed but project node was kept
        assert cloudsql_node not in project_node.children
        assert project_node in resource_tree.root.children
        # CloudDNS node should still be there with children
        assert clouddns_node in project_node.children
        assert len(clouddns_node.children) > 0

    @pytest.mark.asyncio
    async def test_project_not_removed_after_all_categories_populated(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that project is not removed when it still has unexpanded categories."""
        # Create a project node with multiple categories
        project_node_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="full-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Full Project", data=project_node_data, allow_expand=True
        )

        # Add all resource type nodes
        resource_tree._add_resource_type_nodes(project_node, "full-project")

        # Get the CloudDNS node
        clouddns_node = None
        for child in project_node.children:
            if child.data and child.data.resource_type == ResourceType.CLOUDDNS:
                clouddns_node = child
                break

        assert clouddns_node is not None

        # Mock ResourceState to return empty list
        with patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []

            # Load DNS zones (should remove CloudDNS node but keep project)
            await resource_tree._load_dns_zones(clouddns_node)

        # Verify CloudDNS node was removed but project still has other categories
        assert clouddns_node not in project_node.children
        assert project_node in resource_tree.root.children
        # Project should still have 7 other resource type nodes (added Firewall and LoadBalancer)
        assert len(project_node.children) == 7


class TestAutomaticCleanup:
    """Tests for automatic cleanup of empty nodes after tree loading."""

    @pytest.mark.asyncio
    async def test_cleanup_empty_nodes_removes_all_empty_projects(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that cleanup_empty_nodes removes projects with all empty resource types."""
        # Create two project nodes
        project1_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project-1",
            resource_data=None,
        )
        project1_node = resource_tree.root.add(
            "📁 Empty Project 1", data=project1_data, allow_expand=True
        )
        resource_tree._add_resource_type_nodes(project1_node, "empty-project-1")

        project2_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="empty-project-2",
            resource_data=None,
        )
        project2_node = resource_tree.root.add(
            "📁 Empty Project 2", data=project2_data, allow_expand=True
        )
        resource_tree._add_resource_type_nodes(project2_node, "empty-project-2")

        # Mock app for notifications
        mock_app = MagicMock()

        # Mock ResourceState to return empty lists for all resource types
        with (
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
            patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_dns,
            patch.object(resource_tree._state, "load_cloudsql_instances", new_callable=AsyncMock) as mock_sql,
            patch.object(resource_tree._state, "load_compute_groups", new_callable=AsyncMock) as mock_compute,
            patch.object(resource_tree._state, "load_firewalls", new_callable=AsyncMock) as mock_firewalls,
            patch.object(resource_tree._state, "load_loadbalancers", new_callable=AsyncMock) as mock_loadbalancers,
            patch.object(resource_tree._state, "load_gke_clusters", new_callable=AsyncMock) as mock_gke,
            patch.object(resource_tree._state, "load_secrets", new_callable=AsyncMock) as mock_secrets,
            patch.object(resource_tree._state, "load_iam_accounts", new_callable=AsyncMock) as mock_iam,
        ):
            # All methods return empty lists
            mock_dns.return_value = []
            mock_sql.return_value = []
            mock_compute.return_value = []
            mock_firewalls.return_value = []
            mock_loadbalancers.return_value = []
            mock_gke.return_value = []
            mock_secrets.return_value = []
            mock_iam.return_value = []

            # Run cleanup
            await resource_tree.cleanup_empty_nodes()

        # Both projects should be removed
        assert project1_node not in resource_tree.root.children
        assert project2_node not in resource_tree.root.children
        assert len(resource_tree.root.children) == 0

    @pytest.mark.asyncio
    async def test_cleanup_empty_nodes_keeps_projects_with_resources(
        self, resource_tree: ResourceTree, sample_dns_zone: ManagedZone
    ) -> None:
        """Test that cleanup_empty_nodes keeps projects with at least one non-empty resource type."""
        # Create a project node
        project_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="mixed-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Mixed Project", data=project_data, allow_expand=True
        )
        resource_tree._add_resource_type_nodes(project_node, "mixed-project")

        # Mock app for notifications
        mock_app = MagicMock()

        # Mock ResourceState: CloudDNS has zones, everything else is empty
        with (
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
            patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_dns,
            patch.object(resource_tree._state, "load_cloudsql_instances", new_callable=AsyncMock) as mock_sql,
            patch.object(resource_tree._state, "load_compute_groups", new_callable=AsyncMock) as mock_compute,
            patch.object(resource_tree._state, "load_firewalls", new_callable=AsyncMock) as mock_firewalls,
            patch.object(resource_tree._state, "load_loadbalancers", new_callable=AsyncMock) as mock_loadbalancers,
            patch.object(resource_tree._state, "load_gke_clusters", new_callable=AsyncMock) as mock_gke,
            patch.object(resource_tree._state, "load_secrets", new_callable=AsyncMock) as mock_secrets,
            patch.object(resource_tree._state, "load_iam_accounts", new_callable=AsyncMock) as mock_iam,
        ):
            # CloudDNS returns zones
            mock_dns.return_value = [sample_dns_zone]

            # All other methods return empty lists
            mock_sql.return_value = []
            mock_compute.return_value = []
            mock_firewalls.return_value = []
            mock_loadbalancers.return_value = []
            mock_gke.return_value = []
            mock_secrets.return_value = []
            mock_iam.return_value = []

            # Run cleanup
            await resource_tree.cleanup_empty_nodes()

        # Project should be kept because CloudDNS has resources
        assert project_node in resource_tree.root.children
        # Project should only have CloudDNS node left
        assert len(project_node.children) == 1
        assert project_node.children[0].data.resource_type == ResourceType.CLOUDDNS

    @pytest.mark.asyncio
    async def test_cleanup_empty_nodes_handles_errors_gracefully(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that cleanup_empty_nodes handles errors in individual resource loads."""
        # Create a project node
        project_data = ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="error-project",
            resource_data=None,
        )
        project_node = resource_tree.root.add(
            "📁 Error Project", data=project_data, allow_expand=True
        )
        resource_tree._add_resource_type_nodes(project_node, "error-project")

        # Mock app for notifications
        mock_app = MagicMock()

        # Mock ResourceState: CloudDNS throws error, everything else is empty
        with (
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
            patch.object(resource_tree._state, "load_dns_zones", new_callable=AsyncMock) as mock_dns,
            patch.object(resource_tree._state, "load_cloudsql_instances", new_callable=AsyncMock) as mock_sql,
            patch.object(resource_tree._state, "load_compute_groups", new_callable=AsyncMock) as mock_compute,
            patch.object(resource_tree._state, "load_firewalls", new_callable=AsyncMock) as mock_firewalls,
            patch.object(resource_tree._state, "load_loadbalancers", new_callable=AsyncMock) as mock_loadbalancers,
            patch.object(resource_tree._state, "load_gke_clusters", new_callable=AsyncMock) as mock_gke,
            patch.object(resource_tree._state, "load_secrets", new_callable=AsyncMock) as mock_secrets,
            patch.object(resource_tree._state, "load_iam_accounts", new_callable=AsyncMock) as mock_iam,
        ):
            # CloudDNS throws error
            mock_dns.side_effect = Exception("API Error")

            # All other methods return empty lists
            mock_sql.return_value = []
            mock_compute.return_value = []
            mock_firewalls.return_value = []
            mock_loadbalancers.return_value = []
            mock_gke.return_value = []
            mock_secrets.return_value = []
            mock_iam.return_value = []

            # Run cleanup - should not raise exception
            await resource_tree.cleanup_empty_nodes()

        # Project should be removed because all other resource types are empty
        # CloudDNS will still be there because the error prevented removal
        assert project_node not in resource_tree.root.children or len(project_node.children) <= 1
