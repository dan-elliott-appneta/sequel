# Sequel - Development Guide

## Project Overview

Sequel is a Python TUI application for browsing Google Cloud resources. It uses Textual for the UI framework and official Google Cloud Python client libraries for API integration.

## Version Management

**Current Version: 0.1.0**

We follow [Semantic Versioning](https://semver.org/) (SemVer):
- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backwards-compatible)
- **PATCH** version: Bug fixes (backwards-compatible)

### Updating Version

When updating the version, change it in **both** locations:
1. `src/sequel/__init__.py` - `__version__ = "X.Y.Z"`
2. `setup.py` - `version="X.Y.Z"`
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
    - Pydantic models for all resources (Project, CloudDNS, CloudSQL, Compute, GKE, Secrets, IAM)
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

### Planned Phases

- [ ] **Phase 8: Error Handling & UX Polish** (Current) - [Plan](docs/phase-8-ux-plan.md)
  - Branch: `phase-8-ux`
  - Enhanced error recovery, progress indicators, toast notifications
  - VIM bindings for keyboard navigation (j/k/h/l/g/G)
  - Enhanced tree navigation with left/right arrow expand/collapse

- [ ] **Phase 9: Testing & Documentation** - [Plan](docs/phase-9-testing-docs-plan.md)
  - Branch: `phase-9-docs-tests`
  - 95%+ coverage, comprehensive documentation, integration tests

- [ ] **Phase 10: Packaging & Release** - [Plan](docs/phase-10-release-plan.md)
  - Branch: `phase-10-release`
  - PyPI publishing, release automation, v0.1.0 tag

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
- Default filter: `^s[d|v|p]ap[n|nc]gl.*$` (matches specific project naming patterns)
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
  - `filters.project_regex`: Project filter regex (default: `"^s[d|v|p]ap[n|nc]gl.*$"`)
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
