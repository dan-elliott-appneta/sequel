"""Resource tree widget for displaying GCP resources in a hierarchical view."""

import re
from typing import Any

from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from sequel.config import get_config
from sequel.services.cloudsql import get_cloudsql_service
from sequel.services.compute import get_compute_service
from sequel.services.gke import get_gke_service
from sequel.services.iam import get_iam_service
from sequel.services.projects import get_project_service
from sequel.services.secrets import get_secret_manager_service
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceType:
    """Constants for resource types."""

    PROJECT = "project"
    CLOUDSQL = "cloudsql"
    COMPUTE = "compute"
    COMPUTE_INSTANCE = "compute_instance"
    GKE = "gke"
    GKE_NODE = "gke_node"
    SECRETS = "secrets"
    IAM = "iam"
    IAM_ROLE = "iam_role"


class ResourceTreeNode:
    """Data class for tree node metadata."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        resource_data: Any = None,
        project_id: str | None = None,
        location: str | None = None,
        zone: str | None = None,
    ) -> None:
        """Initialize resource tree node.

        Args:
            resource_type: Type of resource (project, cloudsql, etc.)
            resource_id: Unique identifier for the resource
            resource_data: The actual resource data/model
            project_id: Parent project ID (if applicable)
            location: GCP location/region (for GKE, etc.)
            zone: GCP zone (for Compute, etc.)
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.resource_data = resource_data
        self.project_id = project_id
        self.location = location
        self.zone = zone
        self.loaded = False


