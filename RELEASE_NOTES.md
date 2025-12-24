# Cloud Storage Objects Support 📄

This release adds support for browsing Cloud Storage objects within buckets, creating a hierarchical Buckets → Objects view.

## New Features

### Cloud Storage Buckets → Objects
- **Hierarchical resource browsing**: Buckets → Objects
- **Object information**: Name, human-readable size (B, KB, MB, GB, TB), content type, creation time, storage class, CRC32C checksum
- **Visual indicators**: 🪣 for buckets, 📄 for objects
- **Smart pagination**: Limit to first 100 objects per bucket to prevent UI overload
- **Lazy loading**: Objects load only when bucket is expanded
- **Filter support**: Filter objects by name using the search functionality

## Implementation Details

- Added StorageObject model with comprehensive metadata and get_display_size() helper
- Implemented list_objects() service method with pagination support (max 100 objects)
- Made buckets expandable in resource tree following Cloud DNS pattern
- Integrated with state management for efficient caching
- Full test coverage: 15 model tests, 8 service tests

## Technical Improvements

- Used contextlib.suppress for cleaner exception handling (ruff SIM105)
- Proper type annotations for mypy strict mode compliance
- Human-readable file size formatting (e.g., "1.5 MB", "3.2 GB")

## Statistics

- **Total Tests**: 625 (all passing)
- **Coverage**: 76.76%
- **New Files**: Modified 11 files
- **New Tests**: 23 tests (15 model, 8 service)

## Supported Resources

Sequel now supports **11 resource categories** with **5 hierarchical resources**:
1. Cloud DNS (zones → records)
2. Cloud SQL instances
3. Compute Instance Groups (groups → instances)
4. GKE Clusters (clusters → nodes)
5. Secrets
6. Service Accounts (accounts → role bindings)
7. Firewall Policies
8. **Cloud Storage (buckets → objects)** ✨ NEW
9. Pub/Sub (topics → subscriptions)
10. Cloud Run (services and jobs)
11. VPC Networks (networks → subnets)

## Installation

```bash
pip install sequel-ag==1.5.1
```

Or upgrade from a previous version:

```bash
pip install --upgrade sequel-ag
```

## Full Changelog

**Merged PRs:**
- #26: Add Cloud Storage Buckets → Objects hierarchical support

**Commits:**
- docs: Add Cloud Storage Objects to implementation plan
- feat: Add Cloud Storage Objects hierarchical support
- test: Add comprehensive tests for Cloud Storage Objects
- docs: Update README to include Cloud Storage Objects feature
- fix: Resolve linting and type checking issues
- chore: Bump version to 1.5.1 and update documentation

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
