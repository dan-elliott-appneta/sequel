"""Error modal widget for displaying errors."""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ErrorModal(ModalScreen[bool]):
    """Modal screen for displaying error messages."""

    def __init__(
        self,
        title: str,
        message: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the error modal.

        Args:
            title: Error title
            message: Error message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.title_text = title
        self.message_text = message

    def compose(self) -> ComposeResult:
        """Compose the modal layout.

        Yields:
            Widget components
        """
        yield Container(
            Static(self.title_text, id="error-title"),
            Static(self.message_text, id="error-message"),
            Container(
                Button("OK", variant="primary", id="ok-button"),
                id="button-container",
            ),
            id="error-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button press event
        """
        self.dismiss(True)

    def on_key(self, event: Any) -> None:
        """Handle key press.

        Args:
            event: Key event
        """
        if event.key in ("escape", "enter"):
            self.dismiss(True)
