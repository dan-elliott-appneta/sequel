"""Resource tree widget for displaying GCP resources in a hierarchical view."""

import asyncio
from typing import Any

from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from sequel.models.project import Project
from sequel.services.compute import get_compute_service
from sequel.services.gke import get_gke_service
from sequel.services.iam import get_iam_service
from sequel.state.resource_state import get_resource_state
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
        self._state = get_resource_state()  # Reference to centralized state
        self._filter_text: str = ""  # Current filter text

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

    async def _load_dns_zones_slowly(
        self, projects: list[Project], force_refresh: bool = False
    ) -> None:
        """Load ONLY DNS zones for projects one at a time to avoid crashes.

        This is a very conservative approach that loads DNS zones slowly
        in the background to populate the local datasource for filtering.

        Args:
            projects: List of projects to load DNS zones for
            force_refresh: If True, bypass cache and reload from API
        """
        logger.info(f"Background loading DNS zones for {len(projects)} projects (one at a time)")

        for i, project in enumerate(projects):
            try:
                # Load DNS zones for this project (filtered by dns_zone_filter)
                zones = await self._state.load_dns_zones(project.project_id, force_refresh)
                logger.debug(f"Loaded {len(zones)} DNS zones for {project.project_id} ({i+1}/{len(projects)})")

                # Wait between projects to avoid overwhelming the system
                await asyncio.sleep(1.0)  # 1 second delay between projects

            except Exception as e:
                logger.warning(f"Failed to load DNS zones for {project.project_id}: {e}")

        logger.info(f"Finished background loading DNS zones for {len(projects)} projects")

    async def _load_all_resources_for_projects(
        self, projects: list[Project], force_refresh: bool = False
    ) -> None:
        """Load all resources for all projects in parallel into state.

        This ensures all resources are available in the local datasource for filtering.

        Args:
            projects: List of projects to load resources for
            force_refresh: If True, bypass cache and reload from API
        """
        logger.info(f"Proactively loading resources for {len(projects)} projects")

        # Limit concurrent operations to prevent overwhelming the API and causing segfaults
        # Process projects in small batches with throttling
        batch_size = 2  # Process only 2 projects at a time to be safe
        max_dns_records_per_batch = 10  # Limit DNS record loads per batch
        all_results = []

        for i in range(0, len(projects), batch_size):
            batch = projects[i:i + batch_size]
            logger.info(f"Loading resources for projects {i+1}-{min(i+batch_size, len(projects))}")

            # Add small delay between batches to avoid rate limits
            if i > 0:
                await asyncio.sleep(0.5)

            # Create tasks for this batch
            from typing import Any
            tasks: list[Any] = []
            for project in batch:
                project_id = project.project_id
                # Load DNS zones (critical for filtering) - these are filtered by dns_zone_filter
                tasks.append(self._state.load_dns_zones(project_id, force_refresh))
                # Load other resources
                tasks.append(self._state.load_cloudsql_instances(project_id, force_refresh))
                tasks.append(self._state.load_compute_groups(project_id, force_refresh))
                tasks.append(self._state.load_gke_clusters(project_id, force_refresh))
                tasks.append(self._state.load_secrets(project_id, force_refresh))
                tasks.append(self._state.load_iam_accounts(project_id, force_refresh))

            # Load this batch in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(results)

            # Now load DNS records for the filtered zones in this batch
            # Limit the number of DNS record loads to prevent segfaults
            record_tasks: list[Any] = []
            for j, result in enumerate(results):
                # DNS zones are every 6th result (indices 0, 6, 12, ...)
                if j % 6 == 0 and isinstance(result, list) and result:
                    project_idx = j // 6
                    if project_idx < len(batch):
                        project_id = batch[project_idx].project_id
                        # Load DNS records for each filtered zone (up to limit)
                        for zone in result:
                            if len(record_tasks) < max_dns_records_per_batch:
                                record_tasks.append(
                                    self._state.load_dns_records(project_id, zone.zone_name, force_refresh)
                                )
                            else:
                                logger.debug(f"Skipping DNS records for {zone.zone_name} (batch limit reached)")

            # Load DNS records for this batch
            if record_tasks:
                logger.info(f"Loading DNS records for {len(record_tasks)} filtered zones in batch")
                record_results = await asyncio.gather(*record_tasks, return_exceptions=True)
                for result in record_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to load DNS records: {result}")

                # Small delay after loading DNS records
                await asyncio.sleep(0.3)

        # Use combined results
        results = all_results

        # Log any errors and count loaded zones
        error_count = 0
        total_zones = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                logger.warning(f"Failed to load resource: {result}")
            # Track DNS zone results (every 6th task starting from index 0 is DNS zones)
            elif i % 6 == 0 and isinstance(result, list):
                total_zones += len(result)

        logger.info(
            f"Loaded resources for {len(projects)} projects "
            f"({len(results)} tasks, {error_count} errors, {total_zones} filtered DNS zones)"
        )

    async def load_projects(self, force_refresh: bool = False) -> None:
        """Load all projects as root-level nodes.

        Args:
            force_refresh: If True, bypass state cache and reload from API
        """
        try:
            logger.info(f"Loading projects into tree (force_refresh={force_refresh})")

            # Load projects into state (uses cache if not force_refresh)
            # Note: Projects are already filtered by project_filter_regex in the state layer
            projects = await self._state.load_projects(force_refresh)

            # Clear existing nodes
            self.root.remove_children()

            # Add project nodes FIRST so UI is responsive
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

            # DISABLED: Background DNS loading causes segfaults due to concurrent API calls
            # DNS zones and records will be loaded on-demand when:
            # 1. User expands DNS zone nodes
            # 2. User applies a filter (filter logic loads DNS data as needed)
            # self._background_task = asyncio.create_task(self._load_dns_zones_slowly(projects, force_refresh))

            # DISABLED: Automatic cleanup still causes segfaults even with batched loading
            # Even with batch size of 2 (12 concurrent API calls), segfaults still occur.
            # Cleanup happens automatically during filtering operations instead.
            # Manual cleanup can be triggered if needed, but automatic background cleanup is too risky.
            # self._cleanup_task = asyncio.create_task(self.cleanup_empty_nodes())

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

        Uses batched loading with throttling to prevent API overload and segfaults.
        Processes projects in small batches with delays between batches.
        """
        logger.info("Starting automatic cleanup of empty nodes with batched loading")

        # Show starting notification
        if self.app:
            self.app.notify(
                "Cleaning up empty projects...",
                severity="information",
                timeout=3,
            )

        # Track initial counts
        initial_project_count = len(self.root.children)

        projects_to_check = list(self.root.children)

        # Filter to only project nodes
        project_nodes = [
            node for node in projects_to_check
            if node.data and node.data.resource_type == ResourceType.PROJECT
        ]

        # Process projects in small batches to prevent too many concurrent API calls
        batch_size = 2  # Process only 2 projects at a time to be safe
        for i in range(0, len(project_nodes), batch_size):
            batch = project_nodes[i:i + batch_size]
            logger.info(f"Cleanup batch {i // batch_size + 1}: processing {len(batch)} projects")

            # Add small delay between batches to avoid rate limits
            if i > 0:
                await asyncio.sleep(0.5)

            # Load resources for this batch of projects in parallel
            tasks = []
            for project_node in batch:
                tasks.append(self._load_all_resources_parallel(project_node))

            # Wait for batch to complete
            await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate how many projects were removed
        final_project_count = len(self.root.children)
        removed_count = initial_project_count - final_project_count

        logger.info(f"Completed automatic cleanup of empty nodes: removed {removed_count} empty projects")

        # Show completion notification
        if self.app:
            if removed_count > 0:
                project_word = "project" if removed_count == 1 else "projects"
                self.app.notify(
                    f"Cleanup complete: removed {removed_count} empty {project_word}",
                    severity="information",
                    timeout=5,
                )
            else:
                self.app.notify(
                    "Cleanup complete: no empty projects found",
                    severity="information",
                    timeout=3,
                )

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
        """Load Cloud DNS managed zones for a project from state."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading DNS zones for {project_id} from state")

        # Load into state (uses cache from service layer)
        zones = await self._state.load_dns_zones(project_id)

        parent_node.remove_children()

        if not zones:
            # Remove the parent node if there are no zones
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        # Apply UI filter if active
        if self._filter_text:
            logger.info(f"Applying UI filter '{self._filter_text}' to {len(zones)} DNS zones")
            filtered_zones = []
            for zone in zones:
                # Check if zone name matches UI filter
                if self._matches_filter(zone.dns_name):
                    filtered_zones.append(zone)
                else:
                    # Check if any DNS records match the filter
                    try:
                        records = await self._state.load_dns_records(project_id, zone.zone_name)
                        for record in records:
                            if self._matches_filter(record.record_name) or self._matches_filter(record.record_type):
                                filtered_zones.append(zone)
                                break
                    except Exception as e:
                        logger.debug(f"Failed to check DNS records for filtering: {e}")

            zones = filtered_zones
            logger.info(f"Filtered to {len(zones)} DNS zones matching '{self._filter_text}'")

        # Update parent label with count
        zone_word = "zone" if len(zones) == 1 else "zones"
        parent_node.set_label(f"🌐 Cloud DNS ({len(zones)} {zone_word})")

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
        """Load DNS records for a managed zone from state."""
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

        # Load DNS records from state (uses cache from service layer)
        try:
            logger.info(
                f"Loading DNS records for zone {zone.zone_name} "
                f"in project {parent_node.data.project_id} from state"
            )
            records = await self._state.load_dns_records(
                project_id=parent_node.data.project_id,
                zone_name=zone.zone_name,
            )

            logger.info(f"Loaded {len(records)} DNS records for {zone.zone_name} from state")

            # Apply UI filter if active
            if self._filter_text:
                logger.info(f"Applying UI filter '{self._filter_text}' to {len(records)} DNS records")
                records = [
                    r for r in records
                    if self._matches_filter(r.record_name) or self._matches_filter(r.record_type)
                ]
                logger.info(f"Filtered to {len(records)} DNS records matching '{self._filter_text}'")

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
        """Load Cloud SQL instances for a project from state."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading Cloud SQL instances for {project_id} from state")

        # Load into state (uses cache from service layer)
        instances = await self._state.load_cloudsql_instances(project_id)

        parent_node.remove_children()

        # Apply UI filter if active
        if self._filter_text:
            logger.info(f"Applying UI filter '{self._filter_text}' to {len(instances)} CloudSQL instances")
            instances = [
                i for i in instances
                if self._matches_filter(i.instance_name)
            ]
            logger.info(f"Filtered to {len(instances)} CloudSQL instances matching '{self._filter_text}'")

        if not instances:
            # Remove the parent node if there are no instances
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        # Update parent label with count
        instance_word = "instance" if len(instances) == 1 else "instances"
        parent_node.set_label(f"☁️  Cloud SQL ({len(instances)} {instance_word})")

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
        """Load Compute Engine instance groups for a project from state."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading instance groups for {project_id} from state")

        # Load into state (uses cache from service layer)
        groups = await self._state.load_compute_groups(project_id)

        parent_node.remove_children()

        # Apply UI filter if active
        if self._filter_text:
            logger.info(f"Applying UI filter '{self._filter_text}' to {len(groups)} compute groups")
            groups = [
                g for g in groups
                if self._matches_filter(g.group_name)
            ]
            logger.info(f"Filtered to {len(groups)} compute groups matching '{self._filter_text}'")

        if not groups:
            # Remove the parent node if there are no instance groups
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        # Update parent label with count
        group_word = "group" if len(groups) == 1 else "groups"
        parent_node.set_label(f"💻 Instance Groups ({len(groups)} {group_word})")

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
        """Load GKE clusters for a project from state."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading GKE clusters for {project_id} from state")

        # Load into state (uses cache from service layer)
        clusters = await self._state.load_gke_clusters(project_id)

        parent_node.remove_children()

        # Apply UI filter if active
        if self._filter_text:
            logger.info(f"Applying UI filter '{self._filter_text}' to {len(clusters)} GKE clusters")
            clusters = [
                c for c in clusters
                if self._matches_filter(c.cluster_name)
            ]
            logger.info(f"Filtered to {len(clusters)} GKE clusters matching '{self._filter_text}'")

        if not clusters:
            # Remove the parent node if there are no clusters
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        # Update parent label with count
        cluster_word = "cluster" if len(clusters) == 1 else "clusters"
        parent_node.set_label(f"⎈  GKE Clusters ({len(clusters)} {cluster_word})")

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
        """Load secrets for a project from state."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading secrets for {project_id} from state")

        # Load into state (uses cache from service layer)
        secrets = await self._state.load_secrets(project_id)

        parent_node.remove_children()

        # Apply UI filter if active
        if self._filter_text:
            logger.info(f"Applying UI filter '{self._filter_text}' to {len(secrets)} secrets")
            secrets = [
                s for s in secrets
                if self._matches_filter(s.secret_name)
            ]
            logger.info(f"Filtered to {len(secrets)} secrets matching '{self._filter_text}'")

        if not secrets:
            # Remove the parent node if there are no secrets
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        # Update parent label with count
        secret_word = "secret" if len(secrets) == 1 else "secrets"
        parent_node.set_label(f"🔐 Secrets ({len(secrets)} {secret_word})")

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
        """Load service accounts for a project from state."""
        if parent_node.data is None or parent_node.data.project_id is None:
            return

        project_id = parent_node.data.project_id
        logger.info(f"Loading service accounts for {project_id} from state")

        # Load into state (uses cache from service layer)
        accounts = await self._state.load_iam_accounts(project_id)

        parent_node.remove_children()

        # Apply UI filter if active
        if self._filter_text:
            logger.info(f"Applying UI filter '{self._filter_text}' to {len(accounts)} IAM accounts")
            accounts = [
                a for a in accounts
                if self._matches_filter(a.email) or (a.display_name and self._matches_filter(a.display_name))
            ]
            logger.info(f"Filtered to {len(accounts)} IAM accounts matching '{self._filter_text}'")

        if not accounts:
            # Remove the parent node if there are no service accounts
            project_node = parent_node.parent
            parent_node.remove()
            # Check if project is now empty and remove it
            if project_node and project_node.data and project_node.data.resource_type == ResourceType.PROJECT:
                self._remove_empty_project_node(project_node)
            return

        # Update parent label with count
        account_word = "account" if len(accounts) == 1 else "accounts"
        parent_node.set_label(f"👤 Service Accounts ({len(accounts)} {account_word})")

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

    async def apply_filter(self, filter_text: str) -> None:
        """Apply filter by querying state and rebuilding tree.

        Args:
            filter_text: Text to filter by (empty string clears filter)
        """
        self._filter_text = filter_text.strip().lower()
        logger.info(f"Applying filter: '{filter_text}'")

        if not self._filter_text:
            # No filter - reload projects normally
            await self.load_projects()
            return

        # Show notification
        if self.app:
            self.app.notify(f"Filtering for '{filter_text}'...", severity="information", timeout=3)

        # Get all projects from state
        # Note: Projects are already filtered by project_filter_regex in the state layer
        projects = self._state.get_projects()

        # Rebuild tree with only matching resources
        self.root.remove_children()

        for project in projects:
            # Check if project name matches
            project_matches = (
                self._matches_filter(project.display_name)
                or self._matches_filter(project.project_id)
            )

            # Get all resources from state for this project
            matching_resources: dict[str, list[Any]] = {}

            # Check DNS Zones and Records (if loaded)
            if self._state.is_loaded(project.project_id, "dns_zones"):
                zones = self._state.get_dns_zones(project.project_id)
                matching_zones = []

                for zone in zones:
                    # Check if zone name matches
                    if self._matches_filter(zone.dns_name):
                        matching_zones.append(zone)
                    else:
                        # Load DNS records for this zone if not already loaded
                        try:
                            records = await self._state.load_dns_records(
                                project.project_id, zone.zone_name
                            )
                            # Check if any records in this zone match
                            for record in records:
                                if self._matches_filter(record.record_name) or self._matches_filter(record.record_type):
                                    matching_zones.append(zone)
                                    break  # Found a match, include this zone
                        except Exception as e:
                            logger.warning(f"Failed to load DNS records for {zone.zone_name}: {e}")

                if matching_zones:
                    matching_resources["dns_zones"] = matching_zones

            # Check CloudSQL (if loaded)
            if self._state.is_loaded(project.project_id, "cloudsql"):
                instances = self._state.get_cloudsql_instances(project.project_id)
                matching_sql = [
                    i for i in instances if self._matches_filter(i.instance_name)
                ]
                if matching_sql:
                    matching_resources["cloudsql"] = matching_sql

            # Check Compute Groups (if loaded)
            if self._state.is_loaded(project.project_id, "compute_groups"):
                groups = self._state.get_compute_groups(project.project_id)
                matching_groups = [g for g in groups if self._matches_filter(g.group_name)]
                if matching_groups:
                    matching_resources["compute_groups"] = matching_groups

            # Check GKE Clusters (if loaded)
            if self._state.is_loaded(project.project_id, "gke_clusters"):
                clusters = self._state.get_gke_clusters(project.project_id)
                matching_clusters = [
                    c for c in clusters if self._matches_filter(c.cluster_name)
                ]
                if matching_clusters:
                    matching_resources["gke_clusters"] = matching_clusters

            # Check Secrets (if loaded)
            if self._state.is_loaded(project.project_id, "secrets"):
                secrets = self._state.get_secrets(project.project_id)
                matching_secrets = [s for s in secrets if self._matches_filter(s.secret_name)]
                if matching_secrets:
                    matching_resources["secrets"] = matching_secrets

            # Check IAM Accounts (if loaded)
            if self._state.is_loaded(project.project_id, "iam_accounts"):
                accounts = self._state.get_iam_accounts(project.project_id)
                matching_accounts = [
                    a
                    for a in accounts
                    if self._matches_filter(a.email)
                    or (a.display_name and self._matches_filter(a.display_name))
                ]
                if matching_accounts:
                    matching_resources["iam_accounts"] = matching_accounts

            # Only add project if it matches or has matching resources
            if project_matches or matching_resources:
                project_data = ResourceTreeNode(
                    resource_type=ResourceType.PROJECT,
                    resource_id=project.project_id,
                    resource_data=project,
                )
                project_node = self.root.add(
                    f"📁 {project.display_name or project.project_id}",
                    data=project_data,
                    allow_expand=True,
                )

                # Add matching DNS Zones
                if "dns_zones" in matching_resources:
                    zones = matching_resources["dns_zones"]
                    dns_data = ResourceTreeNode(
                        resource_type=ResourceType.CLOUDDNS,
                        resource_id=f"{project.project_id}:clouddns",
                        project_id=project.project_id,
                    )
                    zone_word = "zone" if len(zones) == 1 else "zones"
                    dns_node = project_node.add(
                        f"🌐 Cloud DNS ({len(zones)} {zone_word})",
                        data=dns_data,
                        allow_expand=True,
                    )
                    for zone in zones:
                        zone_data = ResourceTreeNode(
                            resource_type=ResourceType.CLOUDDNS_ZONE,
                            resource_id=zone.zone_name,
                            resource_data=zone,
                            project_id=project.project_id,
                        )
                        dns_node.add(
                            f"🔵 {zone.dns_name}",
                            data=zone_data,
                            allow_expand=True,
                        )

                # Add matching CloudSQL instances
                if "cloudsql" in matching_resources:
                    instances = matching_resources["cloudsql"]
                    sql_data = ResourceTreeNode(
                        resource_type=ResourceType.CLOUDSQL,
                        resource_id=f"{project.project_id}:cloudsql",
                        project_id=project.project_id,
                    )
                    instance_word = "instance" if len(instances) == 1 else "instances"
                    sql_node = project_node.add(
                        f"🗄️  Cloud SQL ({len(instances)} {instance_word})",
                        data=sql_data,
                        allow_expand=True,
                    )
                    for instance in instances:
                        inst_data = ResourceTreeNode(
                            resource_type=ResourceType.CLOUDSQL,
                            resource_id=instance.instance_name,
                            resource_data=instance,
                            project_id=project.project_id,
                        )
                        status_icon = "✓" if instance.is_running() else "✗"
                        sql_node.add_leaf(
                            f"{status_icon} {instance.instance_name} ({instance.database_version})",
                            data=inst_data,
                        )

                # Add matching Compute Groups
                if "compute_groups" in matching_resources:
                    groups = matching_resources["compute_groups"]
                    compute_data = ResourceTreeNode(
                        resource_type=ResourceType.COMPUTE,
                        resource_id=f"{project.project_id}:compute",
                        project_id=project.project_id,
                    )
                    group_word = "group" if len(groups) == 1 else "groups"
                    compute_node = project_node.add(
                        f"💻 Instance Groups ({len(groups)} {group_word})",
                        data=compute_data,
                        allow_expand=True,
                    )
                    for group in groups:
                        group_zone: str | None = None
                        region = None
                        if hasattr(group, 'zone') and group.zone:
                            zone_parts = group.zone.split('/')
                            if len(zone_parts) > 0:
                                group_zone = zone_parts[-1]
                        elif hasattr(group, 'region') and group.region:
                            region_parts = group.region.split('/')
                            if len(region_parts) > 0:
                                region = region_parts[-1]

                        group_data = ResourceTreeNode(
                            resource_type=ResourceType.COMPUTE_INSTANCE_GROUP,
                            resource_id=group.group_name,
                            resource_data=group,
                            project_id=project.project_id,
                            zone=group_zone,
                            location=region,
                        )
                        type_icon = "M" if group.is_managed else "U"
                        zone_or_region = group_zone if group_zone else region
                        compute_node.add(
                            f"[{type_icon}] {group.group_name} ({zone_or_region}, size: {group.size})",
                            data=group_data,
                            allow_expand=True,
                        )

                # Add matching GKE Clusters
                if "gke_clusters" in matching_resources:
                    clusters = matching_resources["gke_clusters"]
                    gke_data = ResourceTreeNode(
                        resource_type=ResourceType.GKE,
                        resource_id=f"{project.project_id}:gke",
                        project_id=project.project_id,
                    )
                    cluster_word = "cluster" if len(clusters) == 1 else "clusters"
                    gke_node = project_node.add(
                        f"⎈  GKE Clusters ({len(clusters)} {cluster_word})",
                        data=gke_data,
                        allow_expand=True,
                    )
                    for cluster in clusters:
                        location = cluster.location if hasattr(cluster, 'location') else None
                        cluster_data = ResourceTreeNode(
                            resource_type=ResourceType.GKE_CLUSTER,
                            resource_id=cluster.cluster_name,
                            resource_data=cluster,
                            project_id=project.project_id,
                            location=location,
                        )
                        status_icon = "✓" if cluster.is_running() else "✗"
                        gke_node.add(
                            f"{status_icon} {cluster.cluster_name} (nodes: {cluster.node_count})",
                            data=cluster_data,
                            allow_expand=True,
                        )

                # Add matching Secrets
                if "secrets" in matching_resources:
                    secrets = matching_resources["secrets"]
                    secrets_data = ResourceTreeNode(
                        resource_type=ResourceType.SECRETS,
                        resource_id=f"{project.project_id}:secrets",
                        project_id=project.project_id,
                    )
                    secret_word = "secret" if len(secrets) == 1 else "secrets"
                    secrets_node = project_node.add(
                        f"🔐 Secrets ({len(secrets)} {secret_word})",
                        data=secrets_data,
                        allow_expand=True,
                    )
                    for secret in secrets:
                        secret_data = ResourceTreeNode(
                            resource_type=ResourceType.SECRETS,
                            resource_id=secret.secret_name,
                            resource_data=secret,
                            project_id=project.project_id,
                        )
                        secrets_node.add_leaf(
                            f"🔑 {secret.secret_name}",
                            data=secret_data,
                        )

                # Add matching IAM Accounts
                if "iam_accounts" in matching_resources:
                    accounts = matching_resources["iam_accounts"]
                    iam_data = ResourceTreeNode(
                        resource_type=ResourceType.IAM,
                        resource_id=f"{project.project_id}:iam",
                        project_id=project.project_id,
                    )
                    account_word = "account" if len(accounts) == 1 else "accounts"
                    iam_node = project_node.add(
                        f"👤 Service Accounts ({len(accounts)} {account_word})",
                        data=iam_data,
                        allow_expand=True,
                    )
                    for account in accounts:
                        account_data = ResourceTreeNode(
                            resource_type=ResourceType.IAM_SERVICE_ACCOUNT,
                            resource_id=account.email,
                            resource_data=account,
                            project_id=project.project_id,
                        )
                        status_icon = "✓" if account.is_enabled() else "✗"
                        iam_node.add(
                            f"{status_icon} {account.email}",
                            data=account_data,
                            allow_expand=True,
                        )

        logger.info(f"Filter applied: showing {len(self.root.children)} matching projects")

        # Show completion notification
        if self.app:
            project_count = len(self.root.children)
            project_word = "project" if project_count == 1 else "projects"
            self.app.notify(
                f"Filter complete: {project_count} {project_word} match '{filter_text}'",
                severity="information",
                timeout=5,
            )

    def _matches_filter(self, text: str) -> bool:
        """Check if text matches the current filter.

        Args:
            text: Text to check

        Returns:
            True if text matches filter (case-insensitive)
        """
        if not self._filter_text or not text:
            return False
        return self._filter_text in text.lower()
