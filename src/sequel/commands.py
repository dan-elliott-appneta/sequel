"""Command palette providers for Sequel."""

from textual.command import Hit, Hits, Provider

from sequel.config import get_config, reset_config

# List of available Textual themes (built-in themes from Textual framework)
AVAILABLE_THEMES = [
    "catppuccin-frappe",
    "catppuccin-latte",
    "catppuccin-macchiato",
    "catppuccin-mocha",
    "dracula",
    "gruvbox",
    "monokai",
    "nord",
    "solarized-dark",
    "solarized-light",
    "textual-ansi",
    "textual-dark",
    "textual-light",
    "tokyo-night",
]


class ThemeProvider(Provider):
    """Command provider for selecting Textual themes."""

    async def search(self, query: str) -> Hits:
        """Search for theme commands matching the query.

        Args:
            query: User's search query

        Yields:
            Theme selection commands
        """
        matcher = self.matcher(query)

        for theme in AVAILABLE_THEMES:
            # Create searchable text: "theme: <theme-name>"
            search_text = f"theme: {theme}"
            score = matcher.match(search_text)

            if score > 0:
                # Check if this is the current theme
                current_theme = get_config().theme
                is_current = theme == current_theme
                suffix = " (current)" if is_current else ""

                yield Hit(
                    score,
                    matcher.highlight(search_text),
                    lambda t=theme: self.select_theme(t),
                    help=f"Switch to {theme} theme{suffix}",
                )

    async def select_theme(self, theme: str) -> None:
        """Select a theme and apply it.

        The theme will be automatically persisted to config file via
        the app's watch_theme() method.

        Args:
            theme: Theme name to select
        """
        # Apply theme to app (this triggers watch_theme which saves to config)
        self.app.theme = theme

        # Reset config cache so it reloads from file
        reset_config()

        # Notify user
        self.app.notify(f"Theme changed to: {theme}", title="Theme Updated")
