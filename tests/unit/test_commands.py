"""Tests for command palette providers."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest
from textual.app import App

from sequel.commands import AVAILABLE_THEMES, ThemeProvider


class TestAvailableThemes:
    """Test the AVAILABLE_THEMES constant."""

    def test_available_themes_list(self) -> None:
        """Test AVAILABLE_THEMES contains expected themes."""
        assert isinstance(AVAILABLE_THEMES, list)
        assert len(AVAILABLE_THEMES) > 0

        # Check for some known themes
        assert "textual-dark" in AVAILABLE_THEMES
        assert "textual-light" in AVAILABLE_THEMES
        assert "catppuccin-mocha" in AVAILABLE_THEMES
        assert "nord" in AVAILABLE_THEMES
        assert "dracula" in AVAILABLE_THEMES

    def test_available_themes_sorted(self) -> None:
        """Test AVAILABLE_THEMES is sorted alphabetically."""
        sorted_themes = sorted(AVAILABLE_THEMES)
        assert sorted_themes == AVAILABLE_THEMES

    def test_available_themes_unique(self) -> None:
        """Test AVAILABLE_THEMES has no duplicates."""
        assert len(AVAILABLE_THEMES) == len(set(AVAILABLE_THEMES))


class TestThemeProvider:
    """Test the ThemeProvider command provider."""

    @pytest.mark.asyncio
    async def test_select_theme_updates_app_theme(self) -> None:
        """Test select_theme updates app theme."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Create a mock screen and app
            mock_app = MagicMock(spec=App)
            mock_app.theme = "textual-dark"
            mock_app.notify = MagicMock()

            mock_screen = MagicMock()
            mock_screen.app = mock_app

            provider = ThemeProvider(screen=mock_screen)

            # Select a theme
            with patch("sequel.commands.reset_config") as mock_reset:
                await provider.select_theme("nord")

            # Verify app theme was updated
            assert mock_app.theme == "nord"

            # Verify reset_config was called
            mock_reset.assert_called_once()

            # Verify notification was sent
            mock_app.notify.assert_called_once()
            call_args = mock_app.notify.call_args
            assert "nord" in call_args[0][0]

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    @pytest.mark.asyncio
    async def test_select_theme_sets_app_attribute(self) -> None:
        """Test select_theme sets the app.theme attribute."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Create a mock screen and app
            mock_app = MagicMock(spec=App)
            mock_app.theme = "textual-dark"
            mock_app.notify = MagicMock()

            mock_screen = MagicMock()
            mock_screen.app = mock_app

            provider = ThemeProvider(screen=mock_screen)

            # Select a theme
            with patch("sequel.commands.reset_config"):
                await provider.select_theme("catppuccin-mocha")

            # Verify app.theme was set (which triggers watch_theme in real app)
            assert mock_app.theme == "catppuccin-mocha"

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_theme_provider_instantiation(self) -> None:
        """Test ThemeProvider can be instantiated."""
        mock_screen = MagicMock()
        provider = ThemeProvider(screen=mock_screen)

        assert provider is not None
        assert hasattr(provider, "search")
        assert hasattr(provider, "select_theme")

    @pytest.mark.asyncio
    async def test_search_returns_matching_themes(self) -> None:
        """Test search method returns themes matching the query."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Create a mock screen and app
            mock_app = MagicMock(spec=App)
            mock_app.theme = "textual-dark"

            mock_screen = MagicMock()
            mock_screen.app = mock_app

            provider = ThemeProvider(screen=mock_screen)

            # Search for "dark" themes
            with patch("sequel.commands.get_config") as mock_get_config:
                mock_config = MagicMock()
                mock_config.theme = "textual-dark"
                mock_get_config.return_value = mock_config

                hits = []
                async for hit in provider.search("dark"):
                    hits.append(hit)

            # Should find themes with "dark" in the name
            assert len(hits) > 0
            # textual-dark and solarized-dark should be in results
            hit_texts = [str(hit.text) for hit in hits]
            assert any("textual-dark" in text.lower() for text in hit_texts)

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    @pytest.mark.asyncio
    async def test_search_marks_current_theme(self) -> None:
        """Test search method marks the current theme with (current) suffix."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Create a mock screen and app
            mock_app = MagicMock(spec=App)
            mock_app.theme = "nord"

            mock_screen = MagicMock()
            mock_screen.app = mock_app

            provider = ThemeProvider(screen=mock_screen)

            # Search for "nord"
            with patch("sequel.commands.get_config") as mock_get_config:
                mock_config = MagicMock()
                mock_config.theme = "nord"
                mock_get_config.return_value = mock_config

                hits = []
                async for hit in provider.search("nord"):
                    hits.append(hit)

            # Should find nord theme
            assert len(hits) == 1
            assert "current" in hits[0].help.lower()

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    @pytest.mark.asyncio
    async def test_search_no_matches(self) -> None:
        """Test search method returns no results for non-matching query."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Create a mock screen and app
            mock_app = MagicMock(spec=App)
            mock_app.theme = "textual-dark"

            mock_screen = MagicMock()
            mock_screen.app = mock_app

            provider = ThemeProvider(screen=mock_screen)

            # Search for something that doesn't match any theme
            with patch("sequel.commands.get_config") as mock_get_config:
                mock_config = MagicMock()
                mock_config.theme = "textual-dark"
                mock_get_config.return_value = mock_config

                hits = []
                async for hit in provider.search("xyznonexistent"):
                    hits.append(hit)

            # Should find no results
            assert len(hits) == 0

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)
