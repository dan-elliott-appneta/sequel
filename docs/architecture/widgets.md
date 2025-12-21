# Widget Architecture

The widget layer provides the user interface components using the Textual framework. All widgets are async-aware and integrate with the service layer.

## Widget Hierarchy

```
SequelApp (Textual App)
  └── MainScreen (Screen)
        ├── Header (Textual built-in)
        ├── Horizontal Container (#main-container)
        │     ├── Vertical Container (#tree-container, 40% width)
        │     │     └── ResourceTree (custom widget)
        │     └── Vertical Container (#detail-container, 60% width)
        │           └── DetailPane (custom widget)
        └── StatusBar (custom widget, docked bottom)
```

## MainScreen

**File:** `src/sequel/screens/main.py`

**Purpose:** Main application screen providing the overall layout and coordinating widget interactions.

### Layout

```
+------------------------------------------+
|  Header                                  |
+------------------+----------------------+
|                  |                      |
|  Resource Tree   |   Detail Pane        |
|  (40%)           |   (60%)              |
|                  |                      |
+------------------+----------------------+
|  Status Bar                              |
+------------------------------------------+
```

**CSS Layout:**
- Vertical layout for screen
- Horizontal layout for main container (tree + detail)
- Fixed width ratios: 40% tree, 60% detail
- Status bar docked at bottom (height: 1 line)

### VIM Navigation Bindings

| Key | Action | Description |
|-----|--------|-------------|
| `j`, `↓` | cursor_down | Move down in tree |
| `k`, `↑` | cursor_up | Move up in tree |
| `h`, `←` | collapse_node | Collapse node OR move to parent |
| `l`, `→` | expand_node | Expand node OR move to first child |
| `g` | cursor_top | Go to top of tree (first project) |
| `G` | cursor_bottom | Go to bottom of tree (last visible node) |

**Smart Navigation:**
- **h/←**: If node is expanded, collapse it. If already collapsed, move to parent.
- **l/→**: If node is collapsed and can expand, expand it. If already expanded, move to first child.

### Event Handling

**`on_tree_node_highlighted(event)`**
- Triggered when user selects a tree node
- Updates detail pane with resource data
- Updates status bar with project info
- Clears detail pane if node has no data

**`on_mount()`**
- Loads projects into tree on screen mount
- Shows loading indicator in status bar
- Updates last refresh time

**`refresh_tree()`**
- Reloads all projects from API
- Shows "Refreshing resources..." in status bar
- Updates last refresh timestamp

### Methods

- `show_toast(message, type, duration)`: Toast notifications (currently disabled due to layout issues)
- `refresh_tree()`: Refresh all projects and resources
- `_get_last_visible_node(node)`: Recursively find last visible node for 'G' navigation

## ResourceTree

**File:** `src/sequel/widgets/resource_tree.py`

**Purpose:** Hierarchical tree view displaying GCP resources with lazy loading.

### Tree Structure

```
GCP Resources (root)
  ├── Project 1
  │     ├── 🌐 Cloud DNS
  │     │     ├── Zone 1
  │     │     │     ├── A Record
  │     │     │     └── CNAME Record
  │     │     └── Zone 2
  │     ├── ☁️  Cloud SQL
  │     │     └── Instance 1
  │     ├── 💻 Instance Groups
  │     │     ├── Group 1
  │     │     │     ├── VM Instance 1
  │     │     │     └── VM Instance 2
  │     │     └── Group 2
  │     ├── ⎈  GKE Clusters
  │     │     └── Cluster 1
  │     │           ├── Node Pool 1
  │     │           │     ├── Node 1
  │     │           │     └── Node 2
  │     │           └── Node Pool 2
  │     ├── 🔐 Secrets
  │     │     ├── Secret 1
  │     │     └── Secret 2
  │     └── 👤 Service Accounts
  │           └── SA 1
  └── Project 2
        └── ...
```

### Resource Types

Defined in `ResourceType` class:

