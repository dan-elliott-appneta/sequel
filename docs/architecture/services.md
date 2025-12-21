# Service Layer Architecture

The service layer provides async API wrappers for Google Cloud Platform services with built-in error handling, retries, and caching.

## Architecture Pattern

All services follow a consistent pattern:

```
┌──────────────────────────────────────┐
│         Service Class                │
│  (e.g., ProjectService)              │
├──────────────────────────────────────┤
│  • Extends BaseService               │
│  • Manages API client                │
│  • Implements caching                │
│  • Returns Pydantic models           │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│         BaseService                  │
│  (_execute_with_retry)               │
├──────────────────────────────────────┤
│  • Retry logic (3 attempts)          │
│  • Exponential backoff               │
│  • Timeout handling (30s)            │
│  • Error categorization              │
│  • Credential refresh                │
│  • Quota wait/retry                  │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│      Google Cloud API                │
│  (Resource Manager, Compute, etc.)   │
└──────────────────────────────────────┘
```

## Base Service

### BaseService Class

Located in `src/sequel/services/base.py`, this class provides common functionality for all GCP service wrappers.

**Key Features:**

1. **Automatic Retry with Exponential Backoff**
   - Default: 3 retries (configurable via `SEQUEL_API_MAX_RETRIES`)
   - Initial delay: 1 second (configurable via `SEQUEL_API_RETRY_DELAY`)
   - Backoff multiplier: 2.0 (configurable via `SEQUEL_API_RETRY_BACKOFF`)
   - Example delays: 1s, 2s, 4s

2. **Timeout Handling**
   - Default timeout: 30 seconds (configurable via `SEQUEL_API_TIMEOUT`)
   - Wraps all API calls with `asyncio.wait_for()`
   - Timeout errors categorized as `NetworkError`

3. **Error Categorization**

   Converts Google API exceptions to domain-specific errors:

   | Google API Exception | Sequel Exception | Retry? | Description |
   |---------------------|------------------|--------|-------------|
   | `Unauthenticated` | `AuthError` | Once (after refresh) | Credential refresh attempted |
   | `PermissionDenied`, `Forbidden` | `PermissionError` | No | Extracts required permission |
   | `ResourceExhausted` | `QuotaExceededError` | Yes (with wait) | Extracts retry-after time |
   | `NotFound` | `ResourceNotFoundError` | No | Resource doesn't exist |
   | `ServiceUnavailable`, `DeadlineExceeded` | `NetworkError` | Yes | Transient network issues |
   | `TimeoutError` | `NetworkError` | Yes | Operation timeout |
   | "API not enabled" | `ServiceNotEnabledError` | No | Extracts API name |
   | Other `GoogleAPIError` | `Exception` | No | Unexpected errors |

4. **Credential Refresh**

   When `Unauthenticated` error occurs:
   - Attempts to refresh credentials on first attempt
   - Uses `google.auth.transport.requests.Request()`
   - Retries operation with refreshed credentials
   - If refresh fails, raises `AuthError` with instructions

5. **Quota Handling**

   When `ResourceExhausted` error occurs:
   - Extracts retry-after time from error message (regex patterns)
   - Falls back to `SEQUEL_GCLOUD_QUOTA_WAIT_TIME` (default: 60 seconds)
   - Logs wait time and countdown
   - Automatically waits and retries
   - Raises `QuotaExceededError` if all retries exhausted

### Error Extraction Methods

**`_extract_retry_after(error)`**
- Parses error messages for retry timing: `"Retry after 60 seconds"`, `"rateLimitExceeded...60"`
- Returns integer seconds or None

**`_extract_permission_error(error)`**
- Extracts permission name: `"Permission 'compute.instances.list' denied"`
- Returns helpful message: `"Missing permission: compute.instances.list. Grant this permission in IAM..."`

**`_extract_api_name(error)`**
- Extracts API name from error messages
- Patterns: `compute.googleapis.com`, `API [name]`
- Returns API name for enable instructions

## Authentication

### AuthManager Class

Located in `src/sequel/services/auth.py`, manages Application Default Credentials (ADC).

**Credential Sources (in order):**

1. **GOOGLE_APPLICATION_CREDENTIALS** environment variable
   - Points to service account JSON key file
   - Checked first by `google.auth.default()`

2. **gcloud CLI configuration**
   - User credentials from `gcloud auth application-default login`
   - Stored at `~/.config/gcloud/application_default_credentials.json`

3. **GCE/GKE metadata server**
   - Automatic when running on Google Cloud infrastructure
   - Uses instance's attached service account

**Required Scope:**
- `https://www.googleapis.com/auth/cloud-platform.read-only`
- Allows viewing (but not modifying) all GCP resources

**Initialization Flow:**

```python
auth_manager = AuthManager()
await auth_manager.initialize()

# Loads credentials:
credentials, project_id = google.auth.default(scopes=[...])

# Validates and refreshes if needed:
if credentials.expired:
    credentials.refresh(Request())
```

**Error Handling:**

- `DefaultCredentialsError`: No credentials found
  - Raises `AuthError` with setup instructions
- `RefreshError`: Credentials expired and can't refresh
  - Raises `AuthError` asking user to re-authenticate with gcloud

