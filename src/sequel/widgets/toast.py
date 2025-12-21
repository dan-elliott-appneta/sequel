"""Toast notification widget for non-blocking messages."""

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.timer import Timer


class Toast(Static):
    """A toast notification that auto-dismisses after a delay.

    Toast types:
    - info: Informational message (blue)
    - success: Success message (green)
    - warning: Warning message (yellow)
    """

    DEFAULT_CLASSES = "toast"

    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        duration: float = 3.0,
        *args: any,  # type: ignore[valid-type]
        **kwargs: any,  # type: ignore[valid-type]
    ) -> None:
        """Initialize the toast.

        Args:
            message: Message to display
            toast_type: Type of toast (info, success, warning)
            duration: Duration in seconds before auto-dismiss
            *args: Positional arguments for Static
            **kwargs: Keyword arguments for Static
        """
        super().__init__(*args, **kwargs)
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        self._timer: Timer | None = None

    def on_mount(self) -> None:
        """Handle mount event and start auto-dismiss timer."""
        # Add type-specific class
        self.add_class(f"toast-{self.toast_type}")

        # Set message
        self.update(self.message)

        # Start auto-dismiss timer
        if self.duration > 0:
            self._timer = self.set_timer(self.duration, self._auto_dismiss)

    def _auto_dismiss(self) -> None:
        """Auto-dismiss the toast."""
        self.remove()


class ToastContainer(Container):
    """Container for stacking multiple toast notifications."""

    DEFAULT_CLASSES = "toast-container"

    CSS: ClassVar[str] = """
    ToastContainer {
        width: 100%;
        height: 100%;
        overlay: screen;
        align: center top;
        content-align: center top;
        layout: vertical;
    }

    .toast {
        width: auto;
        height: auto;
        min-width: 40;
        max-width: 80;
        padding: 1 2;
        margin: 1 0;
        border: tall $primary;
        background: $panel;
        color: $text;
        text-align: center;
    }

    .toast-info {
        border: tall $info;
    }

    .toast-success {
        border: tall $success;
    }

    .toast-warning {
        border: tall $warning;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the container (initially empty)."""
        # Container starts empty, toasts are added dynamically
        yield from []

    def show_toast(
        self,
        message: str,
        toast_type: str = "info",
        duration: float = 3.0,
    ) -> None:
        """Show a toast notification.

        Args:
            message: Message to display
            toast_type: Type of toast (info, success, warning)
            duration: Duration in seconds before auto-dismiss
        """
        toast = Toast(message, toast_type, duration)
        self.mount(toast)
