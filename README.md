# Sequel

A Terminal User Interface (TUI) for browsing and inspecting Google Cloud resources.

## Version

Current version: **1.6.1**

## Features

Sequel provides a keyboard-focused, responsive interface for exploring Google Cloud resources:

- **Hierarchical tree view** with expandable sub-nodes showing real resource data:
  - Cloud DNS Zones → DNS records (A, CNAME, MX, TXT, etc.)
  - Cloud Storage Buckets → Objects (with file sizes and content types)
  - Service Accounts → IAM role bindings (with actual role names)
  - GKE Clusters → Individual nodes (with actual node pool names)
  - Instance Groups → VM instances (with actual instance names and status)
  - Sub-resources display in JSON details pane when selected
  - Automatic empty category removal
  - Virtual scrolling with smart limits (50-100 items per node) and "... and N more" indicators
- **JSON details pane** with tree-sitter syntax highlighting, pretty-printed API responses, and mouse text selection
- **Performance optimized**:
  - Parallel API operations for simultaneous resource loading
  - Concurrency limiting (max 5 concurrent region queries) to prevent system overload
  - Intelligent caching with LRU eviction and 100MB size limit
  - Cache statistics tracking (hits, misses, evictions, expirations)
  - Connection pooling for API clients
  - Background cache cleanup every 5 minutes
- **Lazy loading** for efficient API usage
- **ADC authentication** using Google Cloud Application Default Credentials
- **Comprehensive testing** with high code coverage (96%+)

### Supported Resources (MVP)

- Projects
- Cloud DNS managed zones and DNS records
- CloudSQL instances
- Cloud Storage buckets and objects
- Pub/Sub topics and subscriptions
- VPC Networks and subnets
- Compute Engine Instance Groups
- Firewall Policies (VPC firewall rules)
- Google Kubernetes Engine (GKE) clusters and nodes
- Secret Manager secrets (metadata only)
- IAM Service Accounts
- Cloud Monitoring Alert Policies

## Prerequisites

- Python 3.11 or higher
- Google Cloud SDK with configured Application Default Credentials (ADC)

## Installation

### From PyPI

```bash
pip install sequel-ag
```

### From Source

```bash
# Clone the repository
git clone https://github.com/dan-elliott-appneta/sequel.git
cd sequel

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -r requirements-dev.txt
pip install -e .
```

## Configuration

### Configuration File

Sequel stores user preferences in `~/.config/sequel/config.json`. This file is automatically created on first run with default values.

**Example configuration:**

```json
{
  "ui": {
    "theme": "textual-dark"
  },
  "filters": {
    "project_regex": "^my-project-prefix.*$"
  },
  "logging": {
    "log_file": "~/.config/sequel/sequel.log",
    "log_level": "INFO"
  }
}
```

You can edit this file manually or use the command palette (`Ctrl+P`) to change themes. Theme changes are automatically persisted to the config file.

**Configuration precedence:**
1. Environment variables (highest priority)
2. Config file (`~/.config/sequel/config.json`)
3. Default values

### Google Cloud Authentication

Sequel uses Application Default Credentials (ADC). Set up authentication using one of these methods:

```bash
# Option 1: Using gcloud CLI (recommended)
gcloud auth application-default login

# Option 2: Using a service account key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Environment Variables

Sequel can be configured using environment variables with the `SEQUEL_` prefix. These override config file values:

```bash
# Project Filtering - Filter projects by regex (default: empty, show all)
export SEQUEL_PROJECT_FILTER_REGEX="^my-project-prefix.*$"

# Disable project filtering (show all projects)
export SEQUEL_PROJECT_FILTER_REGEX=""

# Caching
export SEQUEL_CACHE_ENABLED="true"                # Enable/disable caching (default: true)
export SEQUEL_CACHE_TTL_PROJECTS="600"            # Project cache TTL in seconds (default: 600)
export SEQUEL_CACHE_TTL_RESOURCES="300"           # Resource cache TTL in seconds (default: 300)

# API Settings
export SEQUEL_API_TIMEOUT="30"                    # API timeout in seconds (default: 30)
export SEQUEL_API_MAX_RETRIES="3"                 # Max retry attempts (default: 3)

# Logging (defaults to ~/.config/sequel/sequel.log)
export SEQUEL_LOG_LEVEL="INFO"                    # Log level: DEBUG, INFO, WARNING, ERROR
export SEQUEL_LOG_FILE="/path/to/sequel.log"      # Log file path (default: ~/.config/sequel/sequel.log)

# UI Settings
export SEQUEL_THEME="textual-dark"                # Textual theme name
```

## Usage

```bash
# Start the application
sequel

# With debug logging
sequel --debug

# With custom log file
sequel --log-file sequel.log

