# Phase 7: Performance Optimization

## Overview

This phase focuses on optimizing Sequel's performance through parallel API operations, cache improvements, connection pooling, and profiling.

**Branch:** `phase-7-performance`

**Current State:**
- Version: 0.1.0 (Alpha)
- Test Coverage: 94.61% (332 tests)
- All MVP features complete

## Objectives

- Implement parallel API calls using asyncio.gather()
- Add cache monitoring and automatic cleanup
- Optimize resource tree for large datasets
- Add connection pooling for API clients
- Profile and benchmark critical paths

---

## Detailed Tasks

### 7.1 Parallel API Operations

**Files to modify:**
- `src/sequel/services/projects.py` - Add parallel project listing
- `src/sequel/widgets/resource_tree.py` - Parallel resource loading per project
- `src/sequel/services/base.py` - Add gather utility method

**Implementation:**
```python
# Example pattern for parallel loading
async def load_all_resources_parallel(project_id: str):
    results = await asyncio.gather(
        cloudsql_service.list_instances(project_id),
        compute_service.list_instance_groups(project_id),
        gke_service.list_clusters(project_id),
        secrets_service.list_secrets(project_id),
        return_exceptions=True  # Don't fail all if one fails
    )
    # Handle individual failures gracefully
```

**Testing:**
- Performance benchmarks comparing serial vs parallel
- Test partial failure handling
- Verify resource limits aren't exceeded

---

### 7.2 Cache Optimization

**Files to modify:**
- `src/sequel/cache/memory.py` - Add background cleanup, monitoring, size limits

**New Features:**
- Background cleanup task (every 5 minutes)
- Cache statistics: hits, misses, evictions
- Configurable max cache size (default: 100MB)
- LRU eviction when size limit exceeded
- Cache metrics display in status bar

**Implementation:**
```python
class MemoryCache:
    def __init__(self):
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._max_size_bytes = 100 * 1024 * 1024  # 100MB
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self):
        # Background task to remove expired entries every 5 min

    def get_stats(self) -> dict:
        return self._stats.copy()
```

**Testing:**
- Test background cleanup removes expired entries
- Test cache eviction when size limit reached
- Verify statistics accuracy
- Test cleanup task lifecycle

---

### 7.3 Connection Pooling

**Files to modify:**
- `src/sequel/services/cloudsql.py` - Reuse discovery client
- `src/sequel/services/compute.py` - Reuse discovery client
- `src/sequel/services/iam.py` - Reuse discovery client
- `src/sequel/services/clouddns.py` - Reuse discovery client

**Pattern:**
- Create clients once, reuse across calls
- Currently: client created per call in some services
- Already implemented: GKE, Secrets use cached clients

**Testing:**
- Verify clients are reused
- Test concurrent access is thread-safe
- Measure latency improvement

---

### 7.4 Virtual Scrolling for Large Trees

**Files to modify:**
- `src/sequel/widgets/resource_tree.py` - Implement virtual scrolling

**Implementation:**
- Only render visible tree nodes
- Load children on-demand as user scrolls
- Set max children per expansion (currently 10 for GKE nodes, apply globally)
- Add "... and N more" nodes

**Testing:**
- Test with projects having 100+ resources
- Verify scroll performance
- Test memory usage with large datasets

---

### 7.5 Performance Profiling

**New file:** `scripts/profile.py`

**Tools:**
- cProfile for CPU profiling
- memory_profiler for memory usage
- Create baseline benchmarks

**Benchmarks to create:**
- Project loading time (1 project, 10 projects, 100 projects)
- Resource tree expansion time
- Cache hit rates
- Memory usage over time

**Testing:**
- Document baseline metrics
- Run benchmarks in CI for regression detection

---

## Success Criteria

- 50% reduction in project loading time with parallel ops
- Cache hit rate > 70% for repeated operations
- Memory usage stable over 1 hour runtime
- Tree scrolling < 16ms per frame

---

## Related Documentation

- [Phase 8: Error Handling & UX Polish](phase-8-ux-plan.md)
- [Phase 9: Testing & Documentation](phase-9-testing-docs-plan.md)
- [Phase 10: Packaging & Release](phase-10-release-plan.md)
