"""Integration test fixtures and utilities."""

from typing import Any
from unittest.mock import MagicMock


def create_mock_project(
    project_id: str,
    display_name: str,
    state: str = "ACTIVE",
    create_time: str = "2024-01-01T00:00:00Z",
    labels: dict[str, str] | None = None,
    parent: str = "",
) -> MagicMock:
    """Create a mock protobuf project object.

    Args:
        project_id: Project ID
        display_name: Display name
        state: Lifecycle state (default: ACTIVE)
        create_time: ISO timestamp
        labels: Project labels
        parent: Parent resource

    Returns:
        MagicMock configured like protobuf Project
    """
    mock_proj = MagicMock()
    mock_proj.name = f"projects/{project_id}"
    mock_proj.project_id = project_id
    mock_proj.display_name = display_name

    # State enum mock - str() should return the state value
    state_mock = MagicMock()
    state_mock.name = state
    state_mock.__str__ = MagicMock(return_value=state)
    mock_proj.state = state_mock

    # Create time mock
    create_time_mock = MagicMock()
    create_time_mock.isoformat = MagicMock(return_value=create_time)
    mock_proj.create_time = create_time_mock

    mock_proj.labels = labels or {}
    mock_proj.parent = parent

    return mock_proj


def create_mock_gke_cluster(
    name: str,
    location: str = "us-central1",
    status: str = "RUNNING",
    master_version: str = "1.27.3-gke.100",
    node_version: str = "1.27.3-gke.100",
    node_pools: list[Any] | None = None,
) -> MagicMock:
    """Create a mock GKE cluster protobuf object.

    Args:
        name: Cluster name
        location: GCP location
        status: Cluster status
        master_version: Kubernetes master version
        node_version: Node version
        node_pools: List of node pools

    Returns:
        MagicMock configured like protobuf Cluster
    """
    mock_cluster = MagicMock()
    mock_cluster.name = name
    mock_cluster.location = location

    # Status enum mock - str() should return the status value
    status_mock = MagicMock()
    status_mock.name = status
    status_mock.__str__ = MagicMock(return_value=status)
    mock_cluster.status = status_mock

    mock_cluster.current_master_version = master_version
    mock_cluster.current_node_version = node_version
    mock_cluster.node_pools = node_pools or []

    # Additional required fields for GKECluster model
    mock_cluster.endpoint = "10.0.0.1"  # IP address
    mock_cluster.self_link = f"https://container.googleapis.com/v1/projects/test/locations/{location}/clusters/{name}"

    return mock_cluster


def create_mock_secret(
    name: str,
    project_id: str,
    create_time: str = "2024-01-01T00:00:00Z",
    labels: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock Secret Manager secret protobuf object.

    Args:
        name: Secret name (short name, not full path)
        project_id: Project ID
        create_time: ISO timestamp
        labels: Secret labels

    Returns:
        MagicMock configured like protobuf Secret
    """
    mock_secret = MagicMock()
    mock_secret.name = f"projects/{project_id}/secrets/{name}"

    # Replication mock
    replication_mock = MagicMock()
    replication_mock.automatic = MagicMock()
    mock_secret.replication = replication_mock

    # Create time mock
    create_time_mock = MagicMock()
    create_time_mock.isoformat = MagicMock(return_value=create_time)
    mock_secret.create_time = create_time_mock

    mock_secret.labels = labels or {}

    return mock_secret
