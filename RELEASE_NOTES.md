# Sequel 1.0.0 - Initial Release

We're excited to announce the initial release of **Sequel** - a Terminal User Interface (TUI) for browsing and inspecting Google Cloud resources!

## 🎉 Highlights

- **Hierarchical Tree View**: Navigate Google Cloud resources with an intuitive, expandable tree interface
- **Real Resource Data**: View actual DNS records, IAM roles, GKE nodes, and instance group members
- **Syntax-Highlighted JSON**: Beautiful JSON details pane with tree-sitter syntax highlighting
- **High Performance**: 215.9x cache speedup, sub-millisecond operations
- **VIM Bindings**: Native keyboard navigation for power users
- **Comprehensive Testing**: 395 tests with 94%+ code coverage

## ✨ Features

### Supported Resources

- **Projects**: Browse all accessible Google Cloud projects
- **Cloud DNS**: View managed zones and DNS records (A, CNAME, MX, TXT, etc.)
- **CloudSQL**: List database instances with version and state information
- **Compute Engine**: Instance groups with individual VM instances
- **GKE**: Clusters with individual node details
- **Secret Manager**: Secret metadata (values never retrieved)
- **IAM**: Service accounts with role bindings

### User Interface

- **Tree Navigation**: Keyboard-focused with VIM bindings (j/k/h/l)
- **JSON Details Pane**: Syntax-highlighted API responses with mouse text selection
- **Status Bar**: Live cache statistics, resource counts, keyboard hints
- **Empty Node Removal**: Automatic cleanup of projects/categories with no resources
- **Virtual Scrolling**: Smart limits with "... and N more" indicators

### Performance

- **Intelligent Caching**: LRU eviction with 100MB size limit, 90.9% hit rate
- **Parallel API Calls**: Simultaneous resource loading across services
- **Background Cleanup**: Automatic cache cleanup every 5 minutes
- **Fast Operations**: 0.001ms cache GET, 0.002ms model creation

### Security

- **Read-Only Access**: Uses `cloud-platform.read-only` scope
- **Credential Scrubbing**: Automatic removal of sensitive data from logs
- **Local Configuration**: All data stays local, no telemetry
- **ADC Authentication**: Standard Google Cloud Application Default Credentials

## 📦 Installation

```bash
pip install sequel-ag
```

### Prerequisites

- Python 3.11 or higher
- Google Cloud SDK with configured Application Default Credentials (ADC)

## 🚀 Quick Start

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Launch Sequel
sequel

# Navigation
# - j/k or ↑/↓: Navigate tree
# - Enter: Expand/collapse node
# - h/l: Move between panes
# - q: Quit
# - r: Refresh
# - Ctrl+P: Command palette
```

## 📊 Performance Benchmarks

- **Project Loading**: 0.11ms (1 project), 1.48ms (100 projects)
- **Cache**: 90.9% hit rate, 215.9x speedup vs API calls
- **Concurrent Operations**: 1000 writes in 15.68ms, 1000 reads in 2.25ms
- **Model Creation**: 0.002ms per model

## 🧪 Testing

- **Unit Tests**: 362 passing
- **Integration Tests**: 25 passing
- **Benchmarks**: 8 passing
- **Total**: 395 tests with 94%+ coverage

## 📚 Documentation

- [Installation Guide](docs/user-guide/installation.md)
- [Configuration Guide](docs/user-guide/configuration.md)
- [Usage Guide](docs/user-guide/usage.md)
- [Troubleshooting Guide](docs/user-guide/troubleshooting.md)
- [Architecture Overview](docs/architecture/overview.md)
- [Contributing Guide](docs/contributing/development.md)

## 🔧 Configuration

Sequel can be configured via environment variables or `~/.config/sequel/config.json`:

```bash
# Filter projects by regex
export SEQUEL_PROJECT_FILTER_REGEX="^my-project-prefix.*$"

# Cache settings
export SEQUEL_CACHE_TTL_PROJECTS="600"
export SEQUEL_CACHE_TTL_RESOURCES="300"

# Theme selection
export SEQUEL_THEME="textual-dark"
```

## 🐛 Known Limitations

- Alpha software - use at your own risk in production
- Limited to read-only operations
- No built-in audit logging
- Relies on GCP quota limits

## 🤝 Contributing

Contributions are welcome! See our [Development Guide](docs/contributing/development.md) for details.

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [Textual](https://textual.textualize.io/) - Modern TUI framework
- [Google Cloud Python Client Libraries](https://cloud.google.com/python/docs/reference)
- [Pydantic](https://docs.pydantic.dev/) - Data validation

## 🔗 Links

- **GitHub**: https://github.com/dan-elliott-appneta/sequel
- **PyPI**: https://pypi.org/project/sequel-ag/
- **Issues**: https://github.com/dan-elliott-appneta/sequel/issues

---

**Full Changelog**: https://github.com/dan-elliott-appneta/sequel/commits/v1.0.0
