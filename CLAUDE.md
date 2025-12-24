# Sequel - Development Guide

## Project Overview

Sequel is a Python TUI application for browsing Google Cloud resources. It uses Textual for the UI framework and official Google Cloud Python client libraries for API integration.

## Version Management

**Current Version: 1.6.1**

We follow [Semantic Versioning](https://semver.org/) (SemVer):
- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backwards-compatible)
- **PATCH** version: Bug fixes (backwards-compatible)

### Updating Version

When updating the version, change it in **both** locations:
1. `src/sequel/__init__.py` - `__version__ = "X.Y.Z"`
2. `pyproject.toml` - `version = "X.Y.Z"`
3. `pyproject.toml` - `version = "X.Y.Z"`
4. Update `README.md` to reflect the new version
5. Update `CHANGELOG.md` with changes

## Implementation Phases

This project is being built in 10 phases. Each phase is implemented in its own branch and merged via PR.

### Completed Phases

- [x] **Phase 1: Infrastructure Setup**
  - Branch: `phase-1-infrastructure`
  - Project structure, CI/CD, testing framework

- [x] **Phase 2: Authentication & Base Services**
  - Branch: `phase-2-auth-services`
  - ADC authentication, base service class, secure logging

- [x] **Phases 3-6: MVP Implementation**
  - Branch: `phases-3-6-implementation`
  - Combined implementation of data models, services, widgets, and application integration
  - Includes:
    - Pydantic models for all resources (Project, CloudDNS, CloudSQL, Storage, Compute, Firewall, GKE, Secrets, IAM)
    - Service layer for all GCP APIs with caching and retry logic
    - Resource tree widget with lazy loading (includes CloudDNS zones → records hierarchy)
    - Detail pane for resource information with JSON syntax highlighting
    - Main application with CLI entry point
    - Configuration file system (JSON-based)
    - Command palette with theme selection
    - Project filtering by regex
  - Test coverage: 94.61% (332 tests)
  - All CI checks passing (lint, type check, tests)

- [x] **Phase 7: Performance Optimization** - [Plan](docs/phase-7-performance-plan.md)
  - Branch: `phase-7-performance`
  - Implemented:
    - Parallel API operations using asyncio.gather() for simultaneous resource loading
    - Cache optimization with LRU eviction, size limits (100MB), and background cleanup
    - Cache statistics tracking (hits, misses, evictions, expirations)
    - Connection pooling for all API clients (already implemented in all services)
    - Virtual scrolling with MAX_CHILDREN_PER_NODE limit (50 items) and "... and N more" indicators
    - Performance profiling script (scripts/profile.py) for benchmarking
    - Bug fix: Managed instance groups now use correct API (instanceGroupManagers vs instanceGroups)
    - Bug fix: Increased instance limit from 10 to 100 per group
    - Debug script (scripts/debug_mig.py) for testing instance group API calls
  - Test coverage: **96.25%** (362 tests) - exceeded 90% goal!
  - All tests passing
  - PR: #6

- [x] **Phase 8: Error Handling & UX Polish** - [Plan](docs/phase-8-ux-plan.md)
  - Branch: `phase-8-ux`
  - Implemented:
    - VIM bindings (j/k for up/down, h/l for collapse/expand, g/G for top/bottom)
    - Smart collapse/expand (h/← collapses or moves to parent, l/→ expands or moves to child)
    - Enhanced status bar with live stats (operation, cache hit rate, API calls, last refresh)
    - Resource counts in tree node labels with proper pluralization
    - Enhanced error recovery (credential refresh, quota wait/retry)
  - Not Implemented:
    - Toast notifications (planned but not implemented - encountered Textual layout issues with z-ordering)
      - Stub methods exist in `main.py` but do nothing (pass statements)
      - No `toast.py` widget file exists
      - Status bar provides similar feedback functionality
      - May be revisited in future if Textual adds better z-index/layer support
    - Progress indicators (status bar serves this purpose)
  - Test coverage: **96.02%** (362 tests) maintained
  - All tests passing
  - All linting and type checking passing
  - PR: #7

