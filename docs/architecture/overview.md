# Architecture Overview

## High-Level Architecture

Sequel follows a layered architecture pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    Textual App Layer                    │
│                   (app.py, screens/)                    │
├─────────────────────────────────────────────────────────┤
│                     Widget Layer                        │
│         (resource_tree, detail_pane, status_bar)        │
├─────────────────────────────────────────────────────────┤
│                     Service Layer                       │
│        (projects, cloudsql, compute, gke, etc.)         │
├─────────────────────────────────────────────────────────┤
│                      Cache Layer                        │
│                  (memory.py - TTL cache)                │
├─────────────────────────────────────────────────────────┤
│                      Model Layer                        │
│          (Pydantic models for type-safe data)           │
├─────────────────────────────────────────────────────────┤
│                 Google Cloud APIs                       │
│    (Resource Manager, Compute, GKE, Secrets, etc.)      │
└─────────────────────────────────────────────────────────┘
```

## Technology Stack

### UI Framework
- **Textual 0.47.0+**: Terminal User Interface framework
- **tree-sitter**: Syntax highlighting for JSON display
  - tree-sitter-languages 1.10.0+
  - tree-sitter-json 0.24.0+

### Google Cloud Integration
- **google-auth 2.25.0+**: Authentication (Application Default Credentials)
- **google-auth-oauthlib 1.2.0+**: OAuth2 support
- **google-api-python-client 2.110.0+**: Discovery-based API client
- **google-cloud-resource-manager 1.12.0+**: Project management
- **google-cloud-container 2.36.0+**: GKE (Kubernetes Engine)
- **google-cloud-secret-manager 2.18.0+**: Secret Manager

### Data Validation
- **Pydantic 2.5.0+**: Data models with type validation

### Utilities
- **aiohttp 3.9.0+**: Async HTTP client
- **pyperclip 1.8.0+**: Clipboard support for VIM yanking

## Component Overview

### 1. Application Layer (`app.py`, `screens/`)

**SequelApp** (main application):
- Entry point for the Textual TUI
- Manages global keyboard bindings (q, r, Ctrl+P, ?)
- Handles authentication initialization
- Manages theme persistence via config file
- Provides command palette via ThemeProvider

**MainScreen** (`screens/main.py`):
- Primary screen layout (tree + detail pane)
- Manages resource tree and detail pane widgets
- Coordinates refresh operations
- Handles error display

### 2. Widget Layer (`widgets/`)

**ResourceTree** (`resource_tree.py`):
- Hierarchical tree view of GCP resources
- VIM-style navigation (j/k/h/l/g/G)
- Lazy loading of child resources
- Displays resource counts per category
- Icons for different resource types

**DetailPane** (`detail_pane.py`):
- JSON display with syntax highlighting (Monokai theme)
- VIM navigation (j/k/h/l/g/G/0/$)
- VIM yanking (y for selection, Y for line)
- Mouse selection support
- Read-only TextArea widget

**StatusBar** (`status_bar.py`):
- Displays current operation status
- Shows cache statistics (hit rate, API calls)
- Shows last refresh time
- Keyboard shortcut hints

**ErrorModal** (`error_modal.py`):
- Displays error messages and help dialogs
- Dismissible with Esc key

**LoadingIndicator** (`loading_indicator.py`):
- Progress indicator for long operations

### 3. Service Layer (`services/`)

**BaseService** (`base.py`):
- Base class for all GCP service wrappers
- Automatic retry with exponential backoff (default: 3 retries)
- Timeout handling (default: 30 seconds)
- Error categorization:
  - `AuthError`: Authentication failures
  - `PermissionError`: IAM permission denied
  - `QuotaExceededError`: API quota exceeded (auto-waits 60s)
  - `NetworkError`: Timeouts and connectivity issues
  - `ServiceNotEnabledError`: API not enabled in project
  - `ResourceNotFoundError`: Resource doesn't exist
- Automatic credential refresh on expiry

**Specialized Services**:
- **AuthManager** (`auth.py`): Manages Application Default Credentials
- **ProjectService** (`projects.py`): Lists and filters GCP projects
- **CloudSQLService** (`cloudsql.py`): Cloud SQL instances
- **ComputeService** (`compute.py`): Instance groups and VMs
- **GKEService** (`gke.py`): Kubernetes clusters, node pools, nodes
- **SecretsService** (`secrets.py`): Secret Manager (metadata only)
- **IAMService** (`iam.py`): Service accounts
- **CloudDNSService** (`clouddns.py`): DNS zones and records

### 4. Cache Layer (`cache/`)

**MemoryCache** (`memory.py`):
- In-memory TTL-based cache
- Default TTLs:
  - Projects: 600 seconds (10 minutes)
  - Resources: 300 seconds (5 minutes)
- Cache invalidation on explicit refresh
- Cache statistics tracking (hits, misses)

### 5. Model Layer (`models/`)

**BaseModel** (`base.py`):
- Base Pydantic model for all resources
- Standard fields: id, name, project_id, created_at, labels
- Stores raw API response in `raw_data` field
- Type-safe validation

**Resource Models**:
- **Project** (`project.py`): GCP projects
- **CloudSQLInstance** (`cloudsql.py`): Database instances
- **ComputeInstance** (`compute.py`): VM instances
- **InstanceGroup** (`compute.py`): Instance groups
- **GKECluster** (`gke.py`): Kubernetes clusters
- **NodePool** (`gke.py`): GKE node pools
- **Secret** (`secrets.py`): Secret Manager entries
- **ServiceAccount** (`iam.py`): IAM service accounts
- **ManagedZone** (`clouddns.py`): DNS zones
- **DNSRecord** (`clouddns.py`): DNS records

### 6. Utilities (`utils/`)

**Logging** (`logging.py`):
- Structured logging with credential scrubbing
- Automatically removes: tokens, API keys, Bearer headers, private keys, passwords
- Supports DEBUG, INFO, WARNING, ERROR levels
- Optional file logging

### 7. Configuration (`config.py`, `config_file.py`)

**Config** (`config.py`):
- Environment variable parsing
- Default values for all settings
- API timeouts, retries, backoff configuration
- Cache TTL settings
- Logging configuration
- Project filtering via regex

**ConfigFile** (`config_file.py`):
- JSON configuration file at `~/.config/sequel/config.json`
- Persists UI preferences (theme)
- Persists project filters
- Precedence: Environment variables > Config file > Defaults

## Data Flow

### Application Startup

1. **main()** → `cli.py` entry point
2. **SequelApp** initialization
   - Load config from file and environment
   - Set theme from config
3. **on_mount()**
   - Initialize AuthManager (load ADC credentials)
   - Push MainScreen
4. **MainScreen.on_mount()**
   - Initialize services (ProjectService, etc.)
   - Load projects from cache or API
   - Build initial tree structure

### Resource Loading (Lazy)

1. User expands tree node
2. **ResourceTree.on_tree_node_expanded()**
3. Check cache for resource data
4. If cache miss:
   - Call appropriate service method (e.g., `gke_service.list_clusters(project_id)`)
   - Service calls `_execute_with_retry()`
   - Make API request with timeout
   - Parse API response into Pydantic models
   - Store in cache with TTL
5. Build child tree nodes from models
6. Update tree display

### Detail Pane Update

1. User selects tree node
2. **ResourceTree.on_tree_node_highlighted()**
3. Post message to MainScreen
4. **MainScreen** updates **DetailPane**
5. **DetailPane** displays `raw_data` field as formatted JSON with syntax highlighting

### Refresh Operation

1. User presses 'r'
2. **SequelApp.action_refresh()**
3. **MainScreen.refresh_tree()**
4. Clear cache for current view
5. Reload data from API
6. Rebuild tree nodes
7. Update display

### Error Handling Flow

1. Service operation fails
2. **BaseService._execute_with_retry()** catches exception
3. Categorize error type:
   - **Quota exceeded**: Extract retry-after time, wait, retry
   - **Unauthenticated**: Attempt credential refresh, retry once
   - **Permission denied**: Raise immediately (no retry)
   - **Not found**: Raise immediately (no retry)
   - **Transient errors**: Retry with exponential backoff
4. If all retries exhausted, raise typed exception
5. Error propagates to widget layer
6. **MainScreen** or widget displays **ErrorModal**

## Key Design Decisions

### 1. Lazy Loading
Resources are loaded only when tree nodes are expanded. This reduces:
- Initial API calls
- Memory usage
- Startup time

### 2. TTL Caching
In-memory cache with separate TTLs for projects and resources minimizes redundant API calls while ensuring data freshness.

### 3. Async-First
All API calls are async using `asyncio`. Services use `_execute_with_retry()` wrapper for consistent error handling.

### 4. Type Safety
Pydantic models provide runtime validation and static type checking via mypy, reducing bugs.

### 5. Error Recovery
Automatic retry with exponential backoff, credential refresh, and quota waiting provides resilient operation.

### 6. Credential Scrubbing
All logging automatically removes credentials and secrets to prevent accidental exposure.

### 7. VIM Bindings
Navigation uses VIM bindings (j/k/h/l/g/G) for power users, with arrow key fallbacks.

## Testing Architecture

Tests are organized by type:

- **Unit Tests** (`tests/unit/`): Test individual components in isolation with mocking
- **Fixtures** (`tests/conftest.py`): Shared test fixtures for services, models, and mock data

Coverage target: 95%+ overall, 100% for critical security paths (credential scrubbing).

## Security Considerations

1. **Authentication**: Uses Application Default Credentials (ADC) with read-only scope
2. **Credential Scrubbing**: Automatic removal of sensitive data from logs
3. **Secret Manager**: Only retrieves metadata, never secret values
4. **No Credential Storage**: Relies on gcloud CLI or service account keys managed externally
5. **Input Validation**: Pydantic models validate all API responses

## Performance Characteristics

- **Startup Time**: < 2 seconds (with cached credentials)
- **Project Loading**: ~500ms for 10 projects (parallel loading)
- **Tree Expansion**: < 100ms (cached), < 1s (API call)
- **Memory Usage**: ~50-100MB base + ~5MB per 100 resources cached
- **Cache Hit Rate**: Target > 70% for repeated operations