**Global Singleton:**

```python
# Services use this to get the shared auth manager:
auth_manager = await get_auth_manager()
credentials = auth_manager.credentials
```

## Cache Integration

### MemoryCache

Located in `src/sequel/cache/memory.py`, provides TTL-based in-memory caching.

**Features:**

1. **TTL-Based Expiration**
   - Each entry has configurable Time-To-Live
   - Default TTLs:
     - Projects: 600 seconds (10 minutes)
     - Resources: 300 seconds (5 minutes)
   - Expired entries automatically removed on access

2. **LRU Eviction**
   - Maximum cache size: 100 MB (configurable)
   - Evicts least-recently-used entries when full
   - Uses `OrderedDict` for efficient LRU tracking

3. **Background Cleanup**
   - Optional periodic cleanup task (default: 5 minutes)
   - Removes expired entries in background
   - Prevents memory leaks from unused entries

4. **Statistics Tracking**
   - Hits: Cache hits
   - Misses: Cache misses
   - Evictions: LRU evictions due to size limit
   - Expirations: Entries removed due to TTL

5. **Thread-Safe**
   - Uses `asyncio.Lock` for concurrent access
   - Safe for multiple async tasks

**Usage Pattern in Services:**

```python
class ProjectService(BaseService):
    def __init__(self):
        super().__init__()
        self._cache = get_cache()

    async def list_projects(self, use_cache: bool = True):
        cache_key = "projects:all"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Execute API call
        projects = await self._execute_with_retry(...)

        # Store in cache
        if use_cache:
            ttl = get_config().cache_ttl_projects
            await self._cache.set(cache_key, projects, ttl)

        return projects
```

## Specialized Services

### ProjectService

**File:** `src/sequel/services/projects.py`

**API:** Cloud Resource Manager API (resourcemanager_v3)

**Client:** `google.cloud.resourcemanager_v3.ProjectsClient`

**Methods:**

- `list_projects(parent, use_cache)` → `list[Project]`
  - Lists all accessible projects
  - Uses `SearchProjectsRequest` when no parent
  - Uses `ListProjectsRequest` when parent specified
  - Pagination: 100 projects per page
  - Cache key: `projects:{parent or 'all'}`

- `get_project(project_id, use_cache)` → `Project | None`
  - Gets a single project by ID
  - Returns None if not found (instead of raising)
  - Cache key: `project:{project_id}`

**Protobuf Conversion:**

```python
def _proto_to_dict(self, proto_message):
    # Converts protobuf message to dict for Pydantic model
    result = {
        "name": proto_message.name,
        "projectId": proto_message.project_id,
        "displayName": proto_message.display_name,
        "lifecycleState": proto_message.state.name,
        "createTime": proto_message.create_time.isoformat(),
        "labels": dict(proto_message.labels),
        "parent": proto_message.parent
    }
    return result
```

### CloudSQLService

**File:** `src/sequel/services/cloudsql.py`

**API:** Cloud SQL Admin API (sqladmin_v1)

**Client:** Discovery client (`googleapiclient.discovery.build`)

**Methods:**

- `list_instances(project_id, use_cache)` → `list[CloudSQLInstance]`
  - Lists database instances in a project
  - Cache key: `cloudsql:instances:{project_id}`

### ComputeService

**File:** `src/sequel/services/compute.py`

**API:** Compute Engine API (compute_v1)

**Client:** Discovery client

**Methods:**

- `list_instance_groups(project_id, use_cache)` → `list[InstanceGroup]`
  - Lists instance groups across all zones
  - Aggregates managed and unmanaged groups
  - Cache key: `compute:instance_groups:{project_id}`

- `list_instances_in_group(project_id, zone, group_name, use_cache)` → `list[ComputeInstance]`
  - Lists VMs in a specific instance group
  - Cache key: `compute:instances:{project_id}:{zone}:{group_name}`

- `get_instance_details(project_id, zone, instance_name, use_cache)` → `dict | None`
  - Gets detailed info for a single VM
  - Cache key: `compute:instance_details:{project_id}:{zone}:{instance_name}`

### GKEService

**File:** `src/sequel/services/gke.py`

**API:** Kubernetes Engine API (container_v1)

**Client:** `google.cloud.container_v1.ClusterManagerClient`

**Methods:**

- `list_clusters(project_id, use_cache)` → `list[GKECluster]`
  - Lists GKE clusters across all locations
  - Cache key: `gke:clusters:{project_id}`

- `list_node_pools(project_id, location, cluster_name, use_cache)` → `list[NodePool]`
  - Lists node pools in a cluster
  - Cache key: `gke:node_pools:{project_id}:{location}:{cluster_name}`

- `list_nodes_in_pool(project_id, location, cluster_name, node_pool_name, use_cache)` → `list[dict]`
  - Lists nodes in a specific node pool
  - Cache key: `gke:nodes:{project_id}:{location}:{cluster_name}:{node_pool_name}`

### SecretsService

**File:** `src/sequel/services/secrets.py`

**API:** Secret Manager API (secretmanager_v1)