- [x] **Phase 9: Testing & Documentation** - [Plan](docs/phase-9-testing-docs-plan.md)
  - Branch: `phase-9-docs-tests`
  - Implemented:
    - 12 comprehensive documentation files (~5,000 lines)
    - 35 integration tests (cache lifecycle, concurrent access, full workflow)
    - 8 performance benchmarks with baseline metrics
    - Total: 395 tests (362 unit, 25 integration, 8 benchmarks) with 94%+ coverage
  - All tests passing
  - All linting and type checking passing
  - PR: #8

- [x] **Phase 10: Packaging & Release** - [Plan](docs/phase-10-release-plan.md)
  - Branch: `phase-10-release`
  - Implemented:
    - PyPI publishing (sequel-ag package)
    - Release automation
    - v1.0.0 tag
  - Package available on PyPI
  - All documentation updated

### Post-Release Improvements (v1.0.1+)

**Security & Lifecycle Fixes** (December 2025):
- ✅ **Timer lifecycle management**: Added `on_unmount()` handler to properly cancel pending filter timers
  - Prevents callbacks executing on destroyed widgets
  - Fixes potential memory leaks on screen unmount
  - Located in: `src/sequel/screens/main.py`

- ✅ **Regex validation & ReDoS prevention**: Added comprehensive regex validation system
  - Validates syntax at config load time (prevents crashes)
  - Detects and blocks ReDoS patterns (nested quantifiers, overlapping alternations)
  - Gracefully handles invalid patterns (logs warning, disables filtering)
  - New module: `src/sequel/utils/regex_validator.py`
  - Integrated in: `src/sequel/config.py`
  - Protects against malicious or poorly-written regex in `SEQUEL_PROJECT_FILTER_REGEX`

- ✅ **Documentation clarity**: Clarified toast notification implementation status
  - Toast notifications were **not** implemented (only stub methods exist)
  - Textual layout issues prevented proper implementation
  - Status bar provides equivalent functionality
  - Updated both CLAUDE.md and code comments for consistency

**New Resource Support** (December 2025):
- ✅ **Cloud Storage (v1.1.0)**: Added Cloud Storage buckets support
  - Simple flat resource (Tier 1 difficulty)
  - Shows bucket name, location, storage class, creation time
  - Full test coverage (23 model tests, 12 service tests)
  - PR: #22

- ✅ **Pub/Sub (v1.2.0)**: Added Pub/Sub topics and subscriptions support
  - Hierarchical resource: Topics → Subscriptions (Tier 3 difficulty)
  - Topics show labels, schema, message retention, KMS encryption
  - Subscriptions show type (Push/Pull), ACK deadline, filters
  - Icons: 📢 for topics, 📬 for push subscriptions, 📭 for pull subscriptions
  - Full test coverage (23 model tests, 15 service tests)
  - PR: #23

- ✅ **VPC Networks (v1.4.0)**: Added VPC Networks and Subnets support
  - Hierarchical resource: Networks → Subnets (Tier 3 difficulty)
  - Networks show name, mode (auto/custom), subnet count, creation time
  - Subnets show name, region, IP range (CIDR), private Google access, flow logs
  - Icons: 🌐 for networks, 🔗 for subnets
  - Uses aggregatedList for subnets to avoid region iteration
  - Follows Cloud DNS pattern for hierarchical expansion
  - Full test coverage (9 model tests, 18 service tests)
  - PR: #25

- ✅ **Cloud Storage Objects (v1.5.1)**: Cloud Storage Objects support
  - Hierarchical resource: Buckets → Objects (Tier 2 difficulty)
  - Buckets already implemented in v1.1.0, now making them expandable
  - Objects show name, size (human-readable), content type, creation time, storage class
  - Icons: 🪣 for buckets, 📄 for objects
  - Pagination support with 100-object limit per bucket
  - Follows Cloud DNS pattern for hierarchical expansion
  - Full test coverage (15 model tests, 8 service tests)
  - PR: #26

- ✅ **Cloud Monitoring Alert Policies (v1.6.0)**: COMPLETED
  - Simple flat resource (Tier 4 difficulty - complex nested structure)
  - Shows alert policy name, enabled status, condition count, notification channels
  - Icon: 🚨 for alert policies
  - Follows Firewall pattern for flat resource implementation
  - Complex condition structures visible in JSON detail pane
  - Helper methods for enabled status and condition summary
  - Full test coverage (29 model tests, 12 service tests)
  - Branch: `alerts`
  - PR: #27