class ResourceTree(Tree[ResourceTreeNode]):
    """Tree widget for displaying GCP resources hierarchically.

    The tree structure is:
    - Projects (root level)
      - CloudSQL Instances
      - Instance Groups
      - GKE Clusters
      - Secrets
      - Service Accounts
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the resource tree."""
        super().__init__("GCP Resources", *args, **kwargs)
        self.root.expand()

    async def load_projects(self) -> None:
        """Load all projects as root-level nodes."""
        try:
            logger.info("Loading projects into tree")
            project_service = await get_project_service()
            projects = await project_service.list_projects()

            # Apply project filter if configured
            config = get_config()
            if config.project_filter_regex:
                try:
                    pattern = re.compile(config.project_filter_regex)
                    filtered_projects = [
                        p for p in projects
                        if pattern.match(p.project_id) or pattern.match(p.display_name)
                    ]
                    logger.info(
                        f"Filtered {len(projects)} projects to {len(filtered_projects)} "
                        f"using regex: {config.project_filter_regex}"
                    )
                    projects = filtered_projects
                except re.error as e:
                    logger.error(f"Invalid project filter regex: {e}")

            # Clear existing nodes
            self.root.remove_children()

            # Add project nodes
            for project in projects:
                node_data = ResourceTreeNode(
                    resource_type=ResourceType.PROJECT,
                    resource_id=project.project_id,
                    resource_data=project,
                )
                project_node = self.root.add(
                    f"📁 {project.display_name}",
                    data=node_data,
                )
                # Add placeholder children for lazy loading
                self._add_resource_type_nodes(project_node, project.project_id)

            logger.info(f"Loaded {len(projects)} projects")

        except Exception as e:
            logger.error(f"Failed to load projects: {e}")

    def _add_resource_type_nodes(self, project_node: TreeNode[ResourceTreeNode], project_id: str) -> None:
        """Add resource type category nodes to a project.

        Args:
            project_node: Parent project node
            project_id: Project ID
        """
        # Add CloudSQL
        cloudsql_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDSQL,
            resource_id=f"{project_id}:cloudsql",
            project_id=project_id,
        )
        project_node.add("☁️  Cloud SQL", data=cloudsql_data, allow_expand=True)

        # Add Compute (Instance Groups)
        compute_data = ResourceTreeNode(
            resource_type=ResourceType.COMPUTE,
            resource_id=f"{project_id}:compute",
            project_id=project_id,
        )
        project_node.add("💻 Instance Groups", data=compute_data, allow_expand=True)

        # Add GKE
        gke_data = ResourceTreeNode(
            resource_type=ResourceType.GKE,
            resource_id=f"{project_id}:gke",
            project_id=project_id,
        )
        project_node.add("⎈  GKE Clusters", data=gke_data, allow_expand=True)

        # Add Secrets
        secrets_data = ResourceTreeNode(
            resource_type=ResourceType.SECRETS,
            resource_id=f"{project_id}:secrets",
            project_id=project_id,
        )
        project_node.add("🔐 Secrets", data=secrets_data, allow_expand=True)

        # Add IAM
        iam_data = ResourceTreeNode(
            resource_type=ResourceType.IAM,
            resource_id=f"{project_id}:iam",
            project_id=project_id,
        )
        project_node.add("👤 Service Accounts", data=iam_data, allow_expand=True)

    async def _on_tree_node_expanded(self, event: Tree.NodeExpanded[ResourceTreeNode]) -> None:
        """Handle tree node expansion with lazy loading.

        Args:
            event: Node expanded event
        """
        node = event.node
        if node.data is None:
            return

        # Skip if already loaded
        if node.data.loaded:
            return

        try:
            # Load resources based on type
            if node.data.resource_type == ResourceType.CLOUDSQL:
                await self._load_cloudsql_instances(node)
            elif node.data.resource_type == ResourceType.COMPUTE:
                await self._load_instance_groups(node)
            elif node.data.resource_type == ResourceType.COMPUTE_INSTANCE:
                await self._load_instances_in_group(node)
            elif node.data.resource_type == ResourceType.GKE:
                await self._load_gke_clusters(node)
            elif node.data.resource_type == ResourceType.GKE_NODE:
                await self._load_cluster_nodes(node)
            elif node.data.resource_type == ResourceType.SECRETS:
                await self._load_secrets(node)
            elif node.data.resource_type == ResourceType.IAM:
                await self._load_service_accounts(node)
            elif node.data.resource_type == ResourceType.IAM_ROLE:
                await self._load_service_account_roles(node)

            node.data.loaded = True

        except Exception as e:
            logger.error(f"Failed to load resources: {e}")
            node.add_leaf(f"Error: {e}")

    async def _load_cloudsql_instances(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load Cloud SQL instances for a project."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading Cloud SQL instances for {project_id}")

        service = await get_cloudsql_service()
        instances = await service.list_instances(project_id)

        parent_node.remove_children()

        if not instances:
            # Remove the parent node if there are no instances
            parent_node.remove()
            return

        for instance in instances:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.CLOUDSQL,
                resource_id=instance.instance_name,
                resource_data=instance,
                project_id=project_id,
            )
            status_icon = "✓" if instance.is_running() else "✗"
            parent_node.add_leaf(
                f"{status_icon} {instance.instance_name} ({instance.database_version})",
                data=node_data,
            )

    async def _load_instance_groups(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load Compute Engine instance groups for a project."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading instance groups for {project_id}")

        service = await get_compute_service()
        groups = await service.list_instance_groups(project_id)

        parent_node.remove_children()

        if not groups:
            # Remove the parent node if there are no instance groups
            parent_node.remove()
            return

        for group in groups:
            # Extract zone from self_link if available
            zone = None
            if hasattr(group, 'zone') and group.zone:
                # Zone is typically like "https://www.googleapis.com/compute/v1/projects/PROJECT/zones/ZONE"
                zone_parts = group.zone.split('/')
                if len(zone_parts) > 0:
                    zone = zone_parts[-1]

            node_data = ResourceTreeNode(
                resource_type=ResourceType.COMPUTE_INSTANCE,
                resource_id=group.group_name,
                resource_data=group,
                project_id=project_id,
                zone=zone,
            )
            type_icon = "M" if group.is_managed else "U"
            # Make instance groups expandable to show instances
            parent_node.add(
                f"[{type_icon}] {group.group_name} (size: {group.size})",
                data=node_data,
                allow_expand=True,
            )

    async def _load_gke_clusters(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load GKE clusters for a project."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading GKE clusters for {project_id}")

        service = await get_gke_service()
        clusters = await service.list_clusters(project_id)

        parent_node.remove_children()

        if not clusters:
            # Remove the parent node if there are no clusters
            parent_node.remove()
            return

        for cluster in clusters:
            # Extract location from cluster
            location = cluster.location if hasattr(cluster, 'location') else None

            node_data = ResourceTreeNode(
                resource_type=ResourceType.GKE_NODE,
                resource_id=cluster.cluster_name,
                resource_data=cluster,
                project_id=project_id,
                location=location,
            )
            status_icon = "✓" if cluster.is_running() else "✗"
            # Make clusters expandable to show nodes
            parent_node.add(
                f"{status_icon} {cluster.cluster_name} (nodes: {cluster.node_count})",
                data=node_data,
                allow_expand=True,
            )

    async def _load_secrets(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load secrets for a project."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading secrets for {project_id}")

        service = await get_secret_manager_service()
        secrets = await service.list_secrets(project_id)

        parent_node.remove_children()

        if not secrets:
            # Remove the parent node if there are no secrets
            parent_node.remove()
            return

        for secret in secrets:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.SECRETS,
                resource_id=secret.secret_name,
                resource_data=secret,
                project_id=project_id,
            )
            parent_node.add_leaf(
                f"🔑 {secret.secret_name}",
                data=node_data,
            )

    async def _load_service_accounts(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load service accounts for a project."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading service accounts for {project_id}")

        service = await get_iam_service()
        accounts = await service.list_service_accounts(project_id)

        parent_node.remove_children()

        if not accounts:
            # Remove the parent node if there are no service accounts
            parent_node.remove()
            return

        for account in accounts:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.IAM_ROLE,
                resource_id=account.email,
                resource_data=account,
                project_id=project_id,
            )
            status_icon = "✓" if account.is_enabled() else "✗"
            # Make service accounts expandable to show IAM roles
            parent_node.add(
                f"{status_icon} {account.email}",
                data=node_data,
                allow_expand=True,
            )

    async def _load_service_account_roles(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load IAM roles for a service account."""
        if parent_node.data is None:
            return

        parent_node.remove_children()

        # For now, show a placeholder - full implementation would fetch IAM policy bindings
        parent_node.add_leaf("📋 Roles (expand service account for details)")

    async def _load_cluster_nodes(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load nodes for a GKE cluster."""
        if parent_node.data is None or parent_node.data.resource_data is None:
            return

        cluster = parent_node.data.resource_data
        parent_node.remove_children()

        # Show node pools and node count from cluster data
        if hasattr(cluster, 'node_count') and cluster.node_count > 0:
            for i in range(cluster.node_count):
                parent_node.add_leaf(f"🖥️  Node {i+1}")
        else:
            parent_node.remove()

    async def _load_instances_in_group(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load instances in an instance group."""
        if parent_node.data is None or parent_node.data.resource_data is None:
            return

        group = parent_node.data.resource_data
        parent_node.remove_children()

        # Show instance count from group data
        if hasattr(group, 'size') and group.size > 0:
            for i in range(min(group.size, 10)):  # Limit to 10 for now
                parent_node.add_leaf(f"💻 Instance {i+1}")
            if group.size > 10:
                parent_node.add_leaf(f"... and {group.size - 10} more")
        else:
            parent_node.remove()
