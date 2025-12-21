"""Google Kubernetes Engine (GKE) models."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class GKECluster(BaseModel):
    """Model for a Google Kubernetes Engine cluster."""

    cluster_name: str = Field(..., description="Cluster name")
    location: str | None = Field(None, description="GCP location (zone or region)")
    status: str = Field(default="RUNNING", description="Cluster status")
    endpoint: str | None = Field(None, description="Cluster endpoint URL")
    node_count: int = Field(default=0, description="Total number of nodes")
    version: str | None = Field(None, description="Kubernetes version")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "GKECluster":
        """Create GKECluster from GKE API response.

        Args:
            data: API response data from clusters.get()

        Returns:
            GKECluster instance

        Example API response structure:
            {
                "name": "my-cluster",
                "location": "us-central1-a",
                "status": "RUNNING",
                "endpoint": "35.192.0.1",
                "currentMasterVersion": "1.27.3-gke.100",
                "currentNodeCount": 3
            }
        """
        cluster_name = data.get("name", "")

        # Extract project_id from selfLink if available
        project_id = None
        self_link = data.get("selfLink", "")
        if self_link:
            # selfLink: https://container.googleapis.com/v1/projects/{project}/locations/{location}/clusters/{name}
            parts = self_link.split("/")
            if len(parts) >= 6:
                project_id = parts[5]

        return cls(
            id=cluster_name,
            name=cluster_name,
            project_id=project_id,
            created_at=None,  # GKE API doesn't provide creation time in basic cluster info
            cluster_name=cluster_name,
            location=data.get("location"),
            status=data.get("status", "UNKNOWN"),
            endpoint=data.get("endpoint"),
            node_count=data.get("currentNodeCount", 0),
            version=data.get("currentMasterVersion"),
            raw_data=data.copy(),
        )

    def is_running(self) -> bool:
        """Check if cluster is running.

        Returns:
            True if cluster is running, False otherwise
        """
        return self.status == "RUNNING"


class GKENode(BaseModel):
    """Model for a GKE cluster node."""

    node_name: str = Field(..., description="Node name")
    cluster_name: str = Field(..., description="Parent cluster name")
    machine_type: str | None = Field(None, description="Machine type")
    status: str = Field(default="READY", description="Node status")
    version: str | None = Field(None, description="Kubernetes version")

    @classmethod
    def from_api_response(cls, data: dict[str, Any], cluster_name: str) -> "GKENode":  # type: ignore[override]
        """Create GKENode from node data.

        Note: This method requires cluster_name as context, which is why it has
        a different signature than the base class.

        Args:
            data: Node data
            cluster_name: Parent cluster name

        Returns:
            GKENode instance
        """
        node_name = data.get("name", "")

        return cls(
            id=node_name,
            name=node_name,
            project_id=None,  # Node doesn't have direct project_id reference
            created_at=None,  # Node creation time not in basic API response
            node_name=node_name,
            cluster_name=cluster_name,
            machine_type=data.get("machineType"),
            status=data.get("status", "UNKNOWN"),
            version=data.get("version"),
            raw_data=data.copy(),
        )
