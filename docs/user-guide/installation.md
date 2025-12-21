# Installation Guide

## Prerequisites

- **Python**: 3.11 or higher
- **Google Cloud SDK** (gcloud): Required for authentication
- **Operating System**: Linux, macOS, or Windows

## Installation Methods

### From Source

```bash
# Clone the repository
git clone https://github.com/dan-elliott-appneta/sequel.git
cd sequel

# Install the package
pip install -e .
```

### Dependencies

Sequel automatically installs the following dependencies:

- **textual**: TUI framework
- **tree-sitter, tree-sitter-languages, tree-sitter-json**: Syntax highlighting
- **google-auth, google-auth-oauthlib**: Google Cloud authentication
- **google-api-python-client**: Google Cloud API client
- **google-cloud-container**: GKE API
- **google-cloud-secret-manager**: Secrets API
- **pydantic**: Data validation
- **aiohttp**: Async HTTP
- **pyperclip**: Clipboard support for VIM yanking

See `requirements.txt` for complete list with version constraints.

## Verification

After installation, verify Sequel is installed correctly:

```bash
# Check version
sequel --version

# Should output: sequel 0.1.0
```

## Troubleshooting

### Command not found: sequel

If you get "command not found" after installation:

1. Ensure the Python scripts directory is in your PATH
2. Try running with `python -m sequel.cli` instead
3. Reinstall with `pip install --force-reinstall -e .`

### Import errors

If you encounter import errors:

1. Verify Python version: `python --version` (must be 3.11+)
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Check for conflicting packages: `pip list | grep google`

### Permission denied

If you get permission errors during installation:

1. Use a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```
2. Or install with --user flag: `pip install --user -e .`
