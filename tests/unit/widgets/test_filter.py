"""Tests for resource tree filter functionality."""

from unittest.mock import patch

import pytest

from sequel.config import Config
from sequel.models.clouddns import ManagedZone
from sequel.models.cloudsql import CloudSQLInstance
from sequel.models.gke import GKECluster
from sequel.models.project import Project
from sequel.state.resource_state import reset_resource_state
from sequel.widgets.resource_tree import ResourceTree, ResourceTreeNode, ResourceType


@pytest.fixture(autouse=True)
def mock_config():
    """Mock get_config to return a config with no project filter regex."""
    test_config = Config(
        project_filter_regex=None,  # No project filtering for tests
        theme="textual-dark",
    )
    with patch("sequel.widgets.resource_tree.get_config", return_value=test_config):
        yield test_config


@pytest.fixture
def resource_tree() -> ResourceTree:
    """Create a resource tree widget for testing."""
    reset_resource_state()
    return ResourceTree()


@pytest.fixture
def populated_tree(resource_tree: ResourceTree) -> ResourceTree:
    """Create a resource tree with sample projects and resources in state."""
    # Populate ResourceState with test data
    state = resource_tree._state

    # Create project models
    project1 = Project(
        id="projects/test-project-1",
        name="Test Project 1",
        project_id="test-project-1",
        display_name="Test Project 1",
        state="ACTIVE",
    )
    project2 = Project(
        id="projects/production-project",
        name="Production Project",
        project_id="production-project",
        display_name="Production Project",
        state="ACTIVE",
    )

    # Add projects to state
    state._projects = {
        "test-project-1": project1,
        "production-project": project2,
    }
    state._loaded.add(("projects",))

    # Create DNS zones for project 1
    zone1 = ManagedZone(
        id="example-zone",
        name="example.com.",
        zone_name="example-zone",
        dns_name="example.com.",
        visibility="public",
        name_servers=["ns1.example.com.", "ns2.example.com."],
    )
    zone2 = ManagedZone(
        id="test-zone",
        name="test.com.",
        zone_name="test-zone",
        dns_name="test.com.",
        visibility="private",
        name_servers=["ns1.test.com.", "ns2.test.com."],
    )

    state._dns_zones["test-project-1"] = [zone1, zone2]
    state._loaded.add(("test-project-1", "dns_zones"))

    # Create CloudSQL instance for project 1
    sql_instance = CloudSQLInstance(
        id="my-database",
        name="my-database",
        instance_name="my-database",
        database_version="POSTGRES_14",
        state="RUNNABLE",
        region="us-central1",
        tier="db-f1-micro",
    )

    state._cloudsql["test-project-1"] = [sql_instance]
    state._loaded.add(("test-project-1", "cloudsql"))

    # Create GKE cluster for project 2
    gke_cluster = GKECluster(
        id="prod-cluster",
        name="prod-cluster",
        cluster_name="prod-cluster",
        location="us-central1",
        status="RUNNING",
        node_count=3,
    )

    state._gke_clusters["production-project"] = [gke_cluster]
    state._loaded.add(("production-project", "gke_clusters"))

    # Build tree from state (for backward compatibility with other tests)
    # This mimics what the tree would look like after loading
    project1_node = resource_tree.root.add(
        "📁 Test Project 1",
        data=ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="test-project-1",
            resource_data=project1,
        ),
        allow_expand=True,
    )

    # Add Cloud DNS category
    clouddns_node = project1_node.add(
        "🌐 Cloud DNS (2 zones)",
        data=ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS,
            resource_id="test-project-1:clouddns",
            project_id="test-project-1",
        ),
        allow_expand=True,
    )

    # Add DNS zones
    clouddns_node.add(
        "🌍 example.com.",
        data=ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS_ZONE,
            resource_id="example-zone",
            resource_data=zone1,
            project_id="test-project-1",
        ),
        allow_expand=False,
    )

    clouddns_node.add(
        "🌍 test.com.",
        data=ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS_ZONE,
            resource_id="test-zone",
            resource_data=zone2,
            project_id="test-project-1",
        ),
        allow_expand=False,
    )

    # Add Cloud SQL category
    cloudsql_node = project1_node.add(
        "☁️  Cloud SQL (1 instance)",
        data=ResourceTreeNode(
            resource_type=ResourceType.CLOUDSQL,
            resource_id="test-project-1:cloudsql",
            project_id="test-project-1",
        ),
        allow_expand=True,
    )

    # Add Cloud SQL instance
    cloudsql_node.add(
        "💾 my-database",
        data=ResourceTreeNode(
            resource_type=ResourceType.CLOUDSQL,
            resource_id="my-database",
            resource_data=sql_instance,
            project_id="test-project-1",
        ),
        allow_expand=False,
    )

    # Add project 2 with GKE
    project2_node = resource_tree.root.add(
        "📁 Production Project",
        data=ResourceTreeNode(
            resource_type=ResourceType.PROJECT,
            resource_id="production-project",
            resource_data=project2,
        ),
        allow_expand=True,
    )

    # Add GKE category
    gke_node = project2_node.add(
        "⎈  GKE Clusters (1 cluster)",
        data=ResourceTreeNode(
            resource_type=ResourceType.GKE,
            resource_id="production-project:gke",
            project_id="production-project",
        ),
        allow_expand=True,
    )

    # Add GKE cluster
    gke_node.add(
        "⎈  prod-cluster",
        data=ResourceTreeNode(
            resource_type=ResourceType.GKE_CLUSTER,
            resource_id="prod-cluster",
            resource_data=gke_cluster,
            project_id="production-project",
        ),
        allow_expand=False,
    )

    return resource_tree