- ✅ **Performance & Code Quality Optimizations (v1.6.1)**: COMPLETED
  - Fixed 3 critical blocking API calls that blocked the event loop
  - Fixed CloudSQL.get_instance() blocking execute() call
  - Fixed IAM.get_service_account() blocking execute() call
  - Fixed BaseService credential refresh blocking operations
  - Moved inline re imports to module level for better code organization
  - All 666 tests passing with no regressions
  - Branch: `optimize`
  - PR: #28

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `phase-N-description` - Feature branches for each phase
- All changes go through PRs with required checks

### PR Requirements

All PRs must pass:
- ✅ Linting (ruff)
- ✅ Type checking (mypy --strict)
- ✅ Tests (pytest with 80% coverage minimum)
- ✅ Python 3.11 and 3.12 compatibility

### Making Changes

1. Create a branch for your phase
2. Implement the phase according to the plan
3. Run quality checks locally:
   ```bash
   ruff check src tests
   mypy src
   pytest --cov --cov-fail-under=80
   ```
4. Commit changes with descriptive messages
5. Push and create PR
6. Monitor PR checks
7. Address any failures
8. Merge when all checks pass

## Code Standards

### Python Style

- Follow PEP 8 (enforced by ruff)
- Line length: 100 characters
- Use type hints everywhere (enforced by mypy strict mode)
- Write docstrings for all public classes and methods

### Security

**CRITICAL RULES:**
- Never log credentials, tokens, or secret values
- Use credential scrubbing filter in all logging
- For secrets, only retrieve metadata, never values
- Test credential scrubbing with unit tests
- **Validate all user-provided regex patterns** to prevent:
  - ReDoS (Regular Expression Denial of Service) attacks
  - Invalid syntax that crashes the application
  - Overly complex patterns that cause performance issues

**Regex Validation:**
- All regex patterns from config files or environment variables are validated at load time
- Use `sequel.utils.regex_validator` module for validation
- Patterns with nested quantifiers (e.g., `(a+)+`) are rejected as potential ReDoS attacks
- Invalid patterns are logged and disabled (app continues with filtering disabled)
- Located in: `src/sequel/utils/regex_validator.py`

See [SECURITY.md](../SECURITY.md) for detailed security practices and vulnerability reporting.

### Testing

- Write tests alongside implementation
- Target: >90% overall coverage (currently at 94.61%)
- Test all error paths
- Use fixtures from `tests/conftest.py`
- All tests must pass in CI for Python 3.11 and 3.12

### Type Safety

- **Strict mypy mode** enforced across entire codebase
- All functions have proper type hints
- Using `cast()` from typing for cache returns to maintain type safety
- Type expressions in `cast()` must be quoted (ruff requirement)
- Third-party libraries without type stubs configured in `pyproject.toml`:
  - `google.auth.*`
  - `google.cloud.*`
  - `googleapiclient.*`
  - `textual.*`
- Zero mypy errors allowed in CI

### Async Best Practices

- All GCloud API calls must be async
- Use `asyncio.gather()` for parallel operations
- **Use `asyncio.Semaphore()` to limit concurrent operations** when making many parallel API calls
  - Example: Load balancer service limits to 5 concurrent region queries (not 30+)
  - Prevents system overload, memory fragmentation, and segfaults with large datasets
- Set timeouts on all network calls (30s default)
- Handle `CancelledError` properly

## Project Structure

```
sequel/
├── src/sequel/           # Source code
│   ├── models/           # Pydantic data models
│   ├── services/         # GCloud API wrappers
│   ├── cache/            # Caching layer
│   ├── widgets/          # Textual UI components
│   ├── screens/          # Textual screens
│   └── utils/            # Utilities (logging, formatters)
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── ui/               # UI tests
└── docs/                 # Documentation
```

## Key Architectural Decisions

### 1. MVC-like Architecture
- **Models**: Pydantic dataclasses (type-safe, validated)
- **Services**: Async API wrappers returning models
- **Widgets**: Textual components consuming models

### 2. Lazy Loading
- Tree nodes load children only on expand
- Reduces API calls and improves performance

### 3. TTL Caching
- In-memory cache with configurable TTL
- Projects: 10min, Resources: 5min
- Invalidate on explicit refresh

