"""Detail pane widget for displaying resource details."""

import json
from typing import ClassVar

from textual.binding import Binding
from textual.widgets import TextArea

from sequel.models.base import BaseModel
from sequel.utils.logging import get_logger

try:
    import pyperclip  # type: ignore[import-untyped]

    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

logger = get_logger(__name__)


class DetailPane(TextArea):
    """Widget for displaying detailed information about a selected resource.

    This widget is scrollable and supports text selection for copying.
    VIM-style navigation and yanking supported.
    """

    BINDINGS: ClassVar = [
        # VIM navigation (when not in selection mode)
        Binding("j", "cursor_down", "Move down", show=False),
        Binding("k", "cursor_up", "Move up", show=False),
        Binding("h", "cursor_left", "Move left", show=False),
        Binding("l", "cursor_right", "Move right", show=False),
        Binding("g", "cursor_page_up", "Page up", show=False),
        Binding("G", "cursor_page_down", "Page down", show=False),
        Binding("0", "cursor_line_start", "Line start", show=False),
        Binding("$", "cursor_line_end", "Line end", show=False),
        # VIM yanking (copy)
        Binding("y", "yank_selection", "Yank (copy)", show=False),
        Binding("Y", "yank_line", "Yank line", show=False),
    ]

    def __init__(self) -> None:
        """Initialize the detail pane."""
        super().__init__(
            "",  # Initial empty text
            language="json",
            theme="dracula",  # Vibrant purple/pink syntax highlighting theme
            read_only=True,
            show_line_numbers=True,
            soft_wrap=False,
        )
        self.current_resource: BaseModel | None = None

    def update_content(self, resource: BaseModel | None) -> None:
        """Update the detail pane with new resource information.

        Args:
            resource: Resource model to display
        """
        self.current_resource = resource

        if resource is None:
            self.load_text("No resource selected")
            return

        try:
            # Create a formatted display of the resource
            content = self._format_resource(resource)
            # Use call_after_refresh to defer load_text and prevent UI blocking
            self.call_after_refresh(self.load_text, content)

        except Exception as e:
            logger.error(f"Failed to format resource details: {e}")
            self.load_text(f"Error displaying resource: {e}")

    def _format_resource(self, resource: BaseModel) -> str:
        """Format a resource as pretty-printed JSON.

        Args:
            resource: Resource to format

        Returns:
            Pretty-printed JSON string
        """
        # Get raw API response data if available, otherwise use model dict
        if resource.raw_data:
            data = resource.raw_data
        else:
            # Fallback to model dict if raw_data is empty
            data = resource.to_dict()
            # Remove raw_data from display if it's empty
            data.pop("raw_data", None)

        # Pretty-print JSON with 2-space indentation
        json_str = json.dumps(data, indent=2, sort_keys=True, default=str)

        return json_str

    def clear_content(self) -> None:
        """Clear the detail pane."""
        self.current_resource = None
        self.load_text("No resource selected")

    def action_yank_selection(self) -> None:
        """Yank (copy) the current selection to clipboard (VIM 'y' command)."""
        if self.selection:
            # Get the selected text
            selected_text = self.selected_text
            # Copy to system clipboard
            if HAS_PYPERCLIP:
                pyperclip.copy(selected_text)
                logger.debug(f"Yanked {len(selected_text)} characters to clipboard")
            else:
                logger.warning(
                    "pyperclip not available. Install with: pip install pyperclip"
                )
                logger.info(f"Would have yanked: {selected_text[:50]}...")

    def action_yank_line(self) -> None:
        """Yank (copy) the current line to clipboard (VIM 'Y' command)."""
        # Get the current line
        cursor_row, _ = self.cursor_location
        text_lines = self.text.split("\n")

        if 0 <= cursor_row < len(text_lines):
            line_text = text_lines[cursor_row]
            if HAS_PYPERCLIP:
                pyperclip.copy(line_text)
                logger.debug(f"Yanked line {cursor_row + 1} to clipboard")
            else:
                logger.warning(
                    "pyperclip not available. Install with: pip install pyperclip"
                )
                logger.info(f"Would have yanked line: {line_text[:50]}...")
