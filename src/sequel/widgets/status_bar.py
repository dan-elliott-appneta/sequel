"""Status bar widget for displaying application status."""

from typing import Any

from textual.widgets import Static


class StatusBar(Static):
    """Widget for displaying status information and keyboard shortcuts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the status bar."""
        super().__init__(*args, **kwargs)
        self._project: str | None = None
        self._loading: bool = False

    def set_project(self, project_name: str | None) -> None:
        """Set the currently selected project.

        Args:
            project_name: Name of the selected project
        """
        self._project = project_name
        self._update_display()

    def set_loading(self, loading: bool) -> None:
        """Set loading status.

        Args:
            loading: Whether resources are currently loading
        """
        self._loading = loading
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar display."""
        parts = []

        # Add project info
        if self._project:
            parts.append(f"Project: {self._project}")

        # Add loading indicator
        if self._loading:
            parts.append("⏳ Loading...")

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
