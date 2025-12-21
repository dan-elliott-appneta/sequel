# Usage Guide

## Starting Sequel

```bash
# Start with default settings
sequel

# Enable debug logging
sequel --debug

# Write logs to a file
sequel --log-file /tmp/sequel.log

# Disable caching
sequel --no-cache

# Combine options
sequel --debug --log-file /tmp/sequel.log --no-cache
```

## Interface Layout

```
┌─────────────────────────────────────────────────────────┐
│  Header                                                 │
├───────────────────┬─────────────────────────────────────┤
│                   │                                     │
│  Resource Tree    │   Detail Pane                       │
│  (40%)            │   (60%)                             │
│                   │                                     │
│                   │   - JSON syntax highlighting        │
│                   │   - VIM navigation                  │
│                   │   - Text selection/copying          │
│                   │                                     │
├───────────────────┴─────────────────────────────────────┤
│  Status Bar                                             │
│  (Keyboard shortcuts, cache stats, operation status)    │
└─────────────────────────────────────────────────────────┘
```

## Tree Navigation

### VIM-Style Bindings

| Key | Action |
|-----|--------|
| `j` or `↓` | Move down |
| `k` or `↑` | Move up |
| `h` or `←` | Collapse node OR move to parent |
| `l` or `→` | Expand node OR move to first child |
| `g` | Go to top of tree |
| `G` | Go to bottom of tree |
| `Enter` | Toggle expand/collapse |

### Smart Navigation

- **h/←**: If node is expanded, collapses it. If already collapsed, moves to parent node.
- **l/→**: If node is collapsed, expands it. If already expanded, moves to first child.

## Detail Pane

The detail pane displays JSON-formatted resource details with syntax highlighting (Monokai theme).

### VIM Navigation

| Key | Action |
|-----|--------|
| `j` | Move cursor down |
| `k` | Move cursor up |
| `h` | Move cursor left |
| `l` | Move cursor right |
| `g` | Page up |
| `G` | Page down |
| `0` | Jump to line start |
| `$` | Jump to line end |

### Yanking (Copying)

| Key | Action |
|-----|--------|
| `y` | Yank (copy) selected text to clipboard |
| `Y` | Yank (copy) current line to clipboard |

### Mouse Selection

You can also select text with the mouse and copy normally (Ctrl+C or Cmd+C).

## Global Actions

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `r` | Refresh current view |
| `Ctrl+P` | Open command palette (theme selection) |
| `?` | Show help modal |
| `Esc` | Dismiss modal/dialog |

## Resource Types

Sequel displays the following Google Cloud resources:

### Projects
- Lists all accessible projects
- Filtered by regex (if configured)

### Cloud DNS
- Managed zones
- DNS records (A, CNAME, MX, TXT, etc.)

### Cloud SQL
- Database instances
- Status and connection info

### Compute Engine
- Instance Groups (managed and unmanaged)
- VM instances within groups

### Google Kubernetes Engine (GKE)
- Clusters
- Node pools and nodes

### Secret Manager
- Secrets (metadata only, values not displayed)
- Replication settings

### IAM
- Service Accounts
- Role bindings

## Using the Command Palette

1. Press `Ctrl+P` to open the command palette
2. Select a theme from the list
3. Theme is automatically saved to config file

Available themes include:
- textual-dark (default)
- textual-light
- catppuccin
- dracula
- gruvbox
- monokai
- nord
- solarized-dark
- solarized-light
- tokyo-night

## Resource Counts

Tree nodes show the count of resources in each category:

```
📁 my-project (12 resources)
  ├─ 🌐 Cloud DNS (2 zones)
  ├─ ☁️  Cloud SQL (1 instance)
  ├─ 💻 Instance Groups (3 groups)
  └─ ⎈  GKE Clusters (2 clusters)
```

## Status Bar Information

The status bar shows:
- Current operation (e.g., "⏳ Loading projects...")
- Cache hit rate (e.g., "Cache: 73% hit rate")
- API call count (e.g., "12 API calls")
- Last refresh time (e.g., "Updated 2m ago")
- Keyboard shortcut hints

## Tips

### Performance

- **Use caching**: Enabled by default. Disable only for debugging with `--no-cache`
- **Filter projects**: Use `project_filter_regex` in config to limit displayed projects
- **Lazy loading**: Resources load only when tree nodes are expanded

### Navigation

- Use VIM bindings for faster keyboard navigation
- Mouse clicks work for expanding/collapsing nodes
- Scroll with mouse wheel in both tree and detail pane

### Copying Data

- **Quick copy**: Select text with mouse, copy normally
- **VIM yank**: Press `y` to copy selected text or `Y` to copy current line
- Requires `pyperclip` library (installed by default)
