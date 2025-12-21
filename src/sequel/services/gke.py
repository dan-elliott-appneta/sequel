"""Google Kubernetes Engine service using Container API."""

from typing import Any, cast

from google.cloud import container_v1

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.gke import GKECluster
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class GKEService(BaseService):
    """Service for interacting with Google Kubernetes Engine clusters."""

    def __init__(self) -> None:
        """Initialize the GKE service."""
        super().__init__()
        self._client: container_v1.ClusterManagerClient | None = None
        self._cache = get_cache()

    async def _get_client(self) -> container_v1.ClusterManagerClient:
        """Get or create the GKE client.

        Returns:
            Initialized ClusterManagerClient
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = container_v1.ClusterManagerClient(
                credentials=auth_manager.credentials
            )
        return self._client

    async def list_clusters(
        self,
        project_id: str,
        location: str = "-",
        use_cache: bool = True,
    ) -> list[GKECluster]:
        """List all GKE clusters in a project.

        Args:
            project_id: GCP project ID
            location: GCP location (zone/region) or "-" for all locations
            use_cache: Whether to use cached results

        Returns:
            List of GKECluster instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"gke_clusters:{project_id}:{location}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} GKE clusters from cache")
                return cast("list[GKECluster]", cached)

        async def _list_clusters() -> list[GKECluster]:
            """Internal function to list clusters."""
            client = await self._get_client()

            logger.info(f"Listing GKE clusters in project: {project_id}, location: {location}")

            try:
                # Build parent path
                parent = f"projects/{project_id}/locations/{location}"

                # Call the API
                request = container_v1.ListClustersRequest(parent=parent)
                response = client.list_clusters(request=request)

                clusters: list[GKECluster] = []
                for cluster_proto in response.clusters:
                    cluster_dict = self._proto_to_dict(cluster_proto)
                    cluster = GKECluster.from_api_response(cluster_dict)
                    clusters.append(cluster)

                logger.info(f"Found {len(clusters)} GKE clusters")
                return clusters

            except Exception as e:
                logger.error(f"Failed to list GKE clusters: {e}")
                return []

        # Execute with retry logic
        clusters = await self._execute_with_retry(
            operation=_list_clusters,
            operation_name=f"list_gke_clusters({project_id})",
        )

        # Cache the results
        if use_cache:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, clusters, ttl)

        return clusters

    async def get_cluster(
        self,
        project_id: str,
        location: str,
        cluster_name: str,
        use_cache: bool = True,
    ) -> GKECluster | None:
        """Get a specific GKE cluster.

        Args:
            project_id: GCP project ID
            location: GCP location
            cluster_name: Cluster name
            use_cache: Whether to use cached results

        Returns:
            GKECluster or None if not found

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"gke_cluster:{project_id}:{location}:{cluster_name}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning GKE cluster {cluster_name} from cache")
                return cast("GKECluster", cached)

        async def _get_cluster() -> GKECluster | None:
            """Internal function to get cluster."""
            client = await self._get_client()

            logger.info(f"Getting GKE cluster: {project_id}/{location}/{cluster_name}")

            try:
                # Build cluster path
                name = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"

                request = container_v1.GetClusterRequest(name=name)
                cluster_proto = client.get_cluster(request=request)

                cluster_dict = self._proto_to_dict(cluster_proto)
                cluster = GKECluster.from_api_response(cluster_dict)

                logger.info(f"Retrieved GKE cluster: {cluster_name}")
                return cluster

            except Exception as e:
                logger.error(f"Failed to get GKE cluster {cluster_name}: {e}")
                return None

        # Execute with retry logic
        cluster = await self._execute_with_retry(
            operation=_get_cluster,
            operation_name=f"get_gke_cluster({project_id}, {cluster_name})",
        )

        # Cache the result
        if use_cache and cluster is not None:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, cluster, ttl)

        return cluster

    def _proto_to_dict(self, proto_message: Any) -> dict[str, Any]:
        """Convert protobuf message to dictionary.

        Args:
            proto_message: Protobuf message

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {}

        if hasattr(proto_message, "name"):
            result["name"] = proto_message.name
        if hasattr(proto_message, "location"):
            result["location"] = proto_message.location
        if hasattr(proto_message, "status"):
            # status is an enum
            result["status"] = str(proto_message.status)
        if hasattr(proto_message, "endpoint"):
            result["endpoint"] = proto_message.endpoint
        if hasattr(proto_message, "current_node_count"):
            result["currentNodeCount"] = proto_message.current_node_count
        if hasattr(proto_message, "current_master_version"):
            result["currentMasterVersion"] = proto_message.current_master_version
        if hasattr(proto_message, "self_link"):
            result["selfLink"] = proto_message.self_link

        return result


# Global service instance
_gke_service: GKEService | None = None


async def get_gke_service() -> GKEService:
    """Get the global GKE service instance.

    Returns:
        Initialized GKEService
    """
    global _gke_service
    if _gke_service is None:
        _gke_service = GKEService()
    return _gke_service


def reset_gke_service() -> None:
    """Reset the global GKE service (mainly for testing)."""
    global _gke_service
    _gke_service = None
