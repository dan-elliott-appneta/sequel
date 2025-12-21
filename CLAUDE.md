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

- [x] **Phase 1: Infrastructure Setup** (Current)
  - Branch: `phase-1-infrastructure`
  - Project structure, CI/CD, testing framework

### Planned Phases

- [ ] **Phase 2: Authentication & Base Services**
  - Branch: `phase-2-auth-services`
  - ADC authentication, base service class, secure logging

- [ ] **Phase 3: Data Models & Project Service**
  - Branch: `phase-3-models-projects`
  - Pydantic models, project service, caching

- [ ] **Phase 4: Resource Models & Services**
  - Branch: `phase-4-resources`
  - CloudSQL, Compute, GKE, Secrets, IAM services

- [ ] **Phase 5: Core TUI Widgets**
  - Branch: `phase-5-widgets`
  - Tree widget, detail pane, status bar, error modal

- [ ] **Phase 6: Application Integration**
  - Branch: `phase-6-integration`
  - Main app, screens, CLI entry point

- [ ] **Phase 7: Performance Optimization**
  - Branch: `phase-7-performance`
  - Async optimization, lazy loading, caching strategy

- [ ] **Phase 8: Error Handling & UX Polish**
  - Branch: `phase-8-ux`
  - Comprehensive error handling, UX enhancements

- [ ] **Phase 9: Testing & Documentation**
  - Branch: `phase-9-docs-tests`
  - >90% coverage, complete documentation

- [ ] **Phase 10: Packaging & Release**
  - Branch: `phase-10-release`
  - Release preparation, v0.1.0 tag

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

### Testing

- Write tests alongside implementation
- Target: >90% overall coverage
- Test all error paths
- Use fixtures from `tests/conftest.py`

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
