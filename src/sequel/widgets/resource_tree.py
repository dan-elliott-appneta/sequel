"""Resource tree widget for displaying GCP resources in a hierarchical view."""

import asyncio
import re
from typing import Any

from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from sequel.config import get_config
from sequel.services.clouddns import get_clouddns_service
from sequel.services.cloudsql import get_cloudsql_service
from sequel.services.compute import get_compute_service
from sequel.services.gke import get_gke_service
from sequel.services.iam import get_iam_service
from sequel.services.projects import get_project_service
from sequel.services.secrets import get_secret_manager_service
from sequel.utils.logging import get_logger

logger = get_logger(__name__)

# Maximum number of children to display per node expansion
# Additional items are shown as "... and N more"
MAX_CHILDREN_PER_NODE = 50


class ResourceType:
    """Constants for resource types."""

    PROJECT = "project"
    CLOUDDNS = "clouddns"
    CLOUDDNS_ZONE = "clouddns_zone"  # Expandable DNS zone
    CLOUDDNS_RECORD = "clouddns_record"  # Individual DNS record (leaf)
    CLOUDSQL = "cloudsql"
    COMPUTE = "compute"
    COMPUTE_INSTANCE_GROUP = "compute_instance_group"  # Expandable instance group
    COMPUTE_INSTANCE = "compute_instance"  # Individual VM instance (leaf)
    GKE = "gke"
    GKE_CLUSTER = "gke_cluster"  # Expandable cluster
    GKE_NODE = "gke_node"  # Individual node (leaf)
    SECRETS = "secrets"
    IAM = "iam"
    IAM_SERVICE_ACCOUNT = "iam_service_account"  # Expandable service account
    IAM_ROLE = "iam_role"  # Individual role binding (leaf)


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

    def _should_limit_children(self, count: int) -> bool:
        """Check if we should limit the number of children displayed.

        Args:
            count: Total number of children

        Returns:
            True if count exceeds MAX_CHILDREN_PER_NODE
        """
        return count > MAX_CHILDREN_PER_NODE

    def _add_more_indicator(
        self,
        parent_node: TreeNode[ResourceTreeNode],
        remaining_count: int,
    ) -> None:
        """Add '... and N more' indicator node.

        Args:
            parent_node: Parent tree node
            remaining_count: Number of remaining items not displayed
        """
        parent_node.add(
            f"💭 ... and {remaining_count} more",
            allow_expand=False,
        )

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

            # Automatically cleanup empty nodes in the background (non-blocking)
            # Store task reference to prevent garbage collection
            self._cleanup_task = asyncio.create_task(self.cleanup_empty_nodes())

        except Exception as e:
            logger.error(f"Failed to load projects: {e}")

    def _add_resource_type_nodes(self, project_node: TreeNode[ResourceTreeNode], project_id: str) -> None:
        """Add resource type category nodes to a project.

        Args:
            project_node: Parent project node
            project_id: Project ID
        """
        # Add CloudDNS
        clouddns_data = ResourceTreeNode(
            resource_type=ResourceType.CLOUDDNS,
            resource_id=f"{project_id}:clouddns",
            project_id=project_id,
        )
        project_node.add("🌐 Cloud DNS", data=clouddns_data, allow_expand=True)

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

    def _remove_empty_project_node(self, project_node: TreeNode[ResourceTreeNode]) -> None:
        """Remove a project node if it has no children.

        Args:
            project_node: Project node to check and potentially remove
        """
        if not project_node.children:
            logger.info(f"Removing empty project node: {project_node.label}")
            project_node.remove()

    async def cleanup_empty_nodes(self) -> None:
        """Automatically check and remove empty resource type and project nodes.

        This method iterates through all projects and their resource type nodes,
        loading each resource type to check if it has any resources. Empty resource
        type nodes are removed, and projects with no resource types are also removed.

        Uses parallel loading for performance - loads all resource types for each
        project simultaneously using asyncio.gather().
        """
        logger.info("Starting automatic cleanup of empty nodes with parallel loading")
        projects_to_check = list(self.root.children)

        for project_node in projects_to_check:
            if not project_node.data or project_node.data.resource_type != ResourceType.PROJECT:
                continue

            # Load all resource types in parallel for this project
            await self._load_all_resources_parallel(project_node)

        logger.info("Completed automatic cleanup of empty nodes")

    async def _load_all_resources_parallel(self, project_node: TreeNode[ResourceTreeNode]) -> None:
        """Load all resource types for a project in parallel.

        This method loads CloudDNS, CloudSQL, Compute, GKE, Secrets, and IAM
        resources simultaneously to significantly improve performance.

        Args:
            project_node: Project node to load resources for
        """
        # Get all resource type nodes for this project
        resource_type_nodes = list(project_node.children)

        # Create tasks for loading each resource type
        # Track which node corresponds to which task
        tasks = []
        task_nodes = []

        for resource_node in resource_type_nodes:
            if not resource_node.data or resource_node.data.loaded:
                continue

            resource_type = resource_node.data.resource_type

            # Create coroutine for each resource type
            task = None
            if resource_type == ResourceType.CLOUDDNS:
                task = self._load_dns_zones(resource_node)
            elif resource_type == ResourceType.CLOUDSQL:
                task = self._load_cloudsql_instances(resource_node)
            elif resource_type == ResourceType.COMPUTE:
                task = self._load_instance_groups(resource_node)
            elif resource_type == ResourceType.GKE:
                task = self._load_gke_clusters(resource_node)
            elif resource_type == ResourceType.SECRETS:
                task = self._load_secrets(resource_node)
            elif resource_type == ResourceType.IAM:
                task = self._load_service_accounts(resource_node)

            if task:
                tasks.append(task)
                task_nodes.append(resource_node)

        # Load all resource types in parallel
        # return_exceptions=True prevents one failure from stopping all loads
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and mark nodes as loaded
            for i, result in enumerate(results):
                node_data = task_nodes[i].data
                if isinstance(result, Exception):
                    resource_type = node_data.resource_type if node_data else "unknown"
                    logger.error(f"Error loading {resource_type} during parallel load: {result}")
                else:
                    # Mark as loaded if successful
                    if node_data:
                        node_data.loaded = True

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
            if node.data.resource_type == ResourceType.CLOUDDNS:
                await self._load_dns_zones(node)
            elif node.data.resource_type == ResourceType.CLOUDDNS_ZONE:
                await self._load_dns_records(node)
            elif node.data.resource_type == ResourceType.CLOUDSQL:
                await self._load_cloudsql_instances(node)
            elif node.data.resource_type == ResourceType.COMPUTE:
                await self._load_instance_groups(node)
            elif node.data.resource_type == ResourceType.COMPUTE_INSTANCE_GROUP:
                await self._load_instances_in_group(node)
            elif node.data.resource_type == ResourceType.GKE:
                await self._load_gke_clusters(node)
            elif node.data.resource_type == ResourceType.GKE_CLUSTER:
                await self._load_cluster_nodes(node)
            elif node.data.resource_type == ResourceType.SECRETS:
                await self._load_secrets(node)
            elif node.data.resource_type == ResourceType.IAM:
                await self._load_service_accounts(node)
            elif node.data.resource_type == ResourceType.IAM_SERVICE_ACCOUNT:
                await self._load_service_account_roles(node)

            node.data.loaded = True

        except Exception as e:
            logger.error(f"Failed to load resources: {e}")
            node.add_leaf(f"Error: {e}")

    async def _load_dns_zones(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load Cloud DNS managed zones for a project."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading DNS zones for {project_id}")

        service = await get_clouddns_service()
        zones = await service.list_zones(project_id)

        parent_node.remove_children()

        if not zones:
            # Remove the parent node if there are no zones
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        for zone in zones:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.CLOUDDNS_ZONE,
                resource_id=zone.zone_name,
                resource_data=zone,
                project_id=project_id,
            )
            visibility_icon = "🌍" if zone.visibility == "public" else "🔒"
            # Make zones expandable to show DNS records
            parent_node.add(
                f"{visibility_icon} {zone.dns_name}",
                data=node_data,
                allow_expand=True,
            )

    async def _load_dns_records(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load DNS records for a managed zone."""
        if parent_node.data is None or parent_node.data.resource_data is None:
            return

        zone = parent_node.data.resource_data
        parent_node.remove_children()

        if not parent_node.data.project_id:
            parent_node.add(
                "⚠️  Missing project ID",
                allow_expand=False,
            )
            return

        # Fetch DNS records from Cloud DNS API
        try:
            dns_service = await get_clouddns_service()
            logger.info(
                f"Fetching DNS records for zone {zone.zone_name} "
                f"in project {parent_node.data.project_id}"
            )
            records = await dns_service.list_records(
                project_id=parent_node.data.project_id,
                zone_name=zone.zone_name,
            )

            logger.info(f"Retrieved {len(records)} DNS records for {zone.zone_name}")

            if not records:
                # Show message that no records exist instead of removing the node
                parent_node.add(
                    "📝 No DNS records",
                    allow_expand=False,
                )
                return

            # Add DNS record nodes (with limit)
            total_records = len(records)
            records_to_show = records[:MAX_CHILDREN_PER_NODE] if self._should_limit_children(total_records) else records

            for record in records_to_show:
                node_data = ResourceTreeNode(
                    resource_type=ResourceType.CLOUDDNS_RECORD,
                    resource_id=f"{record.record_name}:{record.record_type}",
                    resource_data=record,
                    project_id=parent_node.data.project_id,
                )
                # Show record name, type, and value
                display_value = record.get_display_value()
                parent_node.add(
                    f"📝 {record.record_type}: {record.record_name} → {display_value}",
                    data=node_data,
                    allow_expand=False,
                )

            # Add "... and N more" indicator if we hit the limit
            if self._should_limit_children(total_records):
                remaining = total_records - MAX_CHILDREN_PER_NODE
                self._add_more_indicator(parent_node, remaining)

        except Exception as e:
            logger.error(f"Failed to load DNS records: {e}")
            # Show error message instead of removing the node
            parent_node.add(
                f"⚠️  Error loading records: {str(e)[:50]}",
                allow_expand=False,
            )

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
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
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
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        for group in groups:
            # Extract zone or region from the group
            zone = None
            region = None

            if hasattr(group, 'zone') and group.zone:
                # Zonal group: zone is like "https://www.googleapis.com/compute/v1/projects/PROJECT/zones/ZONE"
                zone_parts = group.zone.split('/')
                if len(zone_parts) > 0:
                    zone = zone_parts[-1]
            elif hasattr(group, 'region') and group.region:
                # Regional group: region is like "https://www.googleapis.com/compute/v1/projects/PROJECT/regions/REGION"
                region_parts = group.region.split('/')
                if len(region_parts) > 0:
                    region = region_parts[-1]

            node_data = ResourceTreeNode(
                resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
                resource_id=group.group_name,
                resource_data=group,
                project_id=project_id,
                zone=zone,
                location=region,  # Store region in location field for regional groups
            )
            type_icon = "M" if group.is_managed else "U"
            zone_or_region = zone if zone else region
            # Make instance groups expandable to show instances
            parent_node.add(
                f"[{type_icon}] {group.group_name} ({zone_or_region}, size: {group.size})",
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
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        for cluster in clusters:
            # Extract location from cluster
            location = cluster.location if hasattr(cluster, 'location') else None

            node_data = ResourceTreeNode(
                resource_type=ResourceType.GKE_CLUSTER,
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
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
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
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        for account in accounts:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
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
        if parent_node.data is None or parent_node.data.resource_data is None:
            return

        service_account = parent_node.data.resource_data
        parent_node.remove_children()

        if not parent_node.data.project_id:
            parent_node.add(
                "⚠️  Missing project ID",
                allow_expand=False,
            )
            return

        # Fetch real IAM role bindings from IAM API
        try:
            iam_service = await get_iam_service()
            logger.info(
                f"Fetching IAM roles for service account {service_account.email} "
                f"in project {parent_node.data.project_id}"
            )
            role_bindings = await iam_service.get_service_account_roles(
                project_id=parent_node.data.project_id,
                service_account_email=service_account.email,
            )

            logger.info(f"Retrieved {len(role_bindings)} role bindings for {service_account.email}")

            if not role_bindings:
                # Show message that no roles are assigned instead of removing the node
                parent_node.add(
                    "📋 No roles assigned",
                    allow_expand=False,
                )
                return

            # Add role binding nodes with real data (with limit)
            total_roles = len(role_bindings)
            roles_to_show = role_bindings[:MAX_CHILDREN_PER_NODE] if self._should_limit_children(total_roles) else role_bindings

            for role_binding in roles_to_show:
                node_data = ResourceTreeNode(
                    resource_type=ResourceType.IAM_ROLE,
                    resource_id=role_binding.role,
                    resource_data=role_binding,
                    project_id=parent_node.data.project_id,
                )
                # Extract role name (e.g., "roles/editor" -> "Editor")
                role_name = role_binding.role.split("/")[-1]
                parent_node.add(
                    f"📋 {role_name}",
                    data=node_data,
                    allow_expand=False,
                )

            # Add "... and N more" indicator if we hit the limit
            if self._should_limit_children(total_roles):
                remaining = total_roles - MAX_CHILDREN_PER_NODE
                self._add_more_indicator(parent_node, remaining)

        except Exception as e:
            logger.error(f"Failed to load service account roles: {e}")
            # Show error message instead of removing the node
            parent_node.add(
                f"⚠️  Error loading roles: {str(e)[:50]}",
                allow_expand=False,
            )

    async def _load_cluster_nodes(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load nodes for a GKE cluster."""
        if parent_node.data is None or parent_node.data.resource_data is None:
            return

        cluster = parent_node.data.resource_data
        parent_node.remove_children()

        if not parent_node.data.project_id or not parent_node.data.location:
            parent_node.add(
                "⚠️  Missing project ID or location",
                allow_expand=False,
            )
            return

        # Fetch real node data from GKE API
        try:
            gke_service = await get_gke_service()
            nodes = await gke_service.list_nodes(
                project_id=parent_node.data.project_id,
                location=parent_node.data.location,
                cluster_name=cluster.cluster_name,
            )

            if not nodes:
                # Show message that no nodes are found instead of removing the node
                parent_node.add(
                    "🖥️  No nodes found",
                    allow_expand=False,
                )
                return

            # Add node nodes with real data (with limit)
            total_nodes = len(nodes)
            nodes_to_show = nodes[:MAX_CHILDREN_PER_NODE] if self._should_limit_children(total_nodes) else nodes

            for node in nodes_to_show:
                node_data = ResourceTreeNode(
                    resource_type=ResourceType.GKE_NODE,
                    resource_id=node.node_name,
                    resource_data=node,
                    project_id=parent_node.data.project_id,
                    location=parent_node.data.location,
                )
                parent_node.add(
                    f"🖥️  {node.node_name}",
                    data=node_data,
                    allow_expand=False,
                )

            # Add "... and N more" indicator if we hit the limit
            if self._should_limit_children(total_nodes):
                remaining = total_nodes - MAX_CHILDREN_PER_NODE
                self._add_more_indicator(parent_node, remaining)

        except Exception as e:
            logger.error(f"Failed to load cluster nodes: {e}")
            # Show error message instead of removing the node
            parent_node.add(
                f"⚠️  Error loading nodes: {str(e)[:50]}",
                allow_expand=False,
            )

    async def _load_instances_in_group(self, parent_node: TreeNode[ResourceTreeNode]) -> None:
        """Load instances in an instance group (zonal or regional)."""
        if parent_node.data is None or parent_node.data.resource_data is None:
            return

        group = parent_node.data.resource_data
        parent_node.remove_children()

        if not parent_node.data.project_id:
            parent_node.add(
                "⚠️  Missing project ID",
                allow_expand=False,
            )
            return

        # Check if this is a zonal or regional group
        zone = parent_node.data.zone
        region = parent_node.data.location  # For regional groups, region is stored in location

        logger.info(f"Loading instances for group: {group.group_name}, zone={zone}, region={region}")

        if not zone and not region:
            parent_node.add(
                "⚠️  Missing zone or region",
                allow_expand=False,
            )
            return

        # Fetch real instance data from Compute API
        try:
            compute_service = await get_compute_service()

            # Use appropriate method based on whether it's zonal or regional
            is_managed = group.is_managed if hasattr(group, 'is_managed') else True

            if zone:
                # Zonal instance group
                logger.info(f"Loading zonal instances: project={parent_node.data.project_id}, zone={zone}, group={group.group_name}, managed={is_managed}")
                instances = await compute_service.list_instances_in_group(
                    project_id=parent_node.data.project_id,
                    zone=zone,
                    instance_group_name=group.group_name,
                    is_managed=is_managed,
                )
            else:
                # Regional instance group
                logger.info(f"Loading regional instances: project={parent_node.data.project_id}, region={region}, group={group.group_name}, managed={is_managed}")
                instances = await compute_service.list_instances_in_regional_group(
                    project_id=parent_node.data.project_id,
                    region=region,  # type: ignore[arg-type]
                    instance_group_name=group.group_name,
                    is_managed=is_managed,
                )

            logger.info(f"Loaded {len(instances)} instances for {group.group_name}")

            if not instances:
                # Show message that no instances are found instead of removing the node
                logger.warning(f"No instances found for {group.group_name}, adding placeholder")
                parent_node.add(
                    "💻 No instances found",
                    allow_expand=False,
                )
                return

            # Add instance nodes with real data (with limit)
            total_instances = len(instances)
            instances_to_show = instances[:MAX_CHILDREN_PER_NODE] if self._should_limit_children(total_instances) else instances

            logger.info(f"Adding {len(instances_to_show)} of {total_instances} instances to tree for {group.group_name}")

            for instance in instances_to_show:
                node_data = ResourceTreeNode(
                    resource_type=ResourceType.COMPUTE_INSTANCE,
                    resource_id=instance.instance_name,
                    resource_data=instance,
                    project_id=parent_node.data.project_id,
                    zone=instance.zone,
                )
                status_icon = "✓" if instance.is_running() else "✗"
                parent_node.add(
                    f"{status_icon} {instance.instance_name}",
                    data=node_data,
                    allow_expand=False,
                )

            # Add "... and N more" indicator if we hit the limit
            if self._should_limit_children(total_instances):
                remaining = total_instances - MAX_CHILDREN_PER_NODE
                self._add_more_indicator(parent_node, remaining)

        except Exception as e:
            logger.error(f"Failed to load instances in group: {e}", exc_info=True)
            # Show error message instead of removing the node
            parent_node.add(
                f"⚠️  Error loading instances: {str(e)[:50]}",
                allow_expand=False,
            )
