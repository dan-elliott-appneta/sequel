"""Google Cloud Project service using Resource Manager API."""

from typing import Any, cast

from google.cloud import resourcemanager_v3

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.project import Project
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class ProjectService(BaseService):
    """Service for interacting with Google Cloud Projects via Resource Manager API."""

    def __init__(self) -> None:
        """Initialize the Project service."""
        super().__init__()
        self._client: resourcemanager_v3.ProjectsClient | None = None
        self._cache = get_cache()

    async def _get_client(self) -> resourcemanager_v3.ProjectsClient:
        """Get or create the Resource Manager client.

        Returns:
            Initialized ProjectsClient
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = resourcemanager_v3.ProjectsClient(
                credentials=auth_manager.credentials
            )
        return self._client

    async def list_projects(
        self,
        parent: str | None = None,
        use_cache: bool = True,
    ) -> list[Project]:
        """List all accessible projects.

        Args:
            parent: Optional parent resource (e.g., "organizations/123456")
            use_cache: Whether to use cached results

        Returns:
            List of Project instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"projects:{parent or 'all'}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} projects from cache")
                return cast("list[Project]", cached)

        async def _list_projects() -> list[Project]:
            """Internal function to list projects."""
            client = await self._get_client()

            logger.info(f"Listing projects{f' under {parent}' if parent else ''}")

            # Execute request with pagination
            projects: list[Project] = []
            try:
                if parent:
                    # Use ListProjects when parent is specified
                    request = resourcemanager_v3.ListProjectsRequest(
                        parent=parent,
                        page_size=100,
                    )
                    for project_proto in client.list_projects(request=request):
                        project_dict = self._proto_to_dict(project_proto)
                        project = Project.from_api_response(project_dict)
                        projects.append(project)
                else:
                    # Use SearchProjects to get all accessible projects
                    request = resourcemanager_v3.SearchProjectsRequest(
                        page_size=100,
                    )
                    for project_proto in client.search_projects(request=request):
                        project_dict = self._proto_to_dict(project_proto)
                        project = Project.from_api_response(project_dict)
                        projects.append(project)

                logger.info(f"Found {len(projects)} projects")
                return projects

            except Exception as e:
                logger.error(f"Failed to list projects: {e}")
                raise

        # Execute with retry logic
        projects = await self._execute_with_retry(
            operation=_list_projects,
            operation_name=f"list_projects(parent={parent})",
        )

        # Cache the results
        if use_cache:
            ttl = get_config().cache_ttl_projects
            await self._cache.set(cache_key, projects, ttl)

        return projects

    async def get_project(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: The project ID to retrieve
            use_cache: Whether to use cached results

        Returns:
            Project instance or None if not found

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"project:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning project {project_id} from cache")
                return cast("Project", cached)

        async def _get_project() -> Project | None:
            """Internal function to get project."""
            client = await self._get_client()

            request = resourcemanager_v3.GetProjectRequest(
                name=f"projects/{project_id}"
            )

            logger.info(f"Getting project: {project_id}")

            try:
                project_proto = client.get_project(request=request)
                project_dict = self._proto_to_dict(project_proto)
                project = Project.from_api_response(project_dict)
                logger.info(f"Retrieved project: {project_id}")
                return project

            except Exception as e:
                logger.error(f"Failed to get project {project_id}: {e}")
                return None

        # Execute with retry logic
        project = await self._execute_with_retry(
            operation=_get_project,
            operation_name=f"get_project({project_id})",
        )

        # Cache the result
        if use_cache and project is not None:
            ttl = get_config().cache_ttl_projects
            await self._cache.set(cache_key, project, ttl)

        return project

    def _proto_to_dict(self, proto_message: Any) -> dict[str, Any]:
        """Convert protobuf message to dictionary.

        Args:
            proto_message: Protobuf message

        Returns:
            Dictionary representation
        """
        # Convert protobuf to dict
        result: dict[str, Any] = {}

        # Handle common project fields
        if hasattr(proto_message, "name"):
            result["name"] = proto_message.name
        if hasattr(proto_message, "project_id"):
            result["projectId"] = proto_message.project_id
        if hasattr(proto_message, "display_name"):
            result["displayName"] = proto_message.display_name
        if hasattr(proto_message, "state"):
            # state is an enum, get the name
            result["lifecycleState"] = proto_message.state.name
        if hasattr(proto_message, "create_time"):
            result["createTime"] = proto_message.create_time.isoformat()
        if hasattr(proto_message, "labels"):
            result["labels"] = dict(proto_message.labels)
        if hasattr(proto_message, "parent"):
            result["parent"] = proto_message.parent

        return result


# Global service instance
_project_service: ProjectService | None = None


async def get_project_service() -> ProjectService:
    """Get the global project service instance.

    Returns:
        Initialized ProjectService
    """
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service


def reset_project_service() -> None:
    """Reset the global project service (mainly for testing)."""
    global _project_service
    _project_service = None
