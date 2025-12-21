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
    GKE = "gke"
    SECRETS = "secrets"
    IAM = "iam"


class ResourceTreeNode:
    """Data class for tree node metadata."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        resource_data: Any = None,
        project_id: str | None = None,
    ) -> None:
        """Initialize resource tree node.

        Args:
            resource_type: Type of resource (project, cloudsql, etc.)
            resource_id: Unique identifier for the resource
            resource_data: The actual resource data/model
            project_id: Parent project ID (if applicable)
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.resource_data = resource_data
        self.project_id = project_id
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
                # Add resource type nodes, checking for empty categories
                await self._add_resource_type_nodes(project_node, project.project_id)

            logger.info(f"Loaded {len(projects)} projects")

        except Exception as e:
            logger.error(f"Failed to load projects: {e}")

    async def _add_resource_type_nodes(self, project_node: TreeNode[ResourceTreeNode], project_id: str) -> None:
        """Add resource type category nodes to a project.

        Only adds categories that have resources. Eagerly checks each resource type.

        Args:
            project_node: Parent project node
            project_id: Project ID
        """
        # Check CloudSQL
        try:
            cloudsql_service = await get_cloudsql_service()
            cloudsql_instances = await cloudsql_service.list_instances(project_id)
            if cloudsql_instances:
                cloudsql_data = ResourceTreeNode(
                    resource_type=ResourceType.CLOUDSQL,
                    resource_id=f"{project_id}:cloudsql",
                    project_id=project_id,
                )
                project_node.add("☁️  Cloud SQL", data=cloudsql_data, allow_expand=True)
        except Exception as e:
            logger.debug(f"Failed to check CloudSQL instances for {project_id}: {e}")

        # Check Compute (Instance Groups)
        try:
            compute_service = await get_compute_service()
            instance_groups = await compute_service.list_instance_groups(project_id)
            if instance_groups:
                compute_data = ResourceTreeNode(
                    resource_type=ResourceType.COMPUTE,
                    resource_id=f"{project_id}:compute",
                    project_id=project_id,
                )
                project_node.add("💻 Instance Groups", data=compute_data, allow_expand=True)
        except Exception as e:
            logger.debug(f"Failed to check instance groups for {project_id}: {e}")

        # Check GKE
        try:
            gke_service = await get_gke_service()
            gke_clusters = await gke_service.list_clusters(project_id)
            if gke_clusters:
                gke_data = ResourceTreeNode(
                    resource_type=ResourceType.GKE,
                    resource_id=f"{project_id}:gke",
                    project_id=project_id,
                )
                project_node.add("⎈  GKE Clusters", data=gke_data, allow_expand=True)
        except Exception as e:
            logger.debug(f"Failed to check GKE clusters for {project_id}: {e}")

        # Check Secrets
        try:
            secrets_service = await get_secret_manager_service()
            secrets = await secrets_service.list_secrets(project_id)
            if secrets:
                secrets_data = ResourceTreeNode(
                    resource_type=ResourceType.SECRETS,
                    resource_id=f"{project_id}:secrets",
                    project_id=project_id,
                )
                project_node.add("🔐 Secrets", data=secrets_data, allow_expand=True)
        except Exception as e:
            logger.debug(f"Failed to check secrets for {project_id}: {e}")

        # Check IAM
        try:
            iam_service = await get_iam_service()
            service_accounts = await iam_service.list_service_accounts(project_id)
            if service_accounts:
                iam_data = ResourceTreeNode(
                    resource_type=ResourceType.IAM,
                    resource_id=f"{project_id}:iam",
                    project_id=project_id,
                )
                project_node.add("👤 Service Accounts", data=iam_data, allow_expand=True)
        except Exception as e:
            logger.debug(f"Failed to check service accounts for {project_id}: {e}")

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
            elif node.data.resource_type == ResourceType.GKE:
                await self._load_gke_clusters(node)
            elif node.data.resource_type == ResourceType.SECRETS:
                await self._load_secrets(node)
            elif node.data.resource_type == ResourceType.IAM:
                await self._load_service_accounts(node)

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

        for group in groups:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.COMPUTE,
                resource_id=group.group_name,
                resource_data=group,
                project_id=project_id,
            )
            type_icon = "M" if group.is_managed else "U"
            parent_node.add_leaf(
                f"[{type_icon}] {group.group_name} (size: {group.size})",
                data=node_data,
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

        for cluster in clusters:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.GKE,
                resource_id=cluster.cluster_name,
                resource_data=cluster,
                project_id=project_id,
            )
            status_icon = "✓" if cluster.is_running() else "✗"
            parent_node.add_leaf(
                f"{status_icon} {cluster.cluster_name} (nodes: {cluster.node_count})",
                data=node_data,
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

        for account in accounts:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.IAM,
                resource_id=account.email,
                resource_data=account,
                project_id=project_id,
            )
            status_icon = "✓" if account.is_enabled() else "✗"
            parent_node.add_leaf(
                f"{status_icon} {account.email}",
                data=node_data,
            )
