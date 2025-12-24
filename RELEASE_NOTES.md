# Cloud Monitoring Alert Policies Support 🚨

This release adds support for browsing Cloud Monitoring Alert Policies, enabling users to view and manage their alerting configuration directly from Sequel.

## New Features

### Cloud Monitoring Alert Policies
- **Flat resource browsing**: Alert Policies displayed as a flat list per project
- **Policy information**: Name, display name, enabled status, condition count, notification channel count, combiner type, documentation
- **Visual indicators**: 🚨 for alert policies, ✓/✗ for enabled/disabled status
- **Condition summary**: Displays condition count with combiner (e.g., "3 conditions (AND)")
- **Smart filtering**: Filter by policy name or display name
- **Lazy loading**: Policies load only when category is expanded
- **Full details**: Complete policy configuration visible in JSON detail pane

## Implementation Details

- Added AlertPolicy model with comprehensive metadata extraction
- Implemented MonitoringService with Cloud Monitoring API v3 integration
- Helper methods: `is_enabled()`, `get_condition_summary()`
- Integrated with state management for efficient caching
- Follows Firewall pattern for flat resource implementation
- Full test coverage: 29 model tests, 12 service tests

## Technical Improvements

- Robust API response parsing handling complex nested structures
- Proper project path formatting for Cloud Monitoring API (projects/{PROJECT_ID})
- Graceful handling of missing or invalid data
- Support for all combiner types (OR, AND, AND_WITH_MATCHING_RESOURCE, etc.)

## Statistics

- **Total Tests**: 666 (all passing)
- **Coverage**: 91.98%
- **New Files**: 4 (models, service, tests)
- **Modified Files**: 8
- **New Tests**: 41 (29 model, 12 service)

## Supported Resources

Sequel now supports **12 resource categories**:
1. Cloud DNS (zones → records)
2. Cloud SQL instances
3. Compute Instance Groups (groups → instances)
4. GKE Clusters (clusters → nodes)
5. Secrets
6. Service Accounts (accounts → role bindings)
7. Firewall Policies
8. Cloud Storage Buckets (buckets → objects)
9. Pub/Sub (topics → subscriptions)
10. Cloud Run (services and jobs)
11. VPC Networks (networks → subnets)
12. **Cloud Monitoring Alert Policies** ✨ NEW

## Installation

```bash
pip install sequel-ag==1.6.0
```

Or upgrade from a previous version:

```bash
pip install --upgrade sequel-ag
```

## Full Changelog

**Merged PRs:**
- #27: Add Cloud Monitoring Alert Policies support

**Commits:**
- docs: Add Cloud Monitoring Alert Policies to implementation plan
- feat: Add Cloud Monitoring Alert Policies support
- test: Add comprehensive tests for Cloud Monitoring Alert Policies
- docs: Mark Cloud Monitoring Alert Policies as completed
- docs: Add PR #27 reference to alert policies documentation
- chore: Bump version to 1.6.0

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
