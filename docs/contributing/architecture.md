# Architecture Guide for Contributors

This guide explains how to extend Sequel's architecture by adding new resource types, services, widgets, and features.

## Table of Contents

1. [Adding a New Resource Type](#adding-a-new-resource-type)
2. [Creating a New Service](#creating-a-new-service)
3. [Adding a New Widget](#adding-a-new-widget)
4. [Extending the Tree View](#extending-the-tree-view)
5. [Adding Configuration Options](#adding-configuration-options)
6. [Error Handling Patterns](#error-handling-patterns)
7. [Testing Guidelines](#testing-guidelines)

---

## Adding a New Resource Type

### Step 1: Create Pydantic Model

**File:** `src/sequel/models/my_resource.py`

```python
"""Models for My Resource."""

from pydantic import Field

from sequel.models.base import BaseModel

class MyResource(BaseModel):
    """Represents a My Resource instance.

    Attributes:
        id: Unique identifier
        name: Display name
        status: Resource status
        project_id: Parent project ID
        location: GCP location
    """

    status: str = Field(..., description="Resource status")
    location: str | None = Field(None, description="GCP location")

    @classmethod
    def from_api_response(cls, data: dict[str, any]) -> "MyResource":  # type: ignore[valid-type]
        """Create model from GCP API response.

        Args:
            data: Raw API response

        Returns:
            MyResource instance
        """
        # Extract fields from API response
        return cls(
            id=data.get("name", ""),
            name=data.get("name", ""),
            project_id=data.get("projectId"),
            status=data.get("status", "UNKNOWN"),
            location=data.get("location"),
            raw_data=data,  # Store for detail pane
        )
```

**Key Points:**
- Extend `BaseModel` for standard fields (id, name, project_id, etc.)
- Add resource-specific fields with descriptions
- Implement `from_api_response()` to map API data
- Always store `raw_data` for JSON detail pane

### Step 2: Add to Models __init__.py

**File:** `src/sequel/models/__init__.py`

```python
from sequel.models.my_resource import MyResource

__all__ = [
    # ... existing exports
    "MyResource",
]
```

### Step 3: Create Tests

**File:** `tests/unit/models/test_my_resource.py`

```python
import pytest
from sequel.models.my_resource import MyResource

def test_my_resource_from_api_response():
    """Test creating MyResource from API response."""
    api_data = {
        "name": "my-resource-1",
        "projectId": "my-project",
        "status": "RUNNING",
        "location": "us-central1",
    }

    resource = MyResource.from_api_response(api_data)

    assert resource.id == "my-resource-1"
    assert resource.name == "my-resource-1"
    assert resource.project_id == "my-project"
    assert resource.status == "RUNNING"
    assert resource.location == "us-central1"
    assert resource.raw_data == api_data

def test_my_resource_to_dict():
    """Test converting MyResource to dict."""
    resource = MyResource(
        id="my-resource-1",
        name="My Resource",
        project_id="my-project",
        status="RUNNING",
    )

    data = resource.to_dict()

    assert data["id"] == "my-resource-1"
    assert data["name"] == "My Resource"
    assert data["status"] == "RUNNING"
```

---

## Creating a New Service

### Step 1: Create Service Class

**File:** `src/sequel/services/my_service.py`

```python
"""Service for My Resource API."""

from typing import cast

# Import appropriate Google Cloud library
# from google.cloud import myservice_v1
# OR for discovery-based APIs:
from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.my_resource import MyResource
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class MyResourceService(BaseService):
    """Service for interacting with My Resource API."""

    def __init__(self) -> None:
        """Initialize the My Resource service."""
        super().__init__()
        self._client: any | None = None  # type: ignore[valid-type]
        self._cache = get_cache()

    async def _get_client(self) -> any:  # type: ignore[valid-type]
        """Get or create the API client.

        Returns:
            Initialized client
        """
        if self._client is None:
            auth_manager = await self._get_auth_manager()

            # Option 1: Client library
            # self._client = myservice_v1.MyServiceClient(
            #     credentials=auth_manager.credentials
            # )

            # Option 2: Discovery API
            self._client = discovery.build(
                "myservice",
                "v1",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )

        return self._client

    async def list_resources(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> list[MyResource]:
        """List My Resources in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of MyResource instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            NetworkError: If API call times out
        """
        cache_key = f"my_resource:list:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} resources from cache")
                return cast("list[MyResource]", cached)

        async def _list() -> list[MyResource]:
            """Internal function to list resources."""
            client = await self._get_client()

            logger.info(f"Listing My Resources in project {project_id}")

            # Make API call (syntax depends on API type)
            # Option 1: Client library
            # response = client.list_resources(parent=f"projects/{project_id}")
            # resources = [MyResource.from_api_response(r) for r in response]

            # Option 2: Discovery API
            request = client.resources().list(project=project_id)
            response = request.execute()

            items = response.get("items", [])
            resources = [MyResource.from_api_response(item) for item in items]

            logger.info(f"Found {len(resources)} My Resources")
            return resources

        # Execute with retry logic from BaseService
        resources = await self._execute_with_retry(
            operation=_list,
            operation_name=f"list_my_resources(project={project_id})",
        )

        # Cache the results
        if use_cache:
            ttl = get_config().cache_ttl_resources
            await self._cache.set(cache_key, resources, ttl)

        return resources

    async def get_resource(
        self,
        project_id: str,
        resource_id: str,
        use_cache: bool = True,
    ) -> MyResource | None:
        """Get a specific My Resource.

        Args:
            project_id: GCP project ID
            resource_id: Resource identifier
            use_cache: Whether to use cached results

        Returns:
            MyResource instance or None if not found
        """
        cache_key = f"my_resource:get:{project_id}:{resource_id}"

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cast("MyResource", cached)

        async def _get() -> MyResource | None:
            client = await self._get_client()

            request = client.resources().get(
                project=project_id,
                resource=resource_id
            )
            response = request.execute()

            if response:
                return MyResource.from_api_response(response)
            return None

        resource = await self._execute_with_retry(
            operation=_get,
            operation_name=f"get_my_resource({project_id}, {resource_id})",
        )

        if use_cache and resource is not None:
            await self._cache.set(cache_key, resource, get_config().cache_ttl_resources)

        return resource


# Global service instance (singleton pattern)
_my_resource_service: MyResourceService | None = None


async def get_my_resource_service() -> MyResourceService:
    """Get the global My Resource service instance.

    Returns:
        Initialized MyResourceService
    """
    global _my_resource_service
    if _my_resource_service is None:
        _my_resource_service = MyResourceService()
    return _my_resource_service


def reset_my_resource_service() -> None:
    """Reset the global service (mainly for testing)."""
    global _my_resource_service
    _my_resource_service = None
```

**Key Points:**
- Extend `BaseService` for automatic retry, error handling, timeout
- Use singleton pattern with `get_*_service()` and `reset_*_service()`
- Integrate caching with appropriate TTL
- Wrap all API calls in `_execute_with_retry()`
- Return Pydantic models, not raw dicts
- Use type hints everywhere (mypy strict mode)

### Step 2: Add to Services __init__.py

**File:** `src/sequel/services/__init__.py`

```python
from sequel.services.my_service import (
    MyResourceService,
    get_my_resource_service,
    reset_my_resource_service,
)

__all__ = [
    # ... existing exports
    "MyResourceService",
    "get_my_resource_service",
    "reset_my_resource_service",
]
```

### Step 3: Create Service Tests

**File:** `tests/unit/services/test_my_service.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from sequel.models.my_resource import MyResource
from sequel.services.my_service import MyResourceService, reset_my_resource_service

@pytest.fixture
def my_service():
    """Fixture for MyResourceService."""
    reset_my_resource_service()
    return MyResourceService()

@pytest.fixture
def mock_client(mocker):
    """Mock API client."""
    return mocker.MagicMock()

@pytest.mark.asyncio
async def test_list_resources_success(my_service, mock_client, mocker):
    """Test listing resources successfully."""
    # Mock the client
    mocker.patch.object(
        my_service,
        "_get_client",
        return_value=mock_client,
    )

    # Mock the API response
    mock_response = {
        "items": [
            {
                "name": "resource-1",
                "projectId": "my-project",
                "status": "RUNNING",
            }
        ]
    }
    mock_client.resources().list().execute.return_value = mock_response

    # Execute
    resources = await my_service.list_resources("my-project", use_cache=False)

    # Assert
    assert len(resources) == 1
    assert resources[0].name == "resource-1"
    assert resources[0].status == "RUNNING"

@pytest.mark.asyncio
async def test_list_resources_cached(my_service, mocker):
    """Test returning cached resources."""
    # Mock cache to return data
    cached_resources = [
        MyResource(
            id="resource-1",
            name="Resource 1",
            status="RUNNING",
        )
    ]

    cache_mock = mocker.patch.object(my_service._cache, "get")
    cache_mock.return_value = cached_resources

    # Execute
    resources = await my_service.list_resources("my-project")

    # Assert - should return cached data without calling API
    assert resources == cached_resources
    cache_mock.assert_called_once()
```

---

## Extending the Tree View

### Step 1: Add Resource Type Constant

**File:** `src/sequel/widgets/resource_tree.py`

In `ResourceType` class:
```python
class ResourceType:
    """Constants for resource types."""
    # ... existing types
    MY_RESOURCE = "my_resource"
    MY_RESOURCE_ITEM = "my_resource_item"  # For nested items
```

### Step 2: Add Category Node

In `_add_resource_type_nodes()` method:
```python
def _add_resource_type_nodes(self, project_node: TreeNode[ResourceTreeNode], project_id: str) -> None:
    """Add resource type category nodes to a project."""
    # ... existing categories

    # Add My Resource category
    my_resource_data = ResourceTreeNode(
        resource_type=ResourceType.MY_RESOURCE,
        resource_id=f"{project_id}:my_resource",
        project_id=project_id,
    )
    project_node.add("🎯 My Resources", data=my_resource_data, allow_expand=True)
```

### Step 3: Handle Node Expansion

Add case to `on_tree_node_expanded()` method:

```python
async def on_tree_node_expanded(self, event: Tree.NodeExpanded[ResourceTreeNode]) -> None:
    """Handle tree node expansion (lazy loading)."""
    node = event.node
    if not node.data or node.data.loaded:
        return

    try:
        if node.data.resource_type == ResourceType.MY_RESOURCE:
            await self._load_my_resources(node, node.data.project_id)

        # Mark as loaded
        node.data.loaded = True

    except Exception as e:
        logger.error(f"Failed to load {node.data.resource_type}: {e}")
        # Show error in tree
        node.add(f"❌ Error: {e}", allow_expand=False)

async def _load_my_resources(
    self,
    parent_node: TreeNode[ResourceTreeNode],
    project_id: str | None,
) -> None:
    """Load My Resources for a project.

    Args:
        parent_node: Parent tree node
        project_id: Project ID
    """
    if not project_id:
        return

    # Remove placeholder children
    parent_node.remove_children()

    try:
        my_service = await get_my_resource_service()
        resources = await my_service.list_resources(project_id)

        if not resources:
            parent_node.add("(No resources)", allow_expand=False)
            return

        # Add resource nodes
        for resource in resources:
            node_data = ResourceTreeNode(
                resource_type=ResourceType.MY_RESOURCE_ITEM,
                resource_id=resource.id,
                resource_data=resource,  # For detail pane
                project_id=project_id,
            )
            parent_node.add(
                f"🎯 {resource.name}",
                data=node_data,
                allow_expand=False,  # Or True if has children
            )

        logger.info(f"Loaded {len(resources)} My Resources for {project_id}")

    except Exception as e:
        logger.error(f"Failed to load My Resources: {e}")
        parent_node.add(f"❌ Error loading: {e}", allow_expand=False)
```

**Key Points:**
- Import service at top of file
- Add resource type constants
- Add category node in `_add_resource_type_nodes()`
- Handle expansion in `on_tree_node_expanded()`
- Create helper method (`_load_my_resources()`)
- Handle errors gracefully (show in tree)
- Mark node as loaded after successful load
- Store `resource_data` for detail pane

---

## Adding a New Widget

### Step 1: Create Widget File

**File:** `src/sequel/widgets/my_widget.py`

```python
"""My Widget for displaying custom information."""

from typing import ClassVar

from textual.binding import Binding
from textual.widgets import Static

from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class MyWidget(Static):
    """Widget for displaying custom information.

    Key bindings:
    - Enter: Perform action
    """

    BINDINGS: ClassVar = [
        Binding("enter", "perform_action", "Perform Action", show=False),
    ]

    CSS: ClassVar[str] = """
    MyWidget {
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    MyWidget:focus {
        border: solid $accent;
    }
    """

    def __init__(self, *args: any, **kwargs: any) -> None:  # type: ignore[valid-type]
        """Initialize the widget."""
        super().__init__(*args, **kwargs)
        self._data: str = ""

    def update_data(self, data: str) -> None:
        """Update widget data.

        Args:
            data: Data to display
        """
        self._data = data
        self.update(f"Data: {data}")
        logger.debug(f"Widget updated with: {data}")

    async def action_perform_action(self) -> None:
        """Perform widget action (Enter key)."""
        logger.info(f"Performing action with data: {self._data}")
        # Emit custom event or call parent method
        self.post_message(self.ActionPerformed(self._data))

    class ActionPerformed(Static.Changed):
        """Event emitted when action is performed."""

        def __init__(self, data: str) -> None:
            """Initialize event.

            Args:
                data: Data associated with action
            """
            super().__init__(data)
            self.data = data
```

**Key Points:**
- Extend appropriate Textual widget (Static, Container, etc.)
- Define CSS in widget class
- Use reactive attributes for auto-updating state
- Emit custom events for parent communication
- Add type hints and docstrings

### Step 2: Add to Screen

**File:** `src/sequel/screens/main.py`

```python
from sequel.widgets.my_widget import MyWidget

class MainScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        # ... existing widgets
        self.my_widget = MyWidget()
        yield self.my_widget

    async def on_my_widget_action_performed(self, event: MyWidget.ActionPerformed) -> None:
        """Handle custom event from MyWidget."""
        logger.info(f"Received action with data: {event.data}")
        # Update other widgets or perform actions
```

### Step 3: Create Widget Tests

**File:** `tests/unit/widgets/test_my_widget.py`

```python
import pytest
from textual.app import App, ComposeResult

from sequel.widgets.my_widget import MyWidget

class TestApp(App[None]):
    """Test app for MyWidget."""

    def compose(self) -> ComposeResult:
        yield MyWidget()

@pytest.mark.asyncio
async def test_my_widget_update_data():
    """Test updating widget data."""
    async with TestApp().run_test() as pilot:
        widget = pilot.app.query_one(MyWidget)

        widget.update_data("test data")

        assert widget._data == "test data"
        assert "test data" in str(widget.renderable)

@pytest.mark.asyncio
async def test_my_widget_action():
    """Test widget action."""
    async with TestApp().run_test() as pilot:
        widget = pilot.app.query_one(MyWidget)
        widget.update_data("action test")

        # Simulate pressing Enter
        await pilot.press("enter")

        # Assert action was performed (check logs or state)
```

---

## Adding Configuration Options

### Step 1: Add to Config Class

**File:** `src/sequel/config.py`

```python
from pydantic import Field

class Config(BaseModel):
    # ... existing fields

    # My new configuration option
    my_feature_enabled: bool = Field(
        default=True,
        description="Enable My Feature",
    )

    my_feature_setting: int = Field(
        default=100,
        description="My Feature setting value",
    )

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            # ... existing env vars
            my_feature_enabled=os.getenv("SEQUEL_MY_FEATURE_ENABLED", "true").lower() == "true",
            my_feature_setting=int(os.getenv("SEQUEL_MY_FEATURE_SETTING", "100")),
        )
```

### Step 2: Add to Config File Schema

**File:** `src/sequel/config_file.py`

Update `load_config_file()` to handle new section:

```python
def load_config_file() -> dict[str, any]:  # type: ignore[valid-type]
    """Load configuration from JSON file."""
    # ... existing code

    # Add My Feature section
    if "my_feature" in config_data:
        my_feature = config_data["my_feature"]
        if "enabled" in my_feature:
            config["my_feature_enabled"] = my_feature["enabled"]
        if "setting" in my_feature:
            config["my_feature_setting"] = my_feature["setting"]

    return config
```

### Step 3: Update Documentation

**File:** `docs/user-guide/configuration.md`

Add new options to configuration table and examples.

### Step 4: Use in Code

```python
from sequel.config import get_config

config = get_config()

if config.my_feature_enabled:
    # Use feature
    value = config.my_feature_setting
```

---

## Error Handling Patterns

### Service Layer

```python
# Let BaseService handle retries and categorization
resources = await self._execute_with_retry(
    operation=_api_call,
    operation_name="descriptive_name",
)
```

### Widget Layer

```python
try:
    resources = await service.list_resources(project_id)
    # Update UI with resources
except AuthError as e:
    await self.app.show_error("Authentication Error", str(e))
except PermissionError as e:
    await self.app.show_error("Permission Denied", str(e))
except QuotaExceededError as e:
    # Usually auto-handled by retry, but can show here
    await self.app.show_error("Quota Exceeded", str(e))
except ServiceNotEnabledError as e:
    await self.app.show_error("API Not Enabled", str(e))
except NetworkError as e:
    await self.app.show_error("Network Error", str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    await self.app.show_error("Error", f"An unexpected error occurred: {e}")
```

### Tree Loading

```python
try:
    resources = await service.list_resources(project_id)
    if not resources:
        node.add("(No resources)", allow_expand=False)
    else:
        for resource in resources:
            # Add nodes
except Exception as e:
    logger.error(f"Failed to load resources: {e}")
    node.add(f"❌ Error loading: {e}", allow_expand=False)
```

---

## Testing Guidelines

### Unit Tests

**Models:**
- Test `from_api_response()` with various API data shapes
- Test field validation
- Test `to_dict()` conversion

**Services:**
- Mock API client
- Test successful API calls
- Test caching behavior
- Test error handling (each error type)
- Test retry logic

**Widgets:**
- Use `App.run_test()` context
- Test user interactions (key presses, clicks)
- Test state updates
- Test event emission

### Integration Tests

**File:** `tests/integration/test_my_resource_workflow.py`

```python
@pytest.mark.asyncio
async def test_full_my_resource_workflow(mocker):
    """Test complete workflow from service to UI."""
    # Mock GCP API
    mock_api_response = {...}
    # ... setup mocks

    # Test service
    service = await get_my_resource_service()
    resources = await service.list_resources("project-id")

    # Test model
    assert len(resources) > 0
    assert isinstance(resources[0], MyResource)

    # Test UI (if applicable)
    # ... test tree loading, detail pane, etc.
```

### Coverage Requirements

- Minimum: 60% (enforced by CI)
- Target: 95%+
- Critical paths: 100% (error handling, security)

---

## Common Patterns

### Async/Await

All service methods and most widget methods should be async:

```python
async def my_method(self):
    result = await some_async_operation()
    return result
```

### Type Hints

Use strict type hints (mypy --strict):

```python
from typing import Any

def my_function(param: str, optional: int | None = None) -> list[MyModel]:
    """Function with complete type hints."""
    result: list[MyModel] = []
    # ... implementation
    return result
```

### Logging

Use structured logging with credential scrubbing:

```python
from sequel.utils.logging import get_logger

logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message with exception", exc_info=True)
```

### Singleton Pattern

For services and global state:

```python
_instance: MyClass | None = None

def get_instance() -> MyClass:
    global _instance
    if _instance is None:
        _instance = MyClass()
    return _instance

def reset_instance() -> None:
    global _instance
    _instance = None
```

---

## Additional Resources

- [Textual Documentation](https://textual.textualize.io/)
- [Google Cloud Python Client Libraries](https://cloud.google.com/python/docs/reference)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
