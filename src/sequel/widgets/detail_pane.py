"""Detail pane widget for displaying resource details."""

import json
from typing import Any

from rich.syntax import Syntax
from textual.widgets import Static

from sequel.models.base import BaseModel
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class DetailPane(Static):
    """Widget for displaying detailed information about a selected resource."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the detail pane."""
        super().__init__(*args, **kwargs)
        self.current_resource: BaseModel | None = None

    def update_content(self, resource: BaseModel | None) -> None:
        """Update the detail pane with new resource information.

        Args:
            resource: Resource model to display
        """
        self.current_resource = resource

        if resource is None:
            self.update("No resource selected")
            return

        try:
            # Create a formatted display of the resource
            content = self._format_resource(resource)
            self.update(content)

        except Exception as e:
            logger.error(f"Failed to format resource details: {e}")
            self.update(f"Error displaying resource: {e}")

    def _format_resource(self, resource: BaseModel) -> Syntax:
        """Format a resource as pretty-printed JSON.

        Args:
            resource: Resource to format

        Returns:
            Rich Syntax widget with JSON highlighting
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

        # Create syntax-highlighted JSON
        syntax = Syntax(
            json_str,
            "json",
            theme="monokai",
            line_numbers=True,
            word_wrap=False,
            code_width=None,
        )

        return syntax

    def clear_content(self) -> None:
        """Clear the detail pane."""
        self.current_resource = None
        self.update("No resource selected")
