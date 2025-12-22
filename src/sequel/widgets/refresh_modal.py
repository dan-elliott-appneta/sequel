"""Refresh confirmation modal widget."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class RefreshModal(ModalScreen[str]):
    """Modal dialog to confirm refresh scope.

    Allows user to choose between:
    - Refreshing all projects and resources
    - Refreshing only currently visible resources
    - Canceling the refresh
    """

    DEFAULT_CSS = """
    RefreshModal {
        align: center middle;
    }

    RefreshModal > Vertical {
        background: $surface;
        border: thick $primary;
        padding: 2;
        width: 60;
        height: auto;
    }

    RefreshModal Label {
        width: 100%;
        text-align: center;
        margin-bottom: 2;
    }

    RefreshModal Button {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the refresh modal."""
        with Vertical():
            yield Label("[bold]What do you want to refresh?[/bold]")
            yield Button(
                "All projects and resources",
                id="refresh-all",
                variant="primary",
            )
            yield Button(
                "Currently visible resources only",
                id="refresh-visible",
                variant="default",
            )
            yield Button("Cancel", id="cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button pressed event
        """
        if event.button.id == "refresh-all":
            self.dismiss("all")
        elif event.button.id == "refresh-visible":
            self.dismiss("visible")
        else:
            self.dismiss("cancel")
