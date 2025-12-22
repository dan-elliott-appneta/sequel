"""Loading progress indicator widget."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar


class LoadingProgress(Vertical):
    """Progress indicator for resource loading.

    Displays a progress bar and status text during initial load and refresh operations.
    """

    # Reactive attributes for UI updates
    status_text: reactive[str] = reactive("Loading...", init=False)
    progress_text: reactive[str] = reactive("", init=False)
    progress_value: reactive[float] = reactive(0.0, init=False)

    DEFAULT_CSS = """
    LoadingProgress {
        layout: vertical;
        align: center middle;
        background: $surface;
        border: thick $primary;
        padding: 2;
        width: 60;
        height: auto;
    }

    LoadingProgress Label {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }

    LoadingProgress ProgressBar {
        width: 100%;
    }
    """

    def __init__(self) -> None:
        """Initialize the loading progress widget."""
        super().__init__()
        self.status_label: Label | None = None
        self.progress_label: Label | None = None
        self.progress_bar: ProgressBar | None = None

    def compose(self) -> ComposeResult:
        """Compose the loading progress widget."""
        self.status_label = Label(self.status_text, id="status-label")
        self.progress_label = Label(self.progress_text, id="progress-label")
        self.progress_bar = ProgressBar(total=100, show_eta=False, id="progress-bar")

        yield self.status_label
        yield self.progress_label
        yield self.progress_bar

    def watch_status_text(self, new_value: str) -> None:
        """React to status text changes."""
        if self.status_label:
            self.status_label.update(f"[bold]{new_value}[/bold]")

    def watch_progress_text(self, new_value: str) -> None:
        """React to progress text changes."""
        if self.progress_label:
            self.progress_label.update(new_value)

    def watch_progress_value(self, new_value: float) -> None:
        """React to progress value changes."""
        if self.progress_bar:
            self.progress_bar.update(progress=new_value)

    def update_progress(
        self, current: int, total: int, message: str = "Loading resources..."
    ) -> None:
        """Update progress indicator.

        Args:
            current: Number of items completed
            total: Total number of items
            message: Status message to display
        """
        percentage = int((current / total) * 100) if total > 0 else 0

        # Update reactive attributes (triggers UI refresh)
        self.status_text = message
        self.progress_text = f"Progress: {current}/{total} ({percentage}%)"
        self.progress_value = float(percentage)

    def show_loading(self, message: str = "Loading resources...") -> None:
        """Show the progress indicator.

        Args:
            message: Initial status message
        """
        self.status_text = message
        self.progress_text = "Initializing..."
        self.progress_value = 0.0
        self.display = True

    def hide_loading(self) -> None:
        """Hide the progress indicator."""
        self.display = False
