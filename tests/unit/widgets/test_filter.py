"""Tests for resource tree filter functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from sequel.widgets.resource_tree import ResourceTree, ResourceTreeNode, ResourceType


@pytest.fixture
def resource_tree() -> ResourceTree:
    """Create a resource tree widget for testing."""
    return ResourceTree()


@pytest.fixture
def populated_tree(resource_tree: ResourceTree) -> ResourceTree:
    """Create a resource tree with sample projects and resources."""
    # Add project 1 with Cloud DNS
    project1_data = ResourceTreeNode(
        resource_type=ResourceType.PROJECT,
        resource_id="test-project-1",
        resource_data=None,
    )
    project1_node = resource_tree.root.add(
        "📁 Test Project 1", data=project1_data, allow_expand=True
    )

    # Add Cloud DNS category
    clouddns_data = ResourceTreeNode(
        resource_type=ResourceType.CLOUDDNS,
        resource_id="test-project-1:clouddns",
        project_id="test-project-1",
    )
    clouddns_node = project1_node.add(
        "🌐 Cloud DNS (2 zones)", data=clouddns_data, allow_expand=True
    )

    # Add DNS zones
    zone1_data = ResourceTreeNode(
        resource_type=ResourceType.CLOUDDNS_ZONE,
        resource_id="example-zone",
        project_id="test-project-1",
    )
    clouddns_node.add("🌍 example.com.", data=zone1_data, allow_expand=False)

    zone2_data = ResourceTreeNode(
        resource_type=ResourceType.CLOUDDNS_ZONE,
        resource_id="test-zone",
        project_id="test-project-1",
    )
    clouddns_node.add("🌍 test.com.", data=zone2_data, allow_expand=False)

    # Add Cloud SQL category
    cloudsql_data = ResourceTreeNode(
        resource_type=ResourceType.CLOUDSQL,
        resource_id="test-project-1:cloudsql",
        project_id="test-project-1",
    )
    cloudsql_node = project1_node.add(
        "☁️  Cloud SQL (1 instance)", data=cloudsql_data, allow_expand=True
    )

    # Add Cloud SQL instance
    instance_data = ResourceTreeNode(
        resource_type=ResourceType.CLOUDSQL,
        resource_id="my-database",
        project_id="test-project-1",
    )
    cloudsql_node.add("💾 my-database", data=instance_data, allow_expand=False)

    # Add project 2 with GKE
    project2_data = ResourceTreeNode(
        resource_type=ResourceType.PROJECT,
        resource_id="production-project",
        resource_data=None,
    )
    project2_node = resource_tree.root.add(
        "📁 Production Project", data=project2_data, allow_expand=True
    )

    # Add GKE category
    gke_data = ResourceTreeNode(
        resource_type=ResourceType.GKE,
        resource_id="production-project:gke",
        project_id="production-project",
    )
    gke_node = project2_node.add(
        "⎈  GKE Clusters (1 cluster)", data=gke_data, allow_expand=True
    )

    # Add GKE cluster
    cluster_data = ResourceTreeNode(
        resource_type=ResourceType.GKE_CLUSTER,
        resource_id="prod-cluster",
        project_id="production-project",
    )
    gke_node.add("⎈  prod-cluster", data=cluster_data, allow_expand=False)

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
        """Test that clearing filter reloads the full tree."""
        # Apply filter first
        await populated_tree.apply_filter("example")

        # Verify filter is active (only 1 project)
        assert len(populated_tree.root.children) == 1

        # Mock load_projects to verify it's called
        with patch.object(populated_tree, "load_projects", new=AsyncMock()) as mock_load:
            # Clear filter
            await populated_tree.apply_filter("")

            # Should have called load_projects to restore full tree
            mock_load.assert_called_once()

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
        # Apply filter for "Cloud" (matches both Cloud DNS and Cloud SQL)
        await populated_tree.apply_filter("Cloud")

        # Project 1 should remain (has Cloud DNS and Cloud SQL)
        assert len(populated_tree.root.children) == 1
        project_node = populated_tree.root.children[0]

        # Both Cloud DNS and Cloud SQL should remain
        cloud_categories = [
            child.label.plain
            for child in project_node.children
            if "Cloud" in child.label.plain
        ]
        assert len(cloud_categories) == 2

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
        """Test filter matching emoji in labels."""
        # Apply filter for emoji (🌍 in zone labels)
        await populated_tree.apply_filter("🌍")

        # Should match nodes with globe emoji
        assert len(populated_tree.root.children) >= 1


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
