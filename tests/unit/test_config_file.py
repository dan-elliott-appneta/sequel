"""Tests for configuration file management."""

import json
import os
import tempfile
from pathlib import Path

from sequel.config_file import (
    get_config_dir,
    get_config_file,
    get_default_config,
    load_config_file,
    save_config_file,
    update_config_value,
)


class TestConfigFileHelpers:
    """Test configuration file helper functions."""

    def test_get_config_dir_default(self) -> None:
        """Test get_config_dir returns default path."""
        # Clear environment variables
        os.environ.pop("SEQUEL_CONFIG_DIR", None)
        os.environ.pop("XDG_CONFIG_HOME", None)

        config_dir = get_config_dir()
        expected = Path.home() / ".config" / "sequel"

        assert config_dir == expected

    def test_get_config_dir_xdg(self) -> None:
        """Test get_config_dir respects XDG_CONFIG_HOME."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = tmpdir
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

            config_dir = get_config_dir()
            expected = Path(tmpdir) / "sequel"

            assert config_dir == expected

            # Cleanup
            os.environ.pop("XDG_CONFIG_HOME", None)

    def test_get_config_dir_sequel_override(self) -> None:
        """Test get_config_dir respects SEQUEL_CONFIG_DIR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir
            os.environ.pop("XDG_CONFIG_HOME", None)

            config_dir = get_config_dir()
            expected = Path(tmpdir)

            assert config_dir == expected

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_get_config_file(self) -> None:
        """Test get_config_file returns correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            config_file = get_config_file()
            expected = Path(tmpdir) / "config.json"

            assert config_file == expected

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_get_default_config(self) -> None:
        """Test get_default_config returns expected structure."""
        config = get_default_config()

        assert isinstance(config, dict)
        assert "ui" in config
        assert "filters" in config
        assert config["ui"]["theme"] == "textual-dark"
        assert config["filters"]["project_regex"] == r"^s[d|v|p]ap[n|nc]gl.*$"


class TestConfigFileOperations:
    """Test configuration file read/write operations."""

    def test_load_config_file_nonexistent(self) -> None:
        """Test load_config_file returns empty dict when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            config = load_config_file()

            assert config == {}

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_save_and_load_config_file(self) -> None:
        """Test saving and loading config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Save config
            test_config = {
                "ui": {"theme": "nord"},
                "filters": {"project_regex": r"^test-.*$"},
            }
            save_config_file(test_config)

            # Verify file exists
            config_file = get_config_file()
            assert config_file.exists()

            # Load config
            loaded_config = load_config_file()

            assert loaded_config == test_config
            assert loaded_config["ui"]["theme"] == "nord"
            assert loaded_config["filters"]["project_regex"] == r"^test-.*$"

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_save_config_creates_directory(self) -> None:
        """Test save_config_file creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "does_not_exist"
            os.environ["SEQUEL_CONFIG_DIR"] = str(config_dir)

            # Directory should not exist
            assert not config_dir.exists()

            # Save config
            test_config = {"ui": {"theme": "dracula"}}
            save_config_file(test_config)

            # Directory should now exist
            assert config_dir.exists()

            # Config file should exist
            config_file = get_config_file()
            assert config_file.exists()

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_save_config_file_valid_json(self) -> None:
        """Test saved config file is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            test_config = {
                "ui": {"theme": "catppuccin-mocha"},
                "filters": {"project_regex": r".*"},
            }
            save_config_file(test_config)

            # Read file directly and parse as JSON
            config_file = get_config_file()
            with open(config_file) as f:
                loaded = json.load(f)

            assert loaded == test_config

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_load_config_file_invalid_json(self) -> None:
        """Test load_config_file handles invalid JSON gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Create invalid JSON file
            config_file = get_config_file()
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w") as f:
                f.write("{invalid json}")

            # Should return empty dict
            config = load_config_file()
            assert config == {}

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_update_config_value_new_section(self) -> None:
        """Test update_config_value creates new section if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Update value in non-existent section
            update_config_value("new_section", "new_key", "new_value")

            # Load config
            config = load_config_file()

            assert "new_section" in config
            assert config["new_section"]["new_key"] == "new_value"

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_update_config_value_existing_section(self) -> None:
        """Test update_config_value updates existing section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Save initial config
            initial_config = {
                "ui": {"theme": "textual-dark", "other": "value"},
                "filters": {"project_regex": r"^s.*$"},
            }
            save_config_file(initial_config)

            # Update existing value
            update_config_value("ui", "theme", "nord")

            # Load config
            config = load_config_file()

            assert config["ui"]["theme"] == "nord"
            assert config["ui"]["other"] == "value"  # Other values preserved
            assert config["filters"]["project_regex"] == r"^s.*$"  # Other sections preserved

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_update_config_value_adds_new_key(self) -> None:
        """Test update_config_value adds new key to existing section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            # Save initial config
            initial_config = {"ui": {"theme": "textual-dark"}}
            save_config_file(initial_config)

            # Add new key
            update_config_value("ui", "new_key", "new_value")

            # Load config
            config = load_config_file()

            assert config["ui"]["theme"] == "textual-dark"
            assert config["ui"]["new_key"] == "new_value"

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)

    def test_save_config_with_indent(self) -> None:
        """Test saved config file is formatted with indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["SEQUEL_CONFIG_DIR"] = tmpdir

            test_config = {"ui": {"theme": "nord"}}
            save_config_file(test_config)

            # Read file content
            config_file = get_config_file()
            with open(config_file) as f:
                content = f.read()

            # Should have indentation (contains newlines and spaces)
            assert "\n" in content
            assert "  " in content

            # Cleanup
            os.environ.pop("SEQUEL_CONFIG_DIR", None)
