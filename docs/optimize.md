# Memory Leak and Blocking Call Review - Implementation Plan

## Executive Summary

Comprehensive code review identified **3 critical blocking calls** and **2 moderate memory leak concerns** in the Sequel codebase. The good news: overall async patterns are excellent, with proper use of `asyncio.to_thread()` throughout most of the codebase. The fixes are isolated and straightforward.

## Critical Issues Found

### 1. CloudSQL Service - Blocking execute() Call
**File**: `src/sequel/services/cloudsql.py`
**Line**: 150
**Severity**: CRITICAL
**Impact**: Event loop blocks during instance retrieval

**Current Code**:
```python
# Line 150 - BLOCKING
response = request.execute()
```

**Fix Required**:
```python
response = await asyncio.to_thread(request.execute)
```

**Context**: The `get_instance()` method is missing async wrapping. All other CloudSQL methods (line 81 in `list_instances()`) correctly use `asyncio.to_thread()`.

---

### 2. IAM Service - Blocking execute() Call
**File**: `src/sequel/services/iam.py`
**Line**: 169
**Severity**: CRITICAL
**Impact**: Event loop blocks during service account retrieval

**Current Code**:
```python
# Line 169 - BLOCKING
response = request.execute()
```

**Fix Required**:
```python
response = await asyncio.to_thread(request.execute)
```

**Context**: The `get_service_account()` method is missing async wrapping. The `list_service_accounts()` method (line 101) correctly uses `asyncio.to_thread()`.

---

### 3. Base Service - Blocking Credential Refresh
**File**: `src/sequel/services/base.py`
**Lines**: 182-183
**Severity**: HIGH
**Impact**: Event loop blocks during credential refresh operations

**Current Code**:
```python
# Lines 182-183 - BLOCKING
request = google.auth.transport.requests.Request()
auth_manager.credentials.refresh(request)
```

**Fix Required**:
```python
# Define helper function
def _refresh_credentials(creds):
    import google.auth.transport.requests
    request = google.auth.transport.requests.Request()
    creds.refresh(request)

# In the method (replace lines 182-183):
await asyncio.to_thread(_refresh_credentials, auth_manager.credentials)
```

**Context**: When credentials expire during API operations, the refresh is synchronous and blocks the event loop.

---

### 4. Inline `re` Module Imports
**File**: `src/sequel/services/base.py`
**Lines**: 256, 283, 313
**Severity**: MEDIUM
**Impact**: Code quality issue, minor inefficiency

**Current Code**:
```python
# Line 256, 283, 313 - Repeated inline imports
import re
match = re.search(...)
```

**Fix Required**:
Move `import re` to module top-level (after line 10 with other imports).

**Context**: The `re` module is imported inline in three error handling helper methods: `_extract_retry_after()`, `_extract_permission_error()`, and `_extract_api_name()`.

---

## Moderate Concerns

### 5. Service Client Cleanup Missing
**Files**: All service files
**Severity**: MEDIUM
**Impact**: Service clients not gracefully closed on shutdown

**Issue**: All services follow singleton pattern with global instances:
```python
_clouddns_service: CloudDNSService | None = None

async def get_clouddns_service() -> CloudDNSService:
    global _clouddns_service
    if _clouddns_service is None:
        _clouddns_service = CloudDNSService()
    return _clouddns_service
```

Each service creates API clients via `discovery.build()` or Google Cloud client libraries. These clients maintain HTTP connections but are never explicitly closed.

**Affected Services**:
- `src/sequel/services/projects.py`
- `src/sequel/services/clouddns.py`
- `src/sequel/services/cloudsql.py`
- `src/sequel/services/compute.py`
- `src/sequel/services/firewall.py`
- `src/sequel/services/gke.py`
- `src/sequel/services/iam.py`
- `src/sequel/services/monitoring.py`
- `src/sequel/services/pubsub.py`
- `src/sequel/services/run.py`
- `src/sequel/services/secrets.py`
- `src/sequel/services/storage.py`
- `src/sequel/services/vpc.py`

**Recommendation**: Add application shutdown handler to close all service clients gracefully.

---

### 6. ResourceState Dictionary Growth
**File**: `src/sequel/state/resource_state.py`
**Lines**: 46-64
**Severity**: LOW-MEDIUM
**Impact**: Unbounded memory growth in long-running sessions

**Issue**: ResourceState maintains 14 separate dictionaries for caching resources:
```python
self._projects: dict[str, Project] = {}
self._dns_zones: dict[str, list[ManagedZone]] = {}
self._dns_records: dict[tuple[str, str], list[DNSRecord]] = {}
self._cloudsql: dict[str, list[CloudSQLInstance]] = {}
# ... 10 more dictionaries
```

