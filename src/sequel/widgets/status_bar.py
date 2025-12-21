"""Status bar widget for displaying application status."""

from datetime import datetime
from typing import Any

from textual.widgets import Static


class StatusBar(Static):
    """Widget for displaying status information and keyboard shortcuts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the status bar."""
        super().__init__(*args, **kwargs)
        self._project: str | None = None
        self._loading: bool = False
        self._current_operation: str | None = None
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._api_calls: int = 0
        self._last_refresh: datetime | None = None

    def set_project(self, project_name: str | None) -> None:
        """Set the currently selected project.

        Args:
            project_name: Name of the selected project
        """
        self._project = project_name
        self._update_display()

    def set_loading(self, loading: bool, operation: str | None = None) -> None:
        """Set loading status.

        Args:
            loading: Whether resources are currently loading
            operation: Description of current operation
        """
        self._loading = loading
        self._current_operation = operation if loading else None
        self._update_display()

    def set_operation(self, operation: str | None) -> None:
        """Set current operation description.

        Args:
            operation: Description of current operation (or None to clear)
        """
        self._current_operation = operation
        self._update_display()

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self._cache_hits += 1
        self._update_display()

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self._cache_misses += 1
        self._update_display()

    def record_api_call(self) -> None:
        """Record an API call."""
        self._api_calls += 1
        self._update_display()

    def update_last_refresh(self) -> None:
        """Update the last refresh timestamp."""
        self._last_refresh = datetime.now()
        self._update_display()

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._cache_hits = 0
        self._cache_misses = 0
        self._api_calls = 0
        self._last_refresh = None
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar display."""
        parts = []

        # Add project info
        if self._project:
            parts.append(f"Project: {self._project}")

        # Add current operation or loading indicator
        if self._current_operation:
            parts.append(f"⏳ {self._current_operation}")
        elif self._loading:
            parts.append("⏳ Loading...")

        # Add cache stats
        total_cache_requests = self._cache_hits + self._cache_misses
        if total_cache_requests > 0:
            hit_rate = (self._cache_hits / total_cache_requests) * 100
            parts.append(f"Cache: {hit_rate:.0f}% hit rate")

        # Add API call count
        if self._api_calls > 0:
            parts.append(f"{self._api_calls} API calls")

        # Add last refresh time
        if self._last_refresh:
            elapsed = datetime.now() - self._last_refresh
            if elapsed.total_seconds() < 60:
                time_str = f"{int(elapsed.total_seconds())}s ago"
            else:
                time_str = f"{int(elapsed.total_seconds() / 60)}m ago"
            parts.append(f"Updated {time_str}")

        # Add keyboard shortcuts with VIM bindings
        shortcuts = [
            "q: Quit",
            "r: Refresh",
            "?: Help",
            "j/k/↑↓: Navigate",
            "h/l/←→: Collapse/Expand",
            "g/G: Top/Bottom",
        ]
        parts.append(" | ".join(shortcuts))

        # Combine all parts
        status_text = "  |  ".join(parts) if parts else "Ready"
        self.update(status_text)