| Type | Constant | Expandable | Description |
|------|----------|------------|-------------|
| Project | `PROJECT` | Yes | GCP project (root level) |
| Cloud DNS | `CLOUDDNS` | Yes | DNS category node |
| DNS Zone | `CLOUDDNS_ZONE` | Yes | Managed zone with records |
| DNS Record | `CLOUDDNS_RECORD` | No | Individual record (leaf) |
| Cloud SQL | `CLOUDSQL` | Yes | Cloud SQL category node |
| Compute | `COMPUTE` | Yes | Compute category node |
| Instance Group | `COMPUTE_INSTANCE_GROUP` | Yes | Instance group with VMs |
| VM Instance | `COMPUTE_INSTANCE` | No | Individual VM (leaf) |
| GKE | `GKE` | Yes | GKE category node |
| GKE Cluster | `GKE_CLUSTER` | Yes | Cluster with node pools |
| GKE Node | `GKE_NODE` | No | Individual node (leaf) |
| Secrets | `SECRETS` | Yes | Secrets category node |
| IAM | `IAM` | Yes | IAM category node |
| Service Account | `IAM_SERVICE_ACCOUNT` | Yes | Service account with roles |
| Role | `IAM_ROLE` | No | Role binding (leaf) |

### ResourceTreeNode

**Purpose:** Data class storing metadata for each tree node.

**Fields:**
- `resource_type`: Type constant (e.g., `ResourceType.PROJECT`)
- `resource_id`: Unique identifier
- `resource_data`: Pydantic model instance (for detail pane)
- `project_id`: Parent project ID
- `location`: GCP location/region (for GKE)
- `zone`: GCP zone (for Compute)
- `loaded`: Whether children have been loaded

### Lazy Loading

Resources are loaded only when nodes are expanded:

**`on_tree_node_expanded(event)`** (not shown in excerpt, but implemented):
1. Check if node data already loaded (`node.data.loaded`)
2. If not loaded:
   - Determine resource type
   - Call appropriate service method
   - Create child nodes from results
   - Mark node as loaded
   - Handle errors gracefully

**Benefits:**
- Reduces initial API calls (only projects loaded at startup)
- Decreases memory usage
- Improves startup time
- Resources loaded on-demand as user navigates

### Child Limiting

**Constant:** `MAX_CHILDREN_PER_NODE = 50`

When a node has more than 50 children:
- Display first 50 children
- Add "💭 ... and N more" indicator node
- Prevents UI slowdown with large datasets (e.g., GKE node pools with 100+ nodes)

**Methods:**
- `_should_limit_children(count)`: Check if count exceeds limit
- `_add_more_indicator(parent, remaining_count)`: Add "... and N more" node

### Project Filtering

**`load_projects()`** applies regex filter from config:

```python
config = get_config()
if config.project_filter_regex:
    pattern = re.compile(config.project_filter_regex)
    filtered_projects = [
        p for p in projects
        if pattern.match(p.project_id) or pattern.match(p.display_name)
    ]
```

- Filter matches against project ID or display name
- Logs filter results (e.g., "Filtered 100 projects to 10 using regex: ...")
- Handles invalid regex gracefully

### Background Cleanup

**`cleanup_empty_nodes()`** (mentioned in code):
- Asynchronous task started after project load
- Removes category nodes with no children
- Non-blocking (runs in background)
- Prevents clutter from API-not-enabled categories

### Icons

| Resource Type | Icon | Unicode |
|--------------|------|---------|
| Project | 📁 | U+1F4C1 |
| Cloud DNS | 🌐 | U+1F310 |
| Cloud SQL | ☁️ | U+2601 |
| Compute | 💻 | U+1F4BB |
| GKE | ⎈ | U+2388 (helm) |
| Secrets | 🔐 | U+1F510 |
| IAM | 👤 | U+1F464 |
| More indicator | 💭 | U+1F4AD |

## DetailPane

**File:** `src/sequel/widgets/detail_pane.py`

**Purpose:** Read-only JSON viewer with syntax highlighting and VIM navigation.

### Features

1. **Syntax Highlighting**
   - Uses TextArea widget with syntax highlighting
   - Theme: Monokai (hardcoded)
   - Language: JSON
   - Tree-sitter-based highlighting