### 4. Error Categorization
- AuthError, PermissionError, QuotaError, NetworkError
- Context-specific error handling and recovery

## Critical Implementation Details

### Google Cloud Authentication
- Use `google.auth.default()` to load ADC
- ADC sources: `GOOGLE_APPLICATION_CREDENTIALS` → gcloud CLI → GCE metadata
- Validate credentials and scopes on startup

### Credential Scrubbing
- Implement in `src/sequel/utils/logging.py`
- Regex patterns for tokens, keys, Bearer headers
- Unit test to verify scrubbing works

### Textual Integration
- Use reactive attributes for state management
- Never block the UI thread (always async)
- Use `App.run_test()` for UI testing

### Project Filtering
- Projects can be filtered by regex using `SEQUEL_PROJECT_FILTER_REGEX` environment variable
- Default filter: `""` (empty string - shows all projects)
- Filter matches against both `project_id` and `display_name`
- Set to empty string (`""`) to disable filtering and show all projects
- Invalid regex patterns are logged but don't crash the app
- Configured in `src/sequel/config.py`, applied in `src/sequel/widgets/resource_tree.py`

### Configuration File System
- User preferences stored in `~/.config/sequel/config.json` (JSON format)
- File location follows XDG Base Directory spec (`XDG_CONFIG_HOME` or `~/.config`)
- Can be overridden with `SEQUEL_CONFIG_DIR` environment variable
- Configuration precedence: Environment Variables > Config File > Defaults
- Current supported settings:
  - `ui.theme`: Textual theme name (default: `"textual-dark"`)
  - `filters.project_regex`: Project filter regex (default: `""`)
- Implemented in `src/sequel/config_file.py` with helpers:
  - `load_config_file()`: Load config from JSON
  - `save_config_file()`: Save config to JSON
  - `update_config_value()`: Update single value and save
  - `get_default_config()`: Get default configuration structure
- Integrated with `Config.from_env()` in `src/sequel/config.py`

### Command Palette & Theme Persistence
- Press `Ctrl+P` to open the command palette
- Textual's built-in "set-theme" command is available
- Custom theme provider also available in `src/sequel/commands.py`
- Available themes (Textual built-in): catppuccin-frappe, catppuccin-latte, catppuccin-macchiato, catppuccin-mocha, dracula, gruvbox, monokai, nord, solarized-dark, solarized-light, textual-ansi, textual-dark, textual-light, tokyo-night
- **Theme persistence**: The `watch_theme()` method in `SequelApp` automatically saves any theme change to the config file, regardless of how the theme is changed (built-in command, custom provider, or programmatic change)
- Command providers registered via `COMMAND_PROVIDERS` class variable in app

## Common Gotchas

| Issue | Solution |
|-------|----------|
| API quota exceeded | Implement caching and rate limiting |
| API not enabled | Handle `ServiceNotEnabled`, show helpful message |
| Async exceptions swallowed | Wrap all async ops in try/except |
| Credential expiry | Handle `RefreshError`, prompt re-auth |
| Large datasets slow UI | Lazy loading, pagination, virtual scrolling |
| Segfaults with large datasets (60+ items) | Use MAX_CHILDREN_PER_NODE limits in tree loading, asyncio.Semaphore to limit concurrent API calls |

## Documentation Requirements

Before git push to any branch:
1. Update README.md if user-facing changes
2. Update this file (CLAUDE.md) if architecture/workflow changes
3. Update version if needed
4. Keep inline code documentation current

## Useful Commands

```bash
# Install for development
pip install -e .
pip install -r requirements-dev.txt

# Run quality checks
ruff check src tests          # Lint
mypy src                      # Type check
pytest --cov                  # Test with coverage

# Run specific test types
pytest -m unit                # Unit tests only
pytest -m integration         # Integration tests only
pytest -m ui                  # UI tests only

# Install package
pip install .
```

## References

- Detailed implementation plan: `~/.claude/plans/lexical-coalescing-melody.md`
- Textual docs: https://textual.textualize.io/
- Google Cloud Python: https://cloud.google.com/python/docs/reference

## Notes for Claude Code

- Each phase should be implemented in its own branch
- Create PR when phase is complete
- Monitor PR checks and fix any failures
- Update version and docs before committing
- Maintain semantic versioning throughout
