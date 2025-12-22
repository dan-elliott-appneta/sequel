"""Main Textual application for Sequel."""

from typing import ClassVar

from textual.app import App
from textual.binding import Binding

from sequel import __version__
from sequel.commands import ThemeProvider
from sequel.config import get_config
from sequel.screens.main import MainScreen
from sequel.services.auth import AuthError, get_auth_manager
from sequel.utils.logging import get_logger
from sequel.widgets.error_modal import ErrorModal

logger = get_logger(__name__)


class SequelApp(App[None]):
    """Main Textual application for browsing GCP resources.

    Key bindings:
    - q: Quit application
    - r: Refresh current view
    - ctrl+p: Open command palette
    - ?: Show help
    """

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("ctrl+p", "command_palette", "Commands"),
        Binding("?", "help", "Help"),
    ]

    COMMAND_PROVIDERS: ClassVar = [ThemeProvider]

    CSS: ClassVar[str] = """
    Screen {
        background: $surface;
    }

    #error-dialog {
        width: 60;
        height: auto;
        background: $panel;
        border: thick $error;
        padding: 1 2;
    }

    #error-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #error-message {
        margin-bottom: 1;
    }

    #button-container {
        layout: horizontal;
        height: auto;
        align: center middle;
    }
    """

    def __init__(self, *args: any, **kwargs: any) -> None:  # type: ignore[valid-type]
        """Initialize the application."""
        super().__init__(*args, **kwargs)
        self.title = "Sequel - GCP Resource Browser"
        self.sub_title = f"v{__version__}"

        # Load theme from config
        config = get_config()
        self.theme = config.theme

    def watch_theme(self, theme: str) -> None:
        """Watch for theme changes and persist to config file.

        This is called automatically when app.theme changes, including when
        using Textual's built-in "set-theme" command.

        Args:
            theme: The new theme name
        """
        from sequel.config_file import update_config_value

        # Persist theme change to config file
        update_config_value("ui", "theme", theme)
        logger.debug(f"Theme changed to {theme} and persisted to config")

    async def on_mount(self) -> None:
        """Handle application mount event."""
        logger.info("Sequel application starting")

        try:
            # Initialize authentication
            logger.info("Initializing authentication...")
            await get_auth_manager()

            # Push main screen
            await self.push_screen(MainScreen())

        except AuthError as e:
            logger.error(f"Authentication failed: {e}")
            await self.show_error("Authentication Error", str(e))
            self.exit()

        except Exception as e:
            logger.error(f"Application initialization failed: {e}")
            await self.show_error("Initialization Error", str(e))
            self.exit()

    async def action_refresh(self) -> None:
        """Refresh the current view."""
        logger.info("Refresh action triggered")

        # Get current screen
        screen = self.screen

        if isinstance(screen, MainScreen):
            await screen.refresh_tree()

    async def action_help(self) -> None:
        """Show help modal."""
        help_text = """
        Keyboard Shortcuts:

        Tree Navigation:
          j / ↓       - Move down
          k / ↑       - Move up
          h / ←       - Collapse node or go to parent
          l / →       - Expand node or go to first child
          g           - Go to top
          G           - Go to bottom
          Enter       - Toggle expand/collapse

        Detail Pane (VIM mode):
          j / k       - Move down / up
          h / l       - Move left / right
          g / G       - Page up / Page down
          0 / $       - Line start / Line end
          y           - Yank (copy) selection
          Y           - Yank (copy) current line
          Mouse       - Select text to copy

        Actions:
          q           - Quit application
          r           - Refresh current view
          Ctrl+P      - Open command palette (themes)
          ?           - Show this help
          Esc         - Dismiss modal
        """

        await self.show_error("Help", help_text)

    async def show_error(self, title: str, message: str) -> None:
        """Show an error modal.

        Args:
            title: Error title
            message: Error message
        """
        await self.push_screen(ErrorModal(title, message))


def run_app() -> None:
    """Run the Sequel application."""
    app = SequelApp()
    app.run()
