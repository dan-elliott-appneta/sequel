"""Detail pane widget for displaying resource details."""

from typing import Any

from rich.table import Table
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

    def _format_resource(self, resource: BaseModel) -> Table:
        """Format a resource as a Rich table.

        Args:
            resource: Resource to format

        Returns:
            Rich Table with resource details
        """
        # Create table
        table = Table(
            title=f"{resource.__class__.__name__}: {resource.name}",
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Property", style="bold")
        table.add_column("Value")

        # Get resource data
        data = resource.to_dict()

        # Add rows for each property
        for key, value in sorted(data.items()):
            if value is None:
                continue

            # Format value
            formatted_value = self._format_value(value)
            table.add_row(key, formatted_value)

        return table

    def _format_value(self, value: Any) -> str:
        """Format a value for display.

        Args:
            value: Value to format

        Returns:
            Formatted string
        """
        if isinstance(value, dict):
            # Format dict as key=value pairs
            if not value:
                return "(empty)"
            items = [f"{k}={v}" for k, v in value.items()]
            return ", ".join(items)

        elif isinstance(value, list):
            # Format list
            if not value:
                return "(empty)"
            return ", ".join(str(item) for item in value)

        elif isinstance(value, bool):
            # Format boolean with symbols
            return "✓" if value else "✗"

        else:
            return str(value)

    def clear_content(self) -> None:
        """Clear the detail pane."""
        self.current_resource = None
        self.update("No resource selected")
