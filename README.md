# Sequel

A Terminal User Interface (TUI) for browsing and inspecting Google Cloud resources.

## Version

Current version: **0.1.0** (Alpha)

## Features

Sequel provides a keyboard-focused, responsive interface for exploring Google Cloud resources:

- **Hierarchical tree view** with expandable sub-nodes:
  - Service Accounts → IAM roles
  - GKE Clusters → Individual nodes
  - Instance Groups → Instances
  - Automatic empty category removal
- **JSON details pane** with tree-sitter syntax highlighting, pretty-printed API responses, and mouse text selection
- **Lazy loading** for efficient API usage
- **ADC authentication** using Google Cloud Application Default Credentials
- **Comprehensive testing** with high code coverage

### Supported Resources (MVP)

- Projects
- CloudSQL instances
- Compute Engine Instance Groups
- Google Kubernetes Engine (GKE) clusters and nodes
- Secret Manager secrets (metadata only)
- IAM Service Accounts

## Prerequisites

- Python 3.11 or higher
- Google Cloud SDK with configured Application Default Credentials (ADC)

## Installation

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
    "project_regex": "^s[d|v|p]ap[n|nc]gl.*$"
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
# Project Filtering - Filter projects by regex (default: ^s[d|v|p]ap[n|nc]gl.*$)
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

# Logging
export SEQUEL_LOG_LEVEL="INFO"                    # Log level: DEBUG, INFO, WARNING, ERROR
export SEQUEL_LOG_FILE="/path/to/sequel.log"      # Log file path (optional)

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
```

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

See `docs/architecture.md` for detailed architecture documentation.

## Project Status

This project is in **alpha** stage. The MVP includes basic browsing functionality for the listed resource types. See the roadmap in `CLAUDE.md` for planned features.

## Contributing

Contributions are welcome! Please see `docs/development.md` for development guidelines.

## License

MIT License - See LICENSE file for details.

## Security

- Credentials are never logged (enforced by credential scrubbing)
- Secret values are never retrieved (only metadata)
- All user data stays local (no telemetry)

For security issues, please see SECURITY.md.

## Support

- Issues: https://github.com/dan-elliott-appneta/sequel/issues
- Documentation: https://github.com/dan-elliott-appneta/sequel/tree/main/docs