These dictionaries have no size limits or automatic cleanup. In long-running applications with many projects, they can grow unbounded.

**Mitigation**: The underlying service layer uses TTL-based cache with 100MB size limit and LRU eviction, so actual API response data is bounded. However, the state dictionaries themselves store model instances indefinitely.

**Recommendation**: Document this behavior. Consider adding optional state cleanup for long-running sessions if needed.

---

## Verification of Good Patterns

✅ **Confirmed**: Only 2 `.execute()` calls are blocking (grep search of all services)
✅ **Confirmed**: All other API calls properly use `asyncio.to_thread()`
✅ **Confirmed**: Cache has TTL, size limits (100MB), and LRU eviction
✅ **Confirmed**: Background cache cleanup task runs every 5 minutes
✅ **Confirmed**: Cache operations use `asyncio.Lock()` for thread safety
✅ **Confirmed**: Cache stats are safely copied in `get_stats()`
✅ **Confirmed**: All async operations use proper `await`
✅ **Confirmed**: No `time.sleep()` or blocking I/O found

---

## Implementation Plan

### Phase 1: Fix Critical Blocking Calls (Priority: URGENT)

**Files to Modify**:
1. `src/sequel/services/cloudsql.py`
2. `src/sequel/services/iam.py`
3. `src/sequel/services/base.py`

**Changes**:

#### 1.1 Fix CloudSQL.get_instance()
**File**: `src/sequel/services/cloudsql.py:150`

```python
# BEFORE:
response = request.execute()

# AFTER:
response = await asyncio.to_thread(request.execute)
```

**Test**: Run existing test `tests/unit/services/test_cloudsql.py::TestCloudSQLService::test_get_instance_success`

---

#### 1.2 Fix IAM.get_service_account()
**File**: `src/sequel/services/iam.py:169`

```python
# BEFORE:
response = request.execute()

# AFTER:
response = await asyncio.to_thread(request.execute)
```

**Test**: Run existing test `tests/unit/services/test_iam.py::TestIAMService::test_get_service_account_success`

---

#### 1.3 Fix BaseService credential refresh
**File**: `src/sequel/services/base.py:182-183`

Add helper function at module level (after imports, before BaseService class):
```python
def _refresh_credentials_sync(credentials: Any) -> None:
    """Synchronous credential refresh helper for asyncio.to_thread()."""
    import google.auth.transport.requests
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
```

Replace lines 182-183 in `_execute_with_retry()`:
```python
# BEFORE:
import google.auth.transport.requests

request = google.auth.transport.requests.Request()  # type: ignore[no-untyped-call]
auth_manager.credentials.refresh(request)  # type: ignore[no-untyped-call]

# AFTER:
await asyncio.to_thread(_refresh_credentials_sync, auth_manager.credentials)
```

**Test**: Manually test with expired credentials or create integration test

---

### Phase 2: Code Quality Improvements (Priority: MEDIUM)

#### 2.1 Move inline re imports to module level
**File**: `src/sequel/services/base.py`

**Change**: Add `import re` at line 11 (with other imports), remove inline imports at lines 256, 283, 313

```python
# At top of file (line 11):
import re  # Added

# Remove these three lines:
# Line 256: import re  # DELETE
# Line 283: import re  # DELETE
# Line 313: import re  # DELETE
```

**Test**: Run all service tests to ensure no regressions

---

### Phase 3: Service Cleanup (Priority: LOW - Future Enhancement)

**Goal**: Add graceful shutdown for service clients

**Approach**:
1. Add `shutdown()` method to BaseService
2. Implement in each service to close clients
3. Add app-level shutdown handler in `src/sequel/app.py`
4. Call shutdown on all services when app exits

**Example**:
```python
# In BaseService
async def shutdown(self) -> None:
    """Gracefully shutdown service and close clients."""
    if self._client is not None:
        # Close client if supported
        if hasattr(self._client, 'close'):
            await asyncio.to_thread(self._client.close)
        self._client = None

# In app.py
async def on_shutdown(self) -> None:
    """Handle application shutdown."""
    # Close all service clients
    from sequel.services import projects, clouddns, cloudsql, ...
    await projects._projects_service.shutdown()
    await clouddns._clouddns_service.shutdown()
    # ... etc
```

**Note**: This is low priority because:
- Python's garbage collector will clean up on process exit
- Most users run Sequel for short sessions
- No evidence of connection leaks in practice

