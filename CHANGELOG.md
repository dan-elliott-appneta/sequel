# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 7: Performance Optimization**
  - Parallel API operations using `asyncio.gather()` for simultaneous resource loading across all resource types
  - Cache optimization with LRU eviction algorithm and 100MB size limit
  - Cache statistics tracking: hits, misses, evictions, expirations
  - Background cache cleanup task running every 5 minutes
  - Virtual scrolling with MAX_CHILDREN_PER_NODE limit (50 items) and "... and N more" indicators
  - Performance profiling script (`scripts/profile.py`) for benchmarking API calls and cache performance
  - Debug script (`scripts/debug_mig.py`) for testing instance group API calls directly
  - Enhanced logging in resource tree widget for better debugging

### Added
- **JSON details pane**: Displays syntax-highlighted, pretty-printed JSON from raw GCP API responses
  - Tree-sitter powered JSON syntax highlighting with Monokai theme
  - Line numbers enabled for easy reference
  - Mouse text selection and copying support
  - Scrollable view for long API responses
  - Preserves all original API fields including custom/extra fields
  - Falls back to model dict if raw API data unavailable
- **Smart tree view**: Empty resource categories automatically removed
  - Categories removed after lazy loading discovers no resources
  - Only shows resource types that contain items (e.g., if no CloudSQL instances, node is removed after expansion)
  - Lazy loading maintains fast initial tree population
- **Hierarchical sub-nodes** for expanded resource details with real API data:
  - Service Accounts → IAM role bindings (fetched from project IAM policy)
  - GKE Clusters → Individual cluster nodes (fetched from node pools)
  - Instance Groups → VM instances (fetched from instance group members)
  - Sub-nodes display actual resource names instead of generic placeholders
  - All sub-node resources include full JSON details in the detail pane
  - Provides deeper inspection of resource composition with real data
- JSON-based configuration file system at `~/.config/sequel/config.json`
- Configuration precedence: Environment Variables > Config File > Defaults
- Theme persistence - theme changes automatically saved to config file
- Command palette (`Ctrl+P`) with theme selection
- Support for 14 Textual themes (catppuccin, dracula, gruvbox, monokai, nord, solarized, tokyo-night, etc.)
- Project filtering by regex (configurable via config file or environment variable)
- Comprehensive type checking with mypy strict mode (zero errors)
- Test coverage at 97% across entire codebase (144 tests)
- Full CI/CD with lint, type check, and test validation
- Comprehensive test suite for hierarchical sub-nodes (18 new tests)
  - Tests for service account role expansion
  - Tests for GKE cluster node expansion
  - Tests for instance group instance expansion
  - Edge case coverage (empty groups, single items, over-limit scenarios)

### Changed
- Detail pane now displays raw API JSON instead of formatted table
- Detail pane switched from Static to TextArea widget for text selection support
- Syntax highlighting uses vibrant Monokai theme for colorful JSON display
- All models now store raw API response data in `raw_data` field for inspection
- Removed border between tree and details panes for cleaner interface

### Fixed
- **Managed instance groups not showing instances**
  - Fixed API endpoint selection: managed groups now use `instanceGroupManagers().listManagedInstances()` instead of `instanceGroups().listInstances()`
  - Added `is_managed` parameter to properly detect and handle managed vs unmanaged instance groups
  - Fixed response parsing: managed groups return `managedInstances` field, unmanaged return `items`
  - Increased instance limit from 10 to 100 per group (tree applies virtual scrolling at 50)
  - Regional managed instance groups now working correctly with proper API calls
- UI border gaps when expanding tree nodes (changed from solid to tall border style)
- All mypy strict mode errors resolved using proper type casting
- Proper handling of missing type stubs for third-party libraries
- Tree clutter from empty resource categories - now automatically removed when expanded
- Syntax highlighting not working - added missing tree-sitter dependencies
  - Added tree-sitter, tree-sitter-languages, tree-sitter-json to requirements
  - JSON syntax highlighting now works with colorful Monokai theme
- Regional instance groups not loading instances correctly
  - Now properly detects both zonal and regional instance groups
  - Calls appropriate API method based on group type (regionInstanceGroups vs instanceGroups)
- IAM roles not displaying for service accounts
  - Fixed AttributeError by switching from IAM API to Cloud Resource Manager API
  - Cloud Resource Manager API provides getIamPolicy() method for fetching project IAM policies
  - Service account role bindings now display correctly in the UI
- JSON syntax highlighting rendering issue - removed CSS padding from DetailPane
  - CSS padding was interfering with TextArea's internal rendering
  - Monokai theme colors now display correctly (pink keys, yellow strings, purple numbers)
- Type checking errors in CloudDNS models and service
  - Added missing project_id and created_at fields to from_api_response methods
  - Fixed type: ignore comments to cover correct mypy error codes
  - All 38 source files now pass mypy --strict with zero errors
- Linting error in resource tree cleanup task
  - Store asyncio.create_task reference to prevent garbage collection
  - Background cleanup task now properly managed

### Security
- Credential scrubbing enforced in all logging
- Secret values never retrieved (metadata only)
- No telemetry or data collection

## [0.1.0] - 2025-12-21

### Added
- Initial MVP release
- Tree view of GCP projects and resources
- Detail pane for resource information
- Support for multiple resource types:
  - Projects
  - CloudSQL instances
  - Compute Engine Instance Groups
  - Google Kubernetes Engine (GKE) clusters and nodes
  - Secret Manager secrets (metadata only)
  - IAM Service Accounts
- Application Default Credentials (ADC) authentication
- Lazy loading for efficient API usage
- TTL-based in-memory caching (Projects: 10min, Resources: 5min)
- Async API calls with retry logic and exponential backoff
- Error handling with categorized exceptions
- Keyboard navigation with standard shortcuts
- CLI with debug and logging options

### Infrastructure
- Python 3.11+ support
- Textual TUI framework
- Google Cloud Python client libraries
- Pydantic models for type-safe data handling
- Pytest with 97% code coverage
- Ruff for linting
- Mypy for strict type checking
- GitHub Actions CI/CD

[Unreleased]: https://github.com/dan-elliott-appneta/sequel/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dan-elliott-appneta/sequel/releases/tag/v0.1.0
