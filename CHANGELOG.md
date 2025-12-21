# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **JSON details pane**: Displays syntax-highlighted, pretty-printed JSON from raw GCP API responses
  - Monokai theme for JSON syntax highlighting
  - Line numbers enabled for easy reference
  - Preserves all original API fields including custom/extra fields
  - Falls back to model dict if raw API data unavailable
- JSON-based configuration file system at `~/.config/sequel/config.json`
- Configuration precedence: Environment Variables > Config File > Defaults
- Theme persistence - theme changes automatically saved to config file
- Command palette (`Ctrl+P`) with theme selection
- Support for 14 Textual themes (catppuccin, dracula, gruvbox, monokai, nord, solarized, tokyo-night, etc.)
- Project filtering by regex (configurable via config file or environment variable)
- Comprehensive type checking with mypy strict mode (zero errors)
- Test coverage at 97% across entire codebase (144 tests)
- Full CI/CD with lint, type check, and test validation

### Changed
- Detail pane now displays raw API JSON instead of formatted table
- All models now store raw API response data in `raw_data` field for inspection

### Fixed
- UI border gaps when expanding tree nodes (changed from solid to tall border style)
- All mypy strict mode errors resolved using proper type casting
- Proper handling of missing type stubs for third-party libraries

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