2. **VIM Navigation**

| Key | Action | Description |
|-----|--------|-------------|
| `j` | cursor_down | Move cursor down |
| `k` | cursor_up | Move cursor up |
| `h` | cursor_left | Move cursor left |
| `l` | cursor_right | Move cursor right |
| `g` | cursor_page_up | Page up |
| `G` | cursor_page_down | Page down |
| `0` | cursor_line_start | Jump to line start |
| `$` | cursor_line_end | Jump to line end |
| `y` | yank_selection | Yank (copy) selected text |
| `Y` | yank_line | Yank (copy) current line |

**Note:** Bindings only active when detail pane has focus.

3. **Clipboard Integration**

Uses `pyperclip` library for cross-platform clipboard support:

```python
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

def action_yank_selection(self):
    if self.selection:
        selected_text = self.selected_text
        if HAS_PYPERCLIP:
            pyperclip.copy(selected_text)
        else:
            logger.warning("pyperclip not available...")
```

**Yank Actions:**
- `y`: Copy currently selected text to clipboard
- `Y`: Copy entire current line to clipboard
- Logs warning if pyperclip not installed

4. **Mouse Selection**

Users can also select text with mouse and copy using OS shortcuts (Ctrl+C / Cmd+C).

### Content Display

**`update_content(resource)`**
- Accepts any Pydantic model with `raw_data` field
- Converts `raw_data` to formatted JSON
- Sets TextArea language to "json"
- Applies Monokai theme
- Makes TextArea read-only

**`clear_content()`**
- Clears display when no resource selected
- Shows empty JSON object: `{}`

**JSON Formatting:**
```python
import json
json_content = json.dumps(resource.raw_data, indent=2, default=str)
```
- Indentation: 2 spaces
- Non-serializable objects: Convert to string (`default=str`)

## StatusBar

**File:** `src/sequel/widgets/status_bar.py`

**Purpose:** Display application status, statistics, and keyboard shortcuts.

### Display Sections

Status bar text format:
```
Project: <name>  |  ⏳ <operation>  |  Cache: <hit_rate>% hit rate  |  <api_calls> API calls  |  Updated <time> ago  |  q: Quit | r: Refresh | ?: Help | ...
```

**Sections (left to right):**

1. **Project Info** (if set)
   - Format: `Project: <project_id>`
   - Updated via `set_project(project_name)`

2. **Current Operation** (if active)
   - Format: `⏳ <operation>` or `⏳ Loading...`
   - Updated via `set_loading(loading, operation)` or `set_operation(operation)`

3. **Cache Statistics** (if any requests made)
   - Format: `Cache: <percentage>% hit rate`
   - Calculated: `(hits / (hits + misses)) * 100`
   - Updated via `record_cache_hit()` and `record_cache_miss()`

4. **API Call Count** (if > 0)
   - Format: `<count> API calls`
   - Updated via `record_api_call()`

5. **Last Refresh Time** (if available)
   - Format: `Updated <N>s ago` (if < 60s) or `Updated <N>m ago` (if ≥ 60s)
   - Updated via `update_last_refresh()`

6. **Keyboard Shortcuts** (always shown)
   - Format: `q: Quit | r: Refresh | ?: Help | j/k/↑↓: Navigate | h/l/←→: Collapse/Expand | g/G: Top/Bottom`

### State Management

**Internal State:**
- `_project`: Current project ID
- `_loading`: Loading status (bool)
- `_current_operation`: Operation description (str)
- `_cache_hits`: Cache hit count (int)
- `_cache_misses`: Cache miss count (int)
- `_api_calls`: API call count (int)
- `_last_refresh`: Last refresh timestamp (datetime)

**Methods:**
- `set_project(project_name)`: Update current project
- `set_loading(loading, operation)`: Update loading status
- `set_operation(operation)`: Update operation description
- `record_cache_hit()`: Increment cache hits
- `record_cache_miss()`: Increment cache misses
- `record_api_call()`: Increment API calls
- `update_last_refresh()`: Set last refresh to now
- `reset_stats()`: Reset all statistics
- `_update_display()`: Rebuild and update display text