**Client:** `google.cloud.secretmanager_v1.SecretManagerServiceClient`

**Security Note:** Only retrieves secret METADATA. Never accesses secret values.

**Methods:**

- `list_secrets(project_id, use_cache)` → `list[Secret]`
  - Lists secret metadata only
  - Cache key: `secrets:list:{project_id}`

### IAMService

**File:** `src/sequel/services/iam.py`

**API:** IAM API (iam_v1)

**Client:** Discovery client

**Methods:**

- `list_service_accounts(project_id, use_cache)` → `list[ServiceAccount]`
  - Lists service accounts in a project
  - Cache key: `iam:service_accounts:{project_id}`

### CloudDNSService

**File:** `src/sequel/services/clouddns.py`

**API:** Cloud DNS API (dns_v1)

**Client:** Discovery client

**Methods:**

- `list_managed_zones(project_id, use_cache)` → `list[ManagedZone]`
  - Lists DNS managed zones
  - Cache key: `clouddns:zones:{project_id}`

- `list_dns_records(project_id, zone_name, use_cache)` → `list[DNSRecord]`
  - Lists DNS records in a zone
  - Cache key: `clouddns:records:{project_id}:{zone_name}`

## Global Service Singletons

All services use the singleton pattern to avoid recreating API clients:

```python
# Global instance
_project_service: ProjectService | None = None

async def get_project_service() -> ProjectService:
    """Get the global project service instance."""
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service

def reset_project_service() -> None:
    """Reset the global service (mainly for testing)."""
    global _project_service
    _project_service = None
```

**Benefits:**
- API client reused across calls (connection pooling)
- Credentials loaded once
- Consistent state across application

**Testing:**
- `reset_*()` functions clear singletons for test isolation

## Error Handling Best Practices

### Service Implementation

```python
async def list_resources(self, project_id: str) -> list[Resource]:
    async def _list():
        client = await self._get_client()
        # Make API call
        response = client.list(project=project_id)
        # Convert to models
        return [Resource.from_api_response(r) for r in response]

    # Let BaseService handle retries and errors
    return await self._execute_with_retry(
        operation=_list,
        operation_name=f"list_resources(project={project_id})"
    )
```

### Widget Layer

```python
try:
    projects = await project_service.list_projects()
except AuthError as e:
    # Show authentication error modal with instructions
    await self.show_error("Authentication Error", str(e))
except PermissionError as e:
    # Show permission error with required permission
    await self.show_error("Permission Denied", str(e))
except QuotaExceededError as e:
    # Show quota error (usually auto-handled by retry logic)
    await self.show_error("Quota Exceeded", str(e))
except ServiceNotEnabledError as e:
    # Show API not enabled error with enable link
    await self.show_error("API Not Enabled", str(e))
except NetworkError as e:
    # Show network/timeout error
    await self.show_error("Network Error", str(e))
```

## Configuration

Services use `Config` class (from `src/sequel/config.py`) for runtime settings:

```python
config = get_config()

# API settings
config.api_timeout  # Default: 30 seconds
config.api_max_retries  # Default: 3
config.api_retry_delay  # Default: 1.0 seconds
config.api_retry_backoff  # Default: 2.0

# Cache settings
config.cache_enabled  # Default: True
config.cache_ttl_projects  # Default: 600 seconds
config.cache_ttl_resources  # Default: 300 seconds

# GCloud settings
config.gcloud_project_id  # Default: None (auto-detect)
config.gcloud_quota_wait_time  # Default: 60 seconds
```

All settings configurable via environment variables (e.g., `SEQUEL_API_TIMEOUT`).

## Adding a New Service

To add a new GCP service:

1. **Create service file** in `src/sequel/services/`
2. **Extend BaseService**
3. **Create API client** in `_get_client()` method
4. **Implement methods** using `_execute_with_retry()` wrapper
5. **Add caching** with appropriate TTL
6. **Create Pydantic models** in `src/sequel/models/`
7. **Add tests** in `tests/unit/services/`
8. **Create singleton** with `get_*_service()` and `reset_*_service()`

**Example:**

```python
from sequel.services.base import BaseService
from sequel.cache.memory import get_cache
from sequel.models.my_resource import MyResource

class MyService(BaseService):
    def __init__(self):
        super().__init__()
        self._client = None
        self._cache = get_cache()

    async def _get_client(self):
        if self._client is None:
            auth_manager = await self._get_auth_manager()
            self._client = MyAPIClient(credentials=auth_manager.credentials)
        return self._client

    async def list_resources(self, project_id: str, use_cache: bool = True) -> list[MyResource]:
        cache_key = f"my_service:resources:{project_id}"

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached

        async def _list():
            client = await self._get_client()
            response = client.list(project=project_id)
            return [MyResource.from_api_response(r) for r in response]

        resources = await self._execute_with_retry(
            operation=_list,
            operation_name=f"list_resources(project={project_id})"
        )

        if use_cache:
            await self._cache.set(cache_key, resources, self.config.cache_ttl_resources)

        return resources

# Singleton
_my_service = None

async def get_my_service() -> MyService:
    global _my_service
    if _my_service is None:
        _my_service = MyService()
    return _my_service
```
