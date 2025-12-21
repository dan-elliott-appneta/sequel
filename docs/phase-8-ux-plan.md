# Phase 8: Error Handling & UX Polish

## Overview

This phase enhances error recovery mechanisms and polishes the user experience with progress indicators, toast notifications, and improved status information.

**Branch:** `phase-8-ux`

**Current State:**
- Version: 0.1.0 (Alpha)
- Basic error handling implemented
- Ready for UX enhancements

## Objectives

- Enhanced error recovery mechanisms
- Progress indicators for long operations
- Improved status bar with live information
- Toast notifications for non-blocking errors
- Keyboard shortcut hints
- Resource counts in tree nodes
- VIM bindings for keyboard navigation (j/k/h/l/g/G)
- Enhanced tree navigation with left/right arrow keys for expand/collapse

---

## Detailed Tasks

### 8.1 Enhanced Error Recovery

**Files to modify:**
- `src/sequel/services/base.py` - Add quota wait, credential refresh
- `src/sequel/widgets/error_modal.py` - Add recovery actions

**New Features:**

**Quota Wait with Countdown:**
```python
# When QuotaExceededError occurs:
if "rateLimitExceeded" in error_message:
    wait_seconds = extract_retry_after(error_message)  # e.g., 60
    # Show modal with countdown: "Quota exceeded. Retrying in 59s..."
    await asyncio.sleep(wait_seconds)
    # Retry operation
```

**Credential Refresh:**
```python
# When AuthError occurs:
try:
    auth_manager.credentials.refresh()
except Exception:
    # Show error modal with help:
    # "Credentials expired. Please run: gcloud auth application-default login"
```

**Partial Failure Handling:**
```python
# If some resources fail to load, show what succeeded:
# "Loaded 4 of 6 resource types. Failed: Cloud SQL (permission denied), GKE (API not enabled)"
```

**Testing:**
- Mock quota errors and verify wait/retry
- Mock credential expiry and verify refresh
- Test partial failure display

---

### 8.2 Progress Indicators

**New file:** `src/sequel/widgets/progress_indicator.py`

**Features:**
- Indeterminate spinner for unknown duration
- Progress bar for known steps
- Operation description (e.g., "Loading projects...")
- Cancel button for long operations

**Integration points:**
- Project loading
- Resource tree expansion
- Refresh operations

**Testing:**
- Test progress updates
- Test cancellation
- Verify UI doesn't block

---

### 8.3 Toast Notification System

**New file:** `src/sequel/widgets/toast.py`

**Use cases:**
- Cache cleared (non-modal info)
- Resource refreshed (success)
- API call failed (warning, recoverable)
- Config saved (success)

**Features:**
- Auto-dismiss after 3 seconds
- Stack multiple toasts
- 3 types: info, success, warning
- Non-blocking

**Testing:**
- Test auto-dismiss timing
- Test multiple toasts stacking
- Verify doesn't block interaction

---

### 8.4 Status Bar Enhancements

**Files to modify:**
- `src/sequel/widgets/status_bar.py` - Add live stats

**New Information:**
- Current operation (e.g., "Loading GKE clusters...")
- Cache hit rate (e.g., "Cache: 73% hit rate")
- API call count (e.g., "12 API calls")
- Last refresh time (e.g., "Updated 2m ago")

**Testing:**
- Verify stats update in real-time
- Test formatting with edge cases

---

### 8.5 UX Improvements

**Files to modify:**
- `src/sequel/widgets/resource_tree.py` - Add resource counts
- `src/sequel/app.py` - Add keyboard hint footer

**Resource Counts:**
```
📁 My Project (12 resources)
  ├─ 🌐 Cloud DNS (2 zones)
  ├─ ☁️  Cloud SQL (1 instance)
  └─ 💻 Instance Groups (3 groups)
```

**Keyboard Hints:**
```
[Footer] q: Quit | r: Refresh | Ctrl+P: Commands | ?: Help | ↑↓: Navigate | Enter: Expand
```

**Breadcrumb Navigation:**
```
[Header] Projects > my-project > Cloud DNS > example.com.
```

**Testing:**
- Verify counts update dynamically
- Test breadcrumb navigation
- Verify keyboard hints accuracy

---

### 8.6 VIM Bindings & Enhanced Tree Navigation

**Files to modify:**
- `src/sequel/app.py` - Add VIM keybindings
- `src/sequel/widgets/resource_tree.py` - Add expand/collapse on arrow keys
- `src/sequel/screens/main.py` - Update key handling