**Auto-Update:**
All public methods call `_update_display()` to immediately reflect changes.

### CSS Styling

```css
StatusBar {
    dock: bottom;
    height: 1;
    background: $primary;
    color: $text;
    padding: 0 1;
}
```

- Docked to bottom of screen
- Fixed height: 1 line
- Background: Primary theme color
- Horizontal padding: 1 character on each side

## ErrorModal

**File:** `src/sequel/widgets/error_modal.py`

**Purpose:** Modal dialog for displaying errors and help messages.

### Features

- Modal overlay (blocks interaction with background)
- Dismissible with Esc key
- Title and message display
- "OK" button to dismiss

### Usage

```python
# From SequelApp or Screen:
await self.show_error("Error Title", "Error message here")

# From help action:
await self.show_error("Help", help_text)
```

### CSS

```css
#error-dialog {
    width: 60;
    height: auto;
    background: $panel;
    border: thick $error;
    padding: 1 2;
}

#error-title {
    text-style: bold;
    color: $error;
    margin-bottom: 1;
}
```

## LoadingIndicator

**File:** `src/sequel/widgets/loading_indicator.py`

**Purpose:** Animated progress indicator for long operations.

**Features:**
- Indeterminate spinner
- Operation description text
- Used during async operations

**Note:** Currently integrated into status bar instead of standalone widget.

## Widget Communication

### Message Passing

Textual uses message passing for widget communication:

**TreeNodeHighlighted Event:**
```python
# ResourceTree emits (automatic Textual event):
ResourceTree.NodeHighlighted[ResourceTreeNode]

# MainScreen handles:
async def on_tree_node_highlighted(self, event):
    if event.node.data and event.node.data.resource_data:
        self.detail_pane.update_content(event.node.data.resource_data)
```

### Parent-Child Communication

**Parent → Child:**
```python
# MainScreen calls child methods directly:
await self.resource_tree.load_projects()
self.detail_pane.update_content(resource)
self.status_bar.set_loading(True, "Loading...")
```

**Child → Parent:**
```python
# Via Textual events (automatic):
# - NodeHighlighted
# - NodeExpanded
# - NodeCollapsed
```

## Reactive State

Textual widgets support reactive attributes that automatically update the UI when changed:

**Example (not currently used, but available):**
```python
from textual.reactive import reactive

class StatusBar(Static):
    loading = reactive(False)

    def watch_loading(self, value):
        # Called automatically when loading changes
        self._update_display()
```

## Adding a New Widget

To add a new widget:

1. **Create widget file** in `src/sequel/widgets/`
2. **Extend Textual widget** (Static, Container, TextArea, etc.)
3. **Define CSS** in widget class or screen
4. **Add to screen** in `compose()` or `on_mount()`
5. **Implement event handlers** if needed
6. **Add tests** in `tests/unit/widgets/`

**Example:**

```python
from textual.widgets import Static

class MyWidget(Static):
    CSS = """
    MyWidget {
        height: auto;
        background: $surface;
        padding: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.update("Widget content")

    def update_data(self, data):
        self.update(str(data))

# In MainScreen:
def compose(self) -> ComposeResult:
    self.my_widget = MyWidget()
    yield self.my_widget
```

## Testing Widgets

Widget tests use Textual's `App.run_test()` async context:

```python
import pytest
from textual.app import App

@pytest.mark.asyncio
async def test_widget():
    class TestApp(App):
        def compose(self):
            yield MyWidget()

    async with TestApp().run_test() as pilot:
        widget = pilot.app.query_one(MyWidget)
        assert widget is not None
        widget.update_data("test")
        assert "test" in widget.renderable
```

**Key concepts:**
- `run_test()`: Runs app in headless mode
- `pilot`: Test pilot for simulating user input
- `query_one(Widget)`: Find widget by type
- `press(key)`: Simulate key press
- `click(Widget)`: Simulate mouse click