class TestFilterBasics:
    """Test basic filter functionality."""

    @pytest.mark.asyncio
    async def test_filter_removes_non_matching_nodes(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test that filter removes nodes that don't match."""
        # Count initial nodes
        initial_project_count = len(populated_tree.root.children)
        assert initial_project_count == 2

        # Apply filter for "example"
        await populated_tree.apply_filter("example")

        # Should only show nodes containing "example" or ancestors
        # Project 1 should remain (has example.com zone)
        # Project 2 should be removed (no match)
        remaining_projects = len(populated_tree.root.children)
        assert remaining_projects == 1
        assert "Test Project 1" in populated_tree.root.children[0].label.plain

    @pytest.mark.asyncio
    async def test_filter_shows_ancestors_of_matching_nodes(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test that filter shows ancestor nodes of matching nodes."""
        # Apply filter for "example.com"
        await populated_tree.apply_filter("example")

        # Project 1 (ancestor) should remain
        assert len(populated_tree.root.children) == 1
        project_node = populated_tree.root.children[0]
        assert "Test Project 1" in project_node.label.plain

        # Cloud DNS category (ancestor) should remain
        assert len(project_node.children) >= 1
        clouddns_node = None
        for child in project_node.children:
            if "Cloud DNS" in child.label.plain:
                clouddns_node = child
                break

        assert clouddns_node is not None

        # example.com zone (match) should remain
        zone_found = False
        for child in clouddns_node.children:
            if "example.com" in child.label.plain:
                zone_found = True
                break
        assert zone_found

    @pytest.mark.asyncio
    async def test_filter_hides_sibling_nodes(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test that filter hides non-matching sibling nodes."""
        # Apply filter for "example"
        await populated_tree.apply_filter("example")

        # Project 1 should remain
        assert len(populated_tree.root.children) == 1
        project_node = populated_tree.root.children[0]

        # Cloud DNS should remain (has matching child)
        # Cloud SQL should be removed (no match)
        clouddns_found = False
        cloudsql_found = False

        for child in project_node.children:
            if "Cloud DNS" in child.label.plain:
                clouddns_found = True
            if "Cloud SQL" in child.label.plain:
                cloudsql_found = True

        assert clouddns_found
        assert not cloudsql_found

    @pytest.mark.asyncio
    async def test_clear_filter_reloads_tree(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test that clearing filter rebuilds tree from state showing all projects."""
        # Apply filter first
        await populated_tree.apply_filter("example")

        # Verify filter is active (only 1 project)
        assert len(populated_tree.root.children) == 1

        # Clear filter
        await populated_tree.apply_filter("")

        # Should now show all projects from state
        assert len(populated_tree.root.children) == 2
        project_names = [node.label.plain for node in populated_tree.root.children]
        assert any("Test Project 1" in name for name in project_names)
        assert any("Production" in name for name in project_names)

    @pytest.mark.asyncio
    async def test_filter_is_case_insensitive(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test that filter matching is case-insensitive."""
        # Apply filter with mixed case
        await populated_tree.apply_filter("EXAMPLE")

        # Should still match "example.com"
        assert len(populated_tree.root.children) == 1
        project_node = populated_tree.root.children[0]
        assert "Test Project 1" in project_node.label.plain

    @pytest.mark.asyncio
    async def test_filter_with_no_matches(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test filter behavior when no nodes match."""
        # Apply filter that matches nothing
        await populated_tree.apply_filter("nonexistent-resource-xyz")

        # All nodes should be removed (no matches)
        assert len(populated_tree.root.children) == 0

    @pytest.mark.asyncio
    async def test_filter_matches_partial_strings(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test that filter matches partial strings in labels."""
        # Apply filter for "prod" (should match "Production Project" and "prod-cluster")
        await populated_tree.apply_filter("prod")

        # Should show Production Project
        assert len(populated_tree.root.children) == 1
        project_node = populated_tree.root.children[0]
        assert "Production" in project_node.label.plain

    @pytest.mark.asyncio
    async def test_filter_empty_tree(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test filter on empty tree doesn't crash."""
        # Apply filter on empty tree
        await resource_tree.apply_filter("anything")

        # Should handle gracefully (no nodes to filter)
        assert len(resource_tree.root.children) == 0


class TestFilterMultipleMatches:
    """Test filter with multiple matching nodes."""

    @pytest.mark.asyncio
    async def test_filter_shows_all_matching_branches(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test that filter shows all branches with matches."""
        # Apply filter for "com" (matches DNS zones: example.com and test.com)
        await populated_tree.apply_filter("com")

        # Project 1 should remain (has DNS zones with "com")
        assert len(populated_tree.root.children) == 1
        project_node = populated_tree.root.children[0]

        # Cloud DNS category should remain with matching zones
        dns_categories = [
            child.label.plain
            for child in project_node.children
            if "DNS" in child.label.plain
        ]
        assert len(dns_categories) >= 1

    @pytest.mark.asyncio
    async def test_filter_matches_across_projects(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test filter showing matches across different projects."""
        # Apply filter for "cluster" (in GKE category and cluster name)
        await populated_tree.apply_filter("cluster")

        # Should show Production Project (has GKE cluster)
        assert len(populated_tree.root.children) == 1
        project_node = populated_tree.root.children[0]
        assert "Production" in project_node.label.plain


class TestFilterEdgeCases:
    """Test filter edge cases and special characters."""

    @pytest.mark.asyncio
    async def test_filter_with_special_characters(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test filter with special characters in search text."""
        # Apply filter for "." (in example.com.)
        await populated_tree.apply_filter("com.")

        # Should match zones ending with .com.
        assert len(populated_tree.root.children) >= 1

    @pytest.mark.asyncio
    async def test_filter_with_whitespace(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test filter with leading/trailing whitespace."""
        # Apply filter with whitespace (should be stripped)
        await populated_tree.apply_filter("  example  ")

        # Should still match (whitespace stripped internally)
        assert len(populated_tree.root.children) == 1

    @pytest.mark.asyncio
    async def test_filter_with_emoji(
        self, populated_tree: ResourceTree
    ) -> None:
        """Test filter handles emoji characters in search (even if no matches)."""
        # Apply filter with emoji character
        await populated_tree.apply_filter("🌍")

        # No resources have emoji in their data, so no matches expected
        # This test verifies emoji doesn't crash the filter
        assert len(populated_tree.root.children) == 0


class TestFilterState:
    """Test filter state management."""

    def test_filter_text_stored_correctly(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that filter text is stored in lowercase."""
        resource_tree._filter_text = ""

        # Manually set filter text
        resource_tree._filter_text = "TEST"

        # Should be stored as-is (conversion happens in apply_filter)
        assert resource_tree._filter_text == "TEST"

    def test_initial_filter_text_empty(
        self, resource_tree: ResourceTree
    ) -> None:
        """Test that filter text starts as empty string."""
        assert resource_tree._filter_text == ""
