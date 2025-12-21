"""Loading indicator widget."""

from typing import Any

from textual.widgets import Static


class LoadingIndicator(Static):
    """Widget for displaying a loading spinner during async operations."""

    def __init__(self, message: str = "Loading...", *args: Any, **kwargs: Any) -> None:
        """Initialize the loading indicator.

        Args:
            message: Message to display
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.message = message
        self.update(f"⏳ {self.message}")

    def set_message(self, message: str) -> None:
        """Update the loading message.

        Args:
            message: New message to display
        """
        self.message = message
        self.update(f"⏳ {self.message}")
