# Sequel

A Terminal User Interface (TUI) for browsing and inspecting Google Cloud resources.

## Version

Current version: **0.1.0** (Alpha)

## Features

Sequel provides a keyboard-focused, responsive interface for exploring Google Cloud resources:

- **Tree view** of projects and resources
- **Detail pane** with resource-specific information
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
git clone https://github.com/parallels/sequel.git
cd sequel

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -r requirements-dev.txt
pip install -e .
```

## Configuration

### Google Cloud Authentication

Sequel uses Application Default Credentials (ADC). Set up authentication using one of these methods:

```bash
# Option 1: Using gcloud CLI (recommended)
gcloud auth application-default login

# Option 2: Using a service account key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
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

- Issues: https://github.com/parallels/sequel/issues
- Documentation: https://github.com/parallels/sequel/tree/main/docs
