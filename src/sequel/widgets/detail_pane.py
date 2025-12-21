"""Detail pane widget for displaying resource details."""

import json

from textual.widgets import TextArea

from sequel.models.base import BaseModel
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class DetailPane(TextArea):
    """Widget for displaying detailed information about a selected resource.

    This widget is scrollable and supports text selection for copying.
    """

    def __init__(self) -> None:
        """Initialize the detail pane."""
        super().__init__(
            "",  # Initial empty text
            language="json",
            theme="dracula",
            read_only=True,
            show_line_numbers=True,
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
            self.load_text(content)

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