**New Features:**

**VIM Navigation Bindings:**
```python
# Tree navigation (VIM-style)
BINDINGS = [
    ("j", "cursor_down", "Move down"),
    ("k", "cursor_up", "Move up"),
    ("h", "collapse_node", "Collapse node / Go to parent"),
    ("l", "expand_node", "Expand node / Go to child"),
    ("g", "cursor_top", "Go to top"),
    ("G", "cursor_bottom", "Go to bottom"),
]
```

**Arrow Key Tree Expansion:**
```python
# Enhanced arrow key behavior for tree
# Current behavior: Up/Down navigate, Enter toggles expand/collapse
# New behavior:
#   - Up/Down: Navigate (unchanged)
#   - Left: Collapse current node OR move to parent if already collapsed
#   - Right: Expand current node OR move to first child if already expanded
#   - Enter: Toggle expand/collapse (unchanged for compatibility)
```

**Implementation Details:**

1. **Left Arrow / 'h' Behavior:**
   ```python
   async def action_collapse_node(self) -> None:
       """Collapse current node or move to parent."""
       node = self.resource_tree.cursor_node
       if node and node.is_expanded:
           node.collapse()
       elif node and node.parent:
           self.resource_tree.select_node(node.parent)
   ```

2. **Right Arrow / 'l' Behavior:**
   ```python
   async def action_expand_node(self) -> None:
       """Expand current node or move to first child."""
       node = self.resource_tree.cursor_node
       if node and not node.is_expanded and node.allow_expand:
           await node.expand()
       elif node and node.is_expanded and node.children:
           self.resource_tree.select_node(node.children[0])
   ```

3. **Top/Bottom Navigation:**
   ```python
   async def action_cursor_top(self) -> None:
       """Move cursor to first tree node."""
       if self.resource_tree.root.children:
           self.resource_tree.select_node(self.resource_tree.root.children[0])

   async def action_cursor_bottom(self) -> None:
       """Move cursor to last visible tree node."""
       # Find last visible node in tree
       last_node = self.resource_tree.get_last_visible_node()
       if last_node:
           self.resource_tree.select_node(last_node)
   ```

**Keybinding Configuration:**
```python
# In app.py or main.py
BINDINGS = [
    # VIM-style navigation
    Binding("j", "cursor_down", "Move down", show=False),
    Binding("k", "cursor_up", "Move up", show=False),
    Binding("h", "collapse_node", "Collapse/Parent", show=False),
    Binding("l", "expand_node", "Expand/Child", show=False),
    Binding("g", "cursor_top", "Go to top", show=False),
    Binding("G", "cursor_bottom", "Go to bottom", show=False),

    # Arrow keys for tree navigation
    Binding("left", "collapse_node", "Collapse/Parent", show=False),
    Binding("right", "expand_node", "Expand/Child", show=False),

    # Existing bindings
    Binding("q", "quit", "Quit"),
    Binding("r", "refresh", "Refresh"),
    Binding("ctrl+p", "command_palette", "Commands"),
    Binding("question_mark", "help", "Help"),
]
```

**Updated Keyboard Hints:**
```
[Footer] q: Quit | r: Refresh | j/k/↑/↓: Navigate | h/l/←/→: Collapse/Expand | g/G: Top/Bottom | ?: Help
```

**Testing:**
- Test VIM navigation (j, k, h, l, g, G)
- Test arrow key expand/collapse (←, →)
- Test edge cases: already collapsed, already expanded, no children, root node
- Test that Enter still works for toggle (backwards compatibility)
- Verify keyboard hints updated
- Test navigation with large trees (1000+ nodes)

**Benefits:**
- VIM users get familiar navigation without configuration
- Arrow key expand/collapse is more intuitive (matches file browsers)
- Faster navigation with g/G for jumping to top/bottom
- Consistent with common TUI applications (lazygit, ranger, etc.)

---

## Success Criteria

- Users can recover from 90% of errors without restarting
- Progress shown for all operations > 1 second
- Toasts appear for all non-critical events
- Status bar provides useful context
- Keyboard hints reduce support questions
- VIM bindings work seamlessly (j/k/h/l/g/G)
- Arrow keys collapse/expand nodes intuitively
- Navigation is fast and responsive with large trees (1000+ nodes)

---

## Related Documentation

- [Phase 7: Performance Optimization](phase-7-performance-plan.md)
- [Phase 9: Testing & Documentation](phase-9-testing-docs-plan.md)
- [Phase 10: Packaging & Release](phase-10-release-plan.md)