**Recommendation**: Document rather than implement unless users report issues.

---

### Phase 4: Documentation (Priority: MEDIUM)

**Goal**: Document memory behavior for long-running sessions

**File**: `docs/architecture.md` or `CLAUDE.md`

**Content**:
```markdown
## Memory Management

### Service Layer
- Services use singleton pattern with cached API clients
- Clients are not explicitly closed (OS cleans up on exit)
- For long-running deployments, consider periodic restarts

### State Layer
- ResourceState maintains in-memory dictionaries for all loaded resources
- No automatic cleanup or size limits on state dictionaries
- Underlying cache has 100MB limit with LRU eviction
- For sessions with 100+ projects, memory usage can grow to several hundred MB

### Cache Layer
- TTL-based cache with 100MB size limit
- LRU eviction when size exceeded
- Background cleanup every 5 minutes
- Statistics tracking for monitoring
```

---

## Testing Strategy

### Unit Tests
**Existing tests should pass** after blocking call fixes:
- `tests/unit/services/test_cloudsql.py` - All tests
- `tests/unit/services/test_iam.py` - All tests
- `tests/unit/services/test_base.py` - Retry logic tests

**New test needed**:
- Test credential refresh in `test_base.py` (currently not tested)

### Integration Tests
**Manual testing**:
1. Run app with expired credentials to test refresh flow
2. Load 50+ projects to verify no memory leaks
3. Monitor memory usage over 30-minute session

### Performance Testing
**Before/After comparison**:
1. Time to load all resources for 10 projects
2. Memory usage after loading 50 projects
3. No regressions expected (fixes are correctness, not performance)

---

## Risk Assessment

### Low Risk Changes
- ✅ CloudSQL blocking fix (simple one-line change)
- ✅ IAM blocking fix (simple one-line change)
- ✅ Move re import to top-level (cosmetic change)

### Medium Risk Changes
- ⚠️ Base Service credential refresh (modifies error handling path)
  - **Mitigation**: Thoroughly test with expired credentials
  - **Rollback**: Simple to revert if issues found

### No Change Recommended (Accept Risk)
- ⚠️ Service cleanup on shutdown (complex, low value)
- ⚠️ ResourceState size limits (no evidence of issues)

---

## Rollout Plan

### Step 1: Create Branch
```bash
git checkout main
git pull
git checkout -b optimize
```

### Step 2: Fix Blocking Calls (Immediate)
1. Fix `cloudsql.py:150`
2. Fix `iam.py:169`
3. Fix `base.py:182-183`
4. Run full test suite
5. Commit: "fix: Wrap blocking API calls in asyncio.to_thread()"

### Step 3: Code Quality (Same PR)
1. Move `import re` to top-level in `base.py`
2. Run tests
3. Commit: "refactor: Move inline re imports to module level"

### Step 4: Testing
```bash
# Run all tests
pytest tests/

# Run service tests specifically
pytest tests/unit/services/

# Check coverage
pytest --cov=src/sequel/services --cov-report=term-missing
```

### Step 5: Create PR
- Title: "Fix blocking API calls and improve code quality"
- Description: Link to this plan, summarize findings
- Reviewers: Check diff carefully for correctness

### Step 6: Merge and Monitor
- Merge to main after CI passes
- Monitor for any issues in next release
- Document findings in CLAUDE.md

---

## Files Modified Summary

| File | Lines Changed | Type | Risk |
|------|---------------|------|------|
| `src/sequel/services/cloudsql.py` | 150 | Fix blocking call | Low |
| `src/sequel/services/iam.py` | 169 | Fix blocking call | Low |
| `src/sequel/services/base.py` | 11, 182-183 | Fix blocking call + refactor | Medium |
| `src/sequel/services/base.py` | 256, 283, 313 | Remove inline imports | Low |

**Total**: 4 files, ~8 lines of actual code changes

---

## Conclusion

The codebase demonstrates excellent async practices overall. The 3 blocking calls found are isolated bugs that slipped through—likely never triggered in practice since the affected methods (`get_instance`, `get_service_account`) may not be heavily used. The fixes are simple one-line changes.

The service cleanup concern is real but low priority—Python's garbage collector handles cleanup on exit, and most users run short sessions. Document the behavior rather than implementing complex shutdown logic.

**Recommendation**: Fix the blocking calls immediately (Phase 1), then code quality improvements (Phase 2). Document memory behavior (Phase 4) but skip service cleanup (Phase 3) unless issues arise.
