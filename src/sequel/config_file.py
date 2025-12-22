"""Configuration file management for Sequel.

This module handles loading and saving user configuration from ~/.config/sequel/config.json
"""

import json
import os
from pathlib import Path
from typing import Any


def get_config_dir() -> Path:
    """Get the Sequel configuration directory.

    Returns:
        Path to config directory (~/.config/sequel or SEQUEL_CONFIG_DIR)
    """
    config_dir = os.getenv("SEQUEL_CONFIG_DIR")
    if config_dir:
        return Path(config_dir)

    # Use XDG_CONFIG_HOME if set, otherwise ~/.config
    xdg_config = os.getenv("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "sequel"

    return Path.home() / ".config" / "sequel"


def get_config_file() -> Path:
    """Get the path to the config file.

    Returns:
        Path to config.json
    """
    return get_config_dir() / "config.json"


def get_log_file_path() -> Path:
    """Get the default path to the log file.

    Returns:
        Path to sequel.log in the config directory
    """
    return get_config_dir() / "sequel.log"


def load_config_file() -> dict[str, Any]:
    """Load configuration from config file.

    Returns:
        Dict with configuration values (empty dict if file doesn't exist)
    """
    config_file = get_config_file()

    if not config_file.exists():
        return {}

    try:
        with open(config_file) as f:
            data = json.load(f)
            # Ensure we return a dict, even if JSON contains something else
            return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Warning: Failed to load config file {config_file}: {e}")
        return {}


def save_config_file(config: dict[str, Any]) -> None:
    """Save configuration to config file.

    Args:
        config: Configuration dict to save
    """
    config_file = get_config_file()

    # Create config directory if it doesn't exist
    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save config file {config_file}: {e}")


def get_default_config() -> dict[str, Any]:
    """Get default configuration values.

    Returns:
        Dict with default configuration
    """
    return {
        "ui": {
            "theme": "textual-dark",
        },
        "filters": {
            "project_regex": "",
            "dns_zone_filter": "",
        },
        "logging": {
            "log_file": str(get_log_file_path()),
            "log_level": "INFO",
        },
    }


def update_config_value(section: str, key: str, value: Any) -> None:
    """Update a single configuration value and save to file.

    Args:
        section: Config section (e.g., "ui", "filters")
        key: Config key within section
        value: Value to set
    """
    config = load_config_file()

    # Ensure section exists
    if section not in config:
        config[section] = {}

    config[section][key] = value
    save_config_file(config)
