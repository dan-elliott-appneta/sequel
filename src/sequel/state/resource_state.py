"""Centralized state manager for in-memory GCP resource data."""

from collections.abc import Callable

from sequel.models.clouddns import DNSRecord, ManagedZone
from sequel.models.cloudsql import CloudSQLInstance
from sequel.models.compute import ComputeInstance, InstanceGroup
from sequel.models.gke import GKECluster, GKENode
from sequel.models.iam import IAMRoleBinding, ServiceAccount
from sequel.models.project import Project
from sequel.models.secrets import Secret
from sequel.services.clouddns import get_clouddns_service
from sequel.services.cloudsql import get_cloudsql_service
from sequel.services.compute import get_compute_service
from sequel.services.gke import get_gke_service
from sequel.services.iam import get_iam_service
from sequel.services.projects import get_project_service
from sequel.services.secrets import get_secret_manager_service
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceState:
    """Centralized state manager for GCP resources.

    This class maintains an in-memory cache of all loaded GCP resources.
    Resources are loaded from services on-demand and cached here. The tree
    widget renders from this state rather than calling APIs directly.

    The state tracks what has been loaded to avoid redundant API calls.
    When force_refresh is True, it bypasses the state cache and reloads from API.
    """

    def __init__(self) -> None:
        """Initialize the resource state manager."""
        # Resource storage by type
        self._projects: dict[str, Project] = {}
        self._dns_zones: dict[str, list[ManagedZone]] = {}
        self._dns_records: dict[tuple[str, str], list[DNSRecord]] = {}
        self._cloudsql: dict[str, list[CloudSQLInstance]] = {}
        self._compute_groups: dict[str, list[InstanceGroup]] = {}
        self._compute_instances: dict[tuple[str, str], list[ComputeInstance]] = {}
        self._gke_clusters: dict[str, list[GKECluster]] = {}
        self._gke_nodes: dict[tuple[str, str], list[GKENode]] = {}
        self._secrets: dict[str, list[Secret]] = {}
        self._iam_accounts: dict[str, list[ServiceAccount]] = {}
        self._iam_roles: dict[tuple[str, str], list[IAMRoleBinding]] = {}

        # Track what's been loaded - set of tuple keys
        self._loaded: set[tuple[str, ...]] = set()

    async def load_projects(self, force_refresh: bool = False) -> list[Project]:
        """Load projects into state from API.

        Args:
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of Project instances
        """
        key = ("projects",)

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            logger.info(f"Returning {len(self._projects)} projects from state")
            return list(self._projects.values())

        # Load from service (service has its own cache layer)
        service = await get_project_service()
        projects = await service.list_projects(use_cache=not force_refresh)

        # Store in state
        self._projects = {p.project_id: p for p in projects}
        self._loaded.add(key)

        logger.info(f"Loaded {len(projects)} projects into state")
        return projects

    async def load_dns_zones(
        self, project_id: str, force_refresh: bool = False
    ) -> list[ManagedZone]:
        """Load DNS zones for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of ManagedZone instances
        """
        key = (project_id, "dns_zones")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            zones = self._dns_zones.get(project_id, [])
            logger.info(f"Returning {len(zones)} DNS zones from state for {project_id}")
            return zones

        # Load from service
        service = await get_clouddns_service()
        zones = await service.list_zones(project_id, use_cache=not force_refresh)

        # Store in state
        self._dns_zones[project_id] = zones
        self._loaded.add(key)

        logger.info(f"Loaded {len(zones)} DNS zones into state for {project_id}")
        return zones

    async def load_dns_records(
        self, project_id: str, zone_name: str, force_refresh: bool = False
    ) -> list[DNSRecord]:
        """Load DNS records for a specific zone.

        Args:
            project_id: GCP project ID
            zone_name: Name of the managed zone
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of DNSRecord instances
        """
        key = (project_id, zone_name, "dns_records")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            records = self._dns_records.get((project_id, zone_name), [])
            logger.info(
                f"Returning {len(records)} DNS records from state for {project_id}/{zone_name}"
            )
            return records

        # Load from service
        service = await get_clouddns_service()
        records = await service.list_records(project_id, zone_name, use_cache=not force_refresh)

        # Store in state
        self._dns_records[(project_id, zone_name)] = records
        self._loaded.add(key)

        logger.info(
            f"Loaded {len(records)} DNS records into state for {project_id}/{zone_name}"
        )
        return records

    async def load_cloudsql_instances(
        self, project_id: str, force_refresh: bool = False
    ) -> list[CloudSQLInstance]:
        """Load Cloud SQL instances for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of CloudSQLInstance instances
        """
        key = (project_id, "cloudsql")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            instances = self._cloudsql.get(project_id, [])
            logger.info(
                f"Returning {len(instances)} Cloud SQL instances from state for {project_id}"
            )
            return instances

        # Load from service
        service = await get_cloudsql_service()
        instances = await service.list_instances(project_id, use_cache=not force_refresh)

        # Store in state
        self._cloudsql[project_id] = instances
        self._loaded.add(key)

        logger.info(f"Loaded {len(instances)} Cloud SQL instances into state for {project_id}")
        return instances

    async def load_compute_groups(
        self, project_id: str, force_refresh: bool = False
    ) -> list[InstanceGroup]:
        """Load Compute instance groups for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of InstanceGroup instances
        """
        key = (project_id, "compute_groups")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            groups = self._compute_groups.get(project_id, [])
            logger.info(
                f"Returning {len(groups)} instance groups from state for {project_id}"
            )
            return groups

        # Load from service
        service = await get_compute_service()
        groups = await service.list_instance_groups(project_id, use_cache=not force_refresh)

        # Store in state
        self._compute_groups[project_id] = groups
        self._loaded.add(key)

        logger.info(f"Loaded {len(groups)} instance groups into state for {project_id}")
        return groups

    async def load_compute_instances(
        self, project_id: str, group_name: str, zone: str, force_refresh: bool = False
    ) -> list[ComputeInstance]:
        """Load Compute instances for an instance group (zonal or regional).

        Args:
            project_id: GCP project ID
            group_name: Name of the instance group
            zone: Zone or region of the instance group
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of ComputeInstance instances
        """
        key = (project_id, group_name, "compute_instances")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            instances = self._compute_instances.get((project_id, group_name), [])
            logger.info(
                f"Returning {len(instances)} instances from state for {project_id}/{group_name}"
            )
            return instances

        # Load from service
        service = await get_compute_service()

        # Detect if this is a zone (ends with letter like -a, -b) or region
        # Zones look like "us-central1-a", regions look like "us-central1"
        is_zone = zone and len(zone.split("-")) > 2

        if is_zone:
            # Zonal instance group
            instances = await service.list_instances_in_group(
                project_id, zone, group_name, use_cache=not force_refresh
            )
        else:
            # Regional instance group
            instances = await service.list_instances_in_regional_group(
                project_id, zone, group_name, use_cache=not force_refresh
            )

        # Store in state
        self._compute_instances[(project_id, group_name)] = instances
        self._loaded.add(key)

        logger.info(
            f"Loaded {len(instances)} instances into state for {project_id}/{group_name}"
        )
        return instances

    async def load_gke_clusters(
        self, project_id: str, force_refresh: bool = False
    ) -> list[GKECluster]:
        """Load GKE clusters for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of GKECluster instances
        """
        key = (project_id, "gke_clusters")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            clusters = self._gke_clusters.get(project_id, [])
            logger.info(f"Returning {len(clusters)} GKE clusters from state for {project_id}")
            return clusters

        # Load from service
        service = await get_gke_service()
        clusters = await service.list_clusters(project_id, use_cache=not force_refresh)

        # Store in state
        self._gke_clusters[project_id] = clusters
        self._loaded.add(key)

        logger.info(f"Loaded {len(clusters)} GKE clusters into state for {project_id}")
        return clusters

    async def load_gke_nodes(
        self, project_id: str, cluster_name: str, zone: str, force_refresh: bool = False
    ) -> list[GKENode]:
        """Load GKE nodes for a cluster.

        Args:
            project_id: GCP project ID
            cluster_name: Name of the GKE cluster
            zone: Zone of the cluster
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of GKENode instances
        """
        key = (project_id, cluster_name, "gke_nodes")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            nodes = self._gke_nodes.get((project_id, cluster_name), [])
            logger.info(
                f"Returning {len(nodes)} GKE nodes from state for {project_id}/{cluster_name}"
            )
            return nodes

        # Load from service
        service = await get_gke_service()
        nodes = await service.list_nodes(
            project_id, cluster_name, zone, use_cache=not force_refresh
        )

        # Store in state
        self._gke_nodes[(project_id, cluster_name)] = nodes
        self._loaded.add(key)

        logger.info(f"Loaded {len(nodes)} GKE nodes into state for {project_id}/{cluster_name}")
        return nodes

    async def load_secrets(self, project_id: str, force_refresh: bool = False) -> list[Secret]:
        """Load secrets for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of Secret instances
        """
        key = (project_id, "secrets")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            secrets = self._secrets.get(project_id, [])
            logger.info(f"Returning {len(secrets)} secrets from state for {project_id}")
            return secrets

        # Load from service
        service = await get_secret_manager_service()
        secrets = await service.list_secrets(project_id, use_cache=not force_refresh)

        # Store in state
        self._secrets[project_id] = secrets
        self._loaded.add(key)

        logger.info(f"Loaded {len(secrets)} secrets into state for {project_id}")
        return secrets

    async def load_iam_accounts(
        self, project_id: str, force_refresh: bool = False
    ) -> list[ServiceAccount]:
        """Load IAM service accounts for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of ServiceAccount instances
        """
        key = (project_id, "iam_accounts")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            accounts = self._iam_accounts.get(project_id, [])
            logger.info(
                f"Returning {len(accounts)} service accounts from state for {project_id}"
            )
            return accounts

        # Load from service
        service = await get_iam_service()
        accounts = await service.list_service_accounts(project_id, use_cache=not force_refresh)

        # Store in state
        self._iam_accounts[project_id] = accounts
        self._loaded.add(key)

        logger.info(f"Loaded {len(accounts)} service accounts into state for {project_id}")
        return accounts

    async def load_iam_roles(
        self, project_id: str, account_email: str, force_refresh: bool = False
    ) -> list[IAMRoleBinding]:
        """Load IAM role bindings for a service account.

        Args:
            project_id: GCP project ID
            account_email: Email of the service account
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of IAMRoleBinding instances
        """
        key = (project_id, account_email, "iam_roles")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            roles = self._iam_roles.get((project_id, account_email), [])
            logger.info(
                f"Returning {len(roles)} IAM roles from state for {project_id}/{account_email}"
            )
            return roles

        # Load from service
        service = await get_iam_service()
        roles = await service.get_service_account_roles(
            project_id, account_email, use_cache=not force_refresh
        )

        # Store in state
        self._iam_roles[(project_id, account_email)] = roles
        self._loaded.add(key)

        logger.info(
            f"Loaded {len(roles)} IAM roles into state for {project_id}/{account_email}"
        )
        return roles

    def is_loaded(self, *key_parts: str) -> bool:
        """Check if a resource type has been loaded into state.

        Args:
            *key_parts: Variable parts of the key (e.g., project_id, "dns_zones")

        Returns:
            True if the resource has been loaded, False otherwise
        """
        return tuple(key_parts) in self._loaded

    def get_project(self, project_id: str) -> Project | None:
        """Get project from state.

        Args:
            project_id: GCP project ID

        Returns:
            Project instance or None if not loaded
        """
        return self._projects.get(project_id)

    def get_dns_zones(self, project_id: str) -> list[ManagedZone]:
        """Get DNS zones from state (returns empty list if not loaded).

        Args:
            project_id: GCP project ID

        Returns:
            List of ManagedZone instances (empty if not loaded)
        """
        return self._dns_zones.get(project_id, [])

    def get_dns_records(self, project_id: str, zone_name: str) -> list[DNSRecord]:
        """Get DNS records from state (returns empty list if not loaded).

        Args:
            project_id: GCP project ID
            zone_name: Name of the managed zone

        Returns:
            List of DNSRecord instances (empty if not loaded)
        """
        return self._dns_records.get((project_id, zone_name), [])

    def invalidate_project(self, project_id: str) -> None:
        """Clear all cached data for a specific project.

        This removes the project and all its resources from state.

        Args:
            project_id: GCP project ID to invalidate
        """
        logger.info(f"Invalidating project {project_id} from state")

        # Remove from loaded tracking
        keys_to_remove = [k for k in self._loaded if k[0] == project_id]
        for key in keys_to_remove:
            self._loaded.discard(key)

        # Clear project data
        self._projects.pop(project_id, None)
        self._dns_zones.pop(project_id, None)
        self._cloudsql.pop(project_id, None)
        self._compute_groups.pop(project_id, None)
        self._gke_clusters.pop(project_id, None)
        self._secrets.pop(project_id, None)
        self._iam_accounts.pop(project_id, None)

        # Clear resource-specific data
        dns_records_keys = [k for k in self._dns_records if k[0] == project_id]
        for key in dns_records_keys:
            self._dns_records.pop(key, None)

        compute_instances_keys = [k for k in self._compute_instances if k[0] == project_id]
        for key in compute_instances_keys:
            self._compute_instances.pop(key, None)

        gke_nodes_keys = [k for k in self._gke_nodes if k[0] == project_id]
        for key in gke_nodes_keys:
            self._gke_nodes.pop(key, None)

        iam_roles_keys = [k for k in self._iam_roles if k[0] == project_id]
        for key in iam_roles_keys:
            self._iam_roles.pop(key, None)

    async def load_all_resources(
        self,
        projects: list[Project],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """Eagerly load all resources for all projects.

        This loads all resource types for each project in parallel where possible.
        Used for initial application startup to populate the entire tree.

        Args:
            projects: List of projects to load resources for
            progress_callback: Optional callback(current, total, message) to report progress
        """
        import asyncio

        total_projects = len(projects)
        logger.info(f"Starting eager load of all resources for {total_projects} projects")

        for i, project in enumerate(projects, start=1):
            project_id = project.project_id

            if progress_callback:
                progress_callback(i - 1, total_projects, f"Loading {project.display_name}...")

            logger.info(f"Loading all resources for project {project_id} ({i}/{total_projects})")

            # Load all resource types in parallel for this project
            results = await asyncio.gather(
                self.load_dns_zones(project_id),
                self.load_cloudsql_instances(project_id),
                self.load_compute_groups(project_id),
                self.load_gke_clusters(project_id),
                self.load_secrets(project_id),
                self.load_iam_accounts(project_id),
                return_exceptions=True,  # Don't fail entire load if one resource type fails
            )

            # Log any errors that occurred
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    resource_types = [
                        "DNS zones",
                        "CloudSQL instances",
                        "Compute groups",
                        "GKE clusters",
                        "Secrets",
                        "IAM accounts",
                    ]
                    logger.warning(
                        f"Failed to load {resource_types[idx]} for {project_id}: {result}"
                    )

            # Yield to event loop to allow UI updates
            await asyncio.sleep(0)

        if progress_callback:
            progress_callback(total_projects, total_projects, "Loading complete!")

        logger.info(f"Completed eager load of all resources for {total_projects} projects")

    def invalidate_all(self) -> None:
        """Clear ALL cached state.

        This removes all projects and resources from state. Used for full refresh.
        """
        logger.info("Invalidating all state")

        self._projects.clear()
        self._dns_zones.clear()
        self._dns_records.clear()
        self._cloudsql.clear()
        self._compute_groups.clear()
        self._compute_instances.clear()
        self._gke_clusters.clear()
        self._gke_nodes.clear()
        self._secrets.clear()
        self._iam_accounts.clear()
        self._iam_roles.clear()
        self._loaded.clear()


# Global singleton instance
_resource_state: ResourceState | None = None


def get_resource_state() -> ResourceState:
    """Get the global resource state singleton.

    Returns:
        ResourceState instance
    """
    global _resource_state
    if _resource_state is None:
        _resource_state = ResourceState()
    return _resource_state


def reset_resource_state() -> None:
    """Reset the global state (for testing).

    This creates a fresh ResourceState instance, discarding the old one.
    """
    global _resource_state
    _resource_state = None