# Disable caching
sequel --no-cache
```

### Keyboard Shortcuts

- `q` - Quit
- `r` - Refresh current view
- `Ctrl+P` - Open command palette (theme selection, etc.)
- `?` - Show help
- `↑/↓` - Navigate tree
- `Enter` - Expand/collapse node
- `Esc` - Dismiss modal

## Documentation

### User Guides

- [Installation Guide](docs/user-guide/installation.md) - Prerequisites and installation instructions
- [Configuration Guide](docs/user-guide/configuration.md) - All configuration options and examples
- [Authentication Guide](docs/user-guide/authentication.md) - Setting up Google Cloud credentials
- [Usage Guide](docs/user-guide/usage.md) - Interface layout, navigation, and features
- [Troubleshooting Guide](docs/user-guide/troubleshooting.md) - Common errors and solutions

### Examples

- [Basic Usage Examples](docs/examples/basic-usage.md) - Step-by-step walkthroughs for common tasks
- [Advanced Examples](docs/examples/advanced.md) - Custom configurations, performance tuning, debugging

### Architecture

- [Architecture Overview](docs/architecture/overview.md) - High-level architecture and component descriptions
- [Service Layer](docs/architecture/services.md) - API wrappers, caching, error handling
- [Widget Layer](docs/architecture/widgets.md) - UI components and event handling

### Contributing

- [Development Guide](docs/contributing/development.md) - Setup, testing, code quality checks
- [Architecture Guide](docs/contributing/architecture.md) - Adding new features and extending the codebase

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m ui

# Run performance benchmarks
pytest -m benchmark --no-cov -s
```

### Performance Benchmarks

Sequel includes performance benchmarks to track optimization improvements:

```bash
# Run benchmarks
pytest -m benchmark --no-cov -s
```

**Benchmark Results (as of Phase 9):**
- **Project Loading**:
  - 1 project: 0.11ms
  - 10 projects: 0.14ms
  - 100 projects: 1.48ms
- **Cache Performance**:
  - Hit rate: 90.9% on repeated reads
  - SET operation: 0.014ms avg
  - GET operation: 0.001ms avg
  - 1000 concurrent writes: 15.68ms
  - 1000 concurrent reads: 2.25ms
  - Cache speedup: 215.9x faster than API calls
- **Model Creation**: 0.002ms per model (1000 models in 2.30ms)

### Code Quality

```bash
# Lint code
ruff check src tests

# Type check
mypy src

# Run all quality checks (as in CI)
ruff check src tests && mypy src && pytest --cov --cov-fail-under=80
```

## Architecture

Sequel follows a layered architecture:

- **Models**: Pydantic data models for type-safe resource representation
- **Services**: Async wrappers around Google Cloud APIs
- **Widgets**: Textual UI components (tree, detail pane, status bar)
- **Cache**: TTL-based in-memory caching for API responses

See [docs/architecture/overview.md](docs/architecture/overview.md) for detailed architecture documentation.

## Project Status

Version 1.0.0 has been released! This version includes comprehensive functionality for browsing Google Cloud resources.

**Completed Phases:**
- ✅ [Phase 7: Performance Optimization](docs/phase-7-performance-plan.md) - Parallel API calls, cache optimization, LRU eviction
- ✅ [Phase 8: Error Handling & UX Polish](docs/phase-8-ux-plan.md) - VIM bindings, enhanced status bar, error recovery
- ✅ [Phase 9: Testing & Documentation](docs/phase-9-testing-docs-plan.md) - Comprehensive documentation, integration tests (35), performance benchmarks (8)
- ✅ [Phase 10: Packaging & Release](docs/phase-10-release-plan.md) - PyPI publishing, release automation

See `CLAUDE.md` for development guidelines.

## Contributing

Contributions are welcome! Please see:
- [Development Guide](docs/contributing/development.md) for development setup and guidelines
- [Architecture Guide](docs/contributing/architecture.md) for extending the codebase

## License

MIT License - See LICENSE file for details.

## Security

- **Credentials are never logged** (enforced by credential scrubbing filter)
- **Secret values are never retrieved** (only metadata is accessed)
- **All user data stays local** (no telemetry or external reporting)
- **Regex patterns are validated** to prevent ReDoS (Regular Expression Denial of Service) attacks
  - User-provided regex patterns from config files or environment variables are validated at startup
  - Patterns with nested quantifiers or catastrophic backtracking potential are rejected
  - Invalid patterns are logged and disabled gracefully (app continues with filtering disabled)

For security issues and detailed security practices, please see [SECURITY.md](SECURITY.md).

## Support

- Issues: https://github.com/dan-elliott-appneta/sequel/issues
- Documentation: https://github.com/dan-elliott-appneta/sequel/tree/main/docs
