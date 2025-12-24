"""Centralized state manager for in-memory GCP resource data."""

from sequel.config import get_config
from sequel.models.clouddns import DNSRecord, ManagedZone
from sequel.models.cloudsql import CloudSQLInstance
from sequel.models.compute import ComputeInstance, InstanceGroup
from sequel.models.firewall import FirewallPolicy
from sequel.models.gke import GKECluster, GKENode
from sequel.models.iam import IAMRoleBinding, ServiceAccount
from sequel.models.monitoring import AlertPolicy
from sequel.models.networks import Subnet, VPCNetwork
from sequel.models.project import Project
from sequel.models.pubsub import Subscription, Topic
from sequel.models.secrets import Secret
from sequel.models.storage import Bucket, StorageObject
from sequel.services.clouddns import get_clouddns_service
from sequel.services.cloudsql import get_cloudsql_service
from sequel.services.compute import get_compute_service
from sequel.services.firewall import get_firewall_service
from sequel.services.gke import get_gke_service
from sequel.services.iam import get_iam_service
from sequel.services.monitoring import get_monitoring_service
from sequel.services.networks import get_networks_service
from sequel.services.projects import get_project_service
from sequel.services.pubsub import get_pubsub_service
from sequel.services.secrets import get_secret_manager_service
from sequel.services.storage import get_storage_service
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceState:
    """Centralized state manager for GCP resources.

    This class maintains an in-memory cache of all loaded GCP resources.
    Resources are loaded from services on-demand and cached here. The tree
    widget renders from this state rather than calling APIs directly.

    The state tracks what has been loaded to avoid redundant API calls.
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
        self._firewalls: dict[str, list[FirewallPolicy]] = {}
        self._buckets: dict[str, list[Bucket]] = {}
        self._storage_objects: dict[tuple[str, str], list[StorageObject]] = {}
        self._pubsub_topics: dict[str, list[Topic]] = {}
        self._pubsub_subscriptions: dict[str, list[Subscription]] = {}
        self._networks: dict[str, list[VPCNetwork]] = {}
        self._subnets: dict[str, list[Subnet]] = {}
        self._alert_policies: dict[str, list[AlertPolicy]] = {}

        # Track what's been loaded - set of tuple keys
        self._loaded: set[tuple[str, ...]] = set()

    async def load_projects(self, force_refresh: bool = False) -> list[Project]:
        """Load projects into state from API.

        Args:
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of Project instances (filtered by project_filter_regex if configured)
        """
        key = ("projects",)

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            logger.info(f"Returning {len(self._projects)} projects from state")
            return list(self._projects.values())

        # Load from service (service has its own cache layer)
        service = await get_project_service()
        projects = await service.list_projects(use_cache=not force_refresh)

        # Apply project filter BEFORE storing in state
        # This ensures we only store and enumerate projects that match the filter
        config = get_config()
        if config.project_filter_regex:
            import re
            try:
                # Note: Regex is already validated in config.py during load time
                # This try-except is kept as a safety measure
                pattern = re.compile(config.project_filter_regex)
                original_count = len(projects)
                projects = [
                    p for p in projects
                    if pattern.match(p.project_id) or pattern.match(p.display_name)
                ]
                logger.info(
                    f"Applied project filter '{config.project_filter_regex}': "
                    f"{original_count} -> {len(projects)} projects"
                )
            except re.error as e:
                # This should never happen due to validation at config load time
                logger.error(f"Invalid project filter regex (should have been caught at config load): {e}")

        # Store in state (only filtered projects)
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
        # Note: Zones in state are already filtered, so no need to filter again
        if not force_refresh and key in self._loaded:
            zones = self._dns_zones.get(project_id, [])
            logger.info(f"Returning {len(zones)} filtered DNS zones from state for {project_id}")
            return zones

        # Load from service
        service = await get_clouddns_service()
        zones = await service.list_zones(project_id, use_cache=not force_refresh)

        # Apply DNS zone filter BEFORE storing in state
        # This ensures we only store and enumerate zones that match the filter
        config = get_config()
        if config.dns_zone_filter:
            original_count = len(zones)
            zones = [z for z in zones if config.dns_zone_filter.lower() in z.dns_name.lower()]
            logger.info(
                f"Applied DNS zone filter '{config.dns_zone_filter}': "
                f"{original_count} -> {len(zones)} zones for {project_id}"
            )

        # Store in state (only filtered zones)
        self._dns_zones[project_id] = zones
        self._loaded.add(key)

        logger.info(f"Loaded {len(zones)} DNS zones into state for {project_id}")
        return zones

    async def load_dns_records(
        self, project_id: str, zone_name: str, force_refresh: bool = False
    ) -> list[DNSRecord]:
        """Load DNS records for a zone.

        Args:
            project_id: GCP project ID
            zone_name: DNS zone name
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of DNSRecord instances
        """
        key = (project_id, zone_name, "dns_records")

        # Return from state if already loaded and not forcing refresh
        if not force_refresh and key in self._loaded:
            records = self._dns_records.get((project_id, zone_name), [])
            logger.info(
                f"Returning {len(records)} DNS records from state for {zone_name} in {project_id}"
            )
            return records

        # Load from service
        service = await get_clouddns_service()
        records = await service.list_records(
            project_id=project_id, zone_name=zone_name, use_cache=not force_refresh
        )

        # Store in state
        self._dns_records[(project_id, zone_name)] = records
        self._loaded.add(key)

        logger.info(
            f"Loaded {len(records)} DNS records into state for {zone_name} in {project_id}"
        )
        return records

    async def load_cloudsql_instances(
        self, project_id: str, force_refresh: bool = False
    ) -> list[CloudSQLInstance]:
        """Load CloudSQL instances for a project."""
        key = (project_id, "cloudsql")

        if not force_refresh and key in self._loaded:
            instances = self._cloudsql.get(project_id, [])
            logger.info(f"Returning {len(instances)} CloudSQL instances from state")
            return instances

        service = await get_cloudsql_service()
        instances = await service.list_instances(project_id, use_cache=not force_refresh)

        self._cloudsql[project_id] = instances
        self._loaded.add(key)

        logger.info(f"Loaded {len(instances)} CloudSQL instances into state")
        return instances

    async def load_compute_groups(
        self, project_id: str, force_refresh: bool = False
    ) -> list[InstanceGroup]:
        """Load compute instance groups for a project."""
        key = (project_id, "compute_groups")

        if not force_refresh and key in self._loaded:
            groups = self._compute_groups.get(project_id, [])
            logger.info(f"Returning {len(groups)} compute groups from state")
            return groups

        service = await get_compute_service()
        groups = await service.list_instance_groups(project_id, use_cache=not force_refresh)

        self._compute_groups[project_id] = groups
        self._loaded.add(key)

        logger.info(f"Loaded {len(groups)} compute groups into state")
        return groups

    async def load_gke_clusters(
        self, project_id: str, force_refresh: bool = False
    ) -> list[GKECluster]:
        """Load GKE clusters for a project."""
        key = (project_id, "gke_clusters")

        if not force_refresh and key in self._loaded:
            clusters = self._gke_clusters.get(project_id, [])
            logger.info(f"Returning {len(clusters)} GKE clusters from state")
            return clusters

        service = await get_gke_service()
        clusters = await service.list_clusters(project_id, use_cache=not force_refresh)

        self._gke_clusters[project_id] = clusters
        self._loaded.add(key)

        logger.info(f"Loaded {len(clusters)} GKE clusters into state")
        return clusters

    async def load_secrets(
        self, project_id: str, force_refresh: bool = False
    ) -> list[Secret]:
        """Load secrets for a project."""
        key = (project_id, "secrets")

        if not force_refresh and key in self._loaded:
            secrets = self._secrets.get(project_id, [])
            logger.info(f"Returning {len(secrets)} secrets from state")
            return secrets

        service = await get_secret_manager_service()
        secrets = await service.list_secrets(project_id, use_cache=not force_refresh)

        self._secrets[project_id] = secrets
        self._loaded.add(key)

        logger.info(f"Loaded {len(secrets)} secrets into state")
        return secrets

    async def load_iam_accounts(
        self, project_id: str, force_refresh: bool = False
    ) -> list[ServiceAccount]:
        """Load IAM service accounts for a project."""
        key = (project_id, "iam_accounts")

        if not force_refresh and key in self._loaded:
            accounts = self._iam_accounts.get(project_id, [])
            logger.info(f"Returning {len(accounts)} IAM accounts from state")
            return accounts

        service = await get_iam_service()
        accounts = await service.list_service_accounts(project_id, use_cache=not force_refresh)

        self._iam_accounts[project_id] = accounts
        self._loaded.add(key)

        logger.info(f"Loaded {len(accounts)} IAM accounts into state")
        return accounts

    async def load_firewalls(
        self, project_id: str, force_refresh: bool = False
    ) -> list[FirewallPolicy]:
        """Load firewall policies for a project."""
        key = (project_id, "firewalls")

        if not force_refresh and key in self._loaded:
            firewalls = self._firewalls.get(project_id, [])
            logger.info(f"Returning {len(firewalls)} firewall policies from state")
            return firewalls

        service = await get_firewall_service()
        firewalls = await service.list_firewall_policies(project_id, use_cache=not force_refresh)

        self._firewalls[project_id] = firewalls
        self._loaded.add(key)

        logger.info(f"Loaded {len(firewalls)} firewall policies into state")
        return firewalls

    async def load_alert_policies(
        self, project_id: str, force_refresh: bool = False
    ) -> list[AlertPolicy]:
        """Load Cloud Monitoring alert policies for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of AlertPolicy instances
        """
        key = (project_id, "alert_policies")

        if not force_refresh and key in self._loaded:
            policies = self._alert_policies.get(project_id, [])
            logger.info(f"Returning {len(policies)} alert policies from state")
            return policies

        service = await get_monitoring_service()
        policies = await service.list_alert_policies(project_id, use_cache=not force_refresh)

        self._alert_policies[project_id] = policies
        self._loaded.add(key)

        logger.info(f"Loaded {len(policies)} alert policies into state")
        return policies

    async def load_buckets(
        self, project_id: str, force_refresh: bool = False
    ) -> list[Bucket]:
        """Load Cloud Storage buckets for a project."""
        key = (project_id, "buckets")

        if not force_refresh and key in self._loaded:
            buckets = self._buckets.get(project_id, [])
            logger.info(f"Returning {len(buckets)} buckets from state")
            return buckets

        service = await get_storage_service()
        buckets = await service.list_buckets(project_id, use_cache=not force_refresh)

        self._buckets[project_id] = buckets
        self._loaded.add(key)

        logger.info(f"Loaded {len(buckets)} buckets into state")
        return buckets

    async def load_storage_objects(
        self, project_id: str, bucket_name: str, force_refresh: bool = False
    ) -> list[StorageObject]:
        """Load objects from a Cloud Storage bucket.

        Args:
            project_id: GCP project ID
            bucket_name: Name of the bucket
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of StorageObject instances
        """
        key = (project_id, "storage_objects", bucket_name)

        if not force_refresh and key in self._loaded:
            objects = self._storage_objects.get((project_id, bucket_name), [])
            logger.info(f"Returning {len(objects)} objects from state for bucket: {bucket_name}")
            return objects

        service = await get_storage_service()
        objects = await service.list_objects(
            project_id, bucket_name, use_cache=not force_refresh
        )

        self._storage_objects[(project_id, bucket_name)] = objects
        self._loaded.add(key)

        logger.info(f"Loaded {len(objects)} objects into state for bucket: {bucket_name}")
        return objects

    def is_loaded(self, *key_parts: str) -> bool:
        """Check if a resource type has been loaded into state.

        Args:
            *key_parts: Variable parts of the key (e.g., project_id, "dns_zones")

        Returns:
            True if the resource has been loaded, False otherwise
        """
        return tuple(key_parts) in self._loaded

    def get_projects(self) -> list[Project]:
        """Get all projects from state."""
        return list(self._projects.values())

    def get_dns_zones(self, project_id: str) -> list[ManagedZone]:
        """Get DNS zones from state (returns empty list if not loaded)."""
        return self._dns_zones.get(project_id, [])

    def get_dns_records(self, project_id: str, zone_name: str) -> list[DNSRecord]:
        """Get DNS records from state (returns empty list if not loaded)."""
        return self._dns_records.get((project_id, zone_name), [])

    def get_cloudsql_instances(self, project_id: str) -> list[CloudSQLInstance]:
        """Get CloudSQL instances from state."""
        return self._cloudsql.get(project_id, [])

    def get_compute_groups(self, project_id: str) -> list[InstanceGroup]:
        """Get compute groups from state."""
        return self._compute_groups.get(project_id, [])

    def get_gke_clusters(self, project_id: str) -> list[GKECluster]:
        """Get GKE clusters from state."""
        return self._gke_clusters.get(project_id, [])

    def get_secrets(self, project_id: str) -> list[Secret]:
        """Get secrets from state."""
        return self._secrets.get(project_id, [])

    def get_iam_accounts(self, project_id: str) -> list[ServiceAccount]:
        """Get IAM accounts from state."""
        return self._iam_accounts.get(project_id, [])

    def get_firewalls(self, project_id: str) -> list[FirewallPolicy]:
        """Get firewall policies from state."""
        return self._firewalls.get(project_id, [])

    def get_alert_policies(self, project_id: str) -> list[AlertPolicy]:
        """Get Cloud Monitoring alert policies from state."""
        return self._alert_policies.get(project_id, [])

    def get_buckets(self, project_id: str) -> list[Bucket]:
        """Get Cloud Storage buckets from state."""
        return self._buckets.get(project_id, [])

    def get_storage_objects(self, project_id: str, bucket_name: str) -> list[StorageObject]:
        """Get objects from state for a specific bucket."""
        return self._storage_objects.get((project_id, bucket_name), [])

    async def load_pubsub_topics(
        self, project_id: str, force_refresh: bool = False
    ) -> list[Topic]:
        """Load Pub/Sub topics for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of Topic instances
        """
        key = (project_id, "pubsub_topics")

        if not force_refresh and key in self._loaded:
            topics = self._pubsub_topics.get(project_id, [])
            logger.info(f"Returning {len(topics)} Pub/Sub topics from state")
            return topics

        service = await get_pubsub_service()
        topics = await service.list_topics(project_id, use_cache=not force_refresh)

        self._pubsub_topics[project_id] = topics
        self._loaded.add(key)

        logger.info(f"Loaded {len(topics)} Pub/Sub topics into state")
        return topics

    async def load_pubsub_subscriptions(
        self, project_id: str, force_refresh: bool = False
    ) -> list[Subscription]:
        """Load Pub/Sub subscriptions for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of Subscription instances
        """
        key = (project_id, "pubsub_subscriptions")

        if not force_refresh and key in self._loaded:
            subscriptions = self._pubsub_subscriptions.get(project_id, [])
            logger.info(f"Returning {len(subscriptions)} Pub/Sub subscriptions from state")
            return subscriptions

        service = await get_pubsub_service()
        subscriptions = await service.list_subscriptions(project_id, use_cache=not force_refresh)

        self._pubsub_subscriptions[project_id] = subscriptions
        self._loaded.add(key)

        logger.info(f"Loaded {len(subscriptions)} Pub/Sub subscriptions into state")
        return subscriptions

    def get_pubsub_topics(self, project_id: str) -> list[Topic]:
        """Get Pub/Sub topics from state."""
        return self._pubsub_topics.get(project_id, [])

    def get_pubsub_subscriptions(self, project_id: str) -> list[Subscription]:
        """Get Pub/Sub subscriptions from state."""
        return self._pubsub_subscriptions.get(project_id, [])

    async def load_networks(
        self, project_id: str, force_refresh: bool = False
    ) -> list[VPCNetwork]:
        """Load VPC networks for a project.

        Args:
            project_id: GCP project ID
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of VPCNetwork instances
        """
        key = (project_id, "networks")

        if not force_refresh and key in self._loaded:
            networks = self._networks.get(project_id, [])
            logger.info(f"Returning {len(networks)} VPC networks from state")
            return networks

        service = await get_networks_service()
        networks = await service.list_networks(project_id, use_cache=not force_refresh)

        self._networks[project_id] = networks
        self._loaded.add(key)

        logger.info(f"Loaded {len(networks)} VPC networks into state")
        return networks

    async def load_subnets(
        self, project_id: str, network_name: str | None = None, force_refresh: bool = False
    ) -> list[Subnet]:
        """Load subnets for a project, optionally filtered by network.

        Args:
            project_id: GCP project ID
            network_name: Optional network name to filter by
            force_refresh: If True, bypass state cache and reload from API

        Returns:
            List of Subnet instances
        """
        # Use different keys for all subnets vs filtered by network
        key = (project_id, "subnets") if network_name is None else (project_id, "subnets", network_name)

        if not force_refresh and key in self._loaded:
            # For filtered requests, filter from cached subnets
            all_subnets = self._subnets.get(project_id, [])
            if network_name is None:
                subnets = all_subnets
            else:
                subnets = [s for s in all_subnets if s.network_name == network_name]
            logger.info(f"Returning {len(subnets)} subnets from state")
            return subnets

        service = await get_networks_service()
        subnets = await service.list_subnets(
            project_id, network_name=network_name, use_cache=not force_refresh
        )

        # Store all subnets (or update with filtered results)
        if network_name is None:
            self._subnets[project_id] = subnets
        else:
            # Merge filtered subnets into existing cache
            existing = self._subnets.get(project_id, [])
            # Remove old subnets for this network
            existing = [s for s in existing if s.network_name != network_name]
            # Add new subnets
            self._subnets[project_id] = existing + subnets

        self._loaded.add(key)

        logger.info(f"Loaded {len(subnets)} subnets into state")
        return subnets

    def get_networks(self, project_id: str) -> list[VPCNetwork]:
        """Get VPC networks from state."""
        return self._networks.get(project_id, [])

    def get_subnets(self, project_id: str) -> list[Subnet]:
        """Get subnets from state."""
        return self._subnets.get(project_id, [])


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
    """Reset the global resource state singleton.

    This is primarily for testing to ensure a clean state between tests.
    """
    global _resource_state
    _resource_state = None
