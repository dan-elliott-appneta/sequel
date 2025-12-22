"""Configuration management for Sequel.

This module provides centralized configuration loaded from config file and environment variables.
Config file (~/.config/sequel/config.toml) takes precedence over environment variables.
"""

import os
from dataclasses import dataclass

from sequel.config_file import get_default_config, load_config_file
from sequel.utils.regex_validator import RegexValidationError, validate_regex


@dataclass
class Config:
    """Application configuration.

    All settings can be overridden via environment variables with the
    SEQUEL_ prefix (e.g., SEQUEL_API_TIMEOUT).
    """

    # API Configuration
    api_timeout: int = 30  # seconds
    api_max_retries: int = 3
    api_retry_delay: float = 1.0  # seconds
    api_retry_backoff: float = 2.0  # exponential backoff multiplier

    # Cache Configuration
    cache_enabled: bool = True
    cache_ttl_projects: int = 600  # 10 minutes
    cache_ttl_resources: int = 300  # 5 minutes

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str | None = None
    enable_credential_scrubbing: bool = True

    # Google Cloud Configuration
    gcloud_project_id: str | None = None
    gcloud_quota_wait_time: int = 60  # seconds to wait on quota errors

    # Project Filtering
    project_filter_regex: str | None = None  # Filter projects by regex (None = show all)

    # DNS Zone Filtering
    dns_zone_filter: str | None = None  # Only show DNS zones containing this string (None = show all)

    # UI Configuration
    theme: str = "textual-dark"  # Textual theme name

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables and config file.

        Configuration precedence (highest to lowest):
            1. Environment variables
            2. Config file (~/.config/sequel/config.json)
            3. Default values

        Environment variables:
            SEQUEL_API_TIMEOUT: API request timeout in seconds
            SEQUEL_API_MAX_RETRIES: Maximum number of retry attempts
            SEQUEL_API_RETRY_DELAY: Initial retry delay in seconds
            SEQUEL_API_RETRY_BACKOFF: Exponential backoff multiplier
            SEQUEL_CACHE_ENABLED: Enable/disable caching (true/false)
            SEQUEL_CACHE_TTL_PROJECTS: Project cache TTL in seconds
            SEQUEL_CACHE_TTL_RESOURCES: Resource cache TTL in seconds
            SEQUEL_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
            SEQUEL_LOG_FILE: Log file path (optional)
            SEQUEL_ENABLE_CREDENTIAL_SCRUBBING: Enable credential scrubbing (true/false)
            SEQUEL_GCLOUD_PROJECT_ID: Default GCloud project ID
            SEQUEL_GCLOUD_QUOTA_WAIT_TIME: Seconds to wait on quota errors
            SEQUEL_PROJECT_FILTER_REGEX: Regex to filter projects (empty string = show all)
            SEQUEL_DNS_ZONE_FILTER: Only show DNS zones containing this string (empty = show all)
            SEQUEL_THEME: Textual theme name

        Returns:
            Config instance with values from environment and config file
        """
        # Load config file
        file_config = load_config_file()

        # Get default values
        defaults = get_default_config()

        # Helper to get value with precedence: env var > config file > default
        def get_value(env_var: str, file_section: str, file_key: str, default: str | None) -> str | None:
            env_val = os.getenv(env_var)
            if env_val is not None:
                return env_val

            if file_section in file_config and file_key in file_config[file_section]:
                return str(file_config[file_section][file_key])

            return default

        # Get project filter regex with special handling for empty string
        project_filter = get_value(
            "SEQUEL_PROJECT_FILTER_REGEX",
            "filters",
            "project_regex",
            defaults["filters"]["project_regex"]
        )
        # Convert empty string to None to disable filtering
        project_filter_regex = project_filter if project_filter else None

        # Validate regex pattern for security (prevent ReDoS attacks)
        if project_filter_regex:
            try:
                validate_regex(project_filter_regex, warn_on_redos=True)
            except RegexValidationError as e:
                print(f"WARNING: Invalid project filter regex '{project_filter_regex}': {e}")
                print("Project filtering will be disabled.")
                project_filter_regex = None

        # Get DNS zone filter with special handling for empty string
        dns_zone_filter = get_value(
            "SEQUEL_DNS_ZONE_FILTER",
            "filters",
            "dns_zone_filter",
            defaults["filters"].get("dns_zone_filter", "")
        )
        # Convert empty string to None to disable filtering
        dns_zone_filter = dns_zone_filter if dns_zone_filter else None

        # Get theme from env > config file > default
        theme = get_value(
            "SEQUEL_THEME",
            "ui",
            "theme",
            defaults["ui"]["theme"]
        ) or "textual-dark"

        # Get log file from env > config file > default
        log_file = get_value(
            "SEQUEL_LOG_FILE",
            "logging",
            "log_file",
            defaults["logging"]["log_file"]
        )

        # Get log level from env > config file > default
        log_level_value = get_value(
            "SEQUEL_LOG_LEVEL",
            "logging",
            "log_level",
            defaults["logging"]["log_level"]
        )
        log_level = log_level_value.upper() if log_level_value else "INFO"

        return cls(
            api_timeout=int(os.getenv("SEQUEL_API_TIMEOUT", "30")),
            api_max_retries=int(os.getenv("SEQUEL_API_MAX_RETRIES", "3")),
            api_retry_delay=float(os.getenv("SEQUEL_API_RETRY_DELAY", "1.0")),
            api_retry_backoff=float(os.getenv("SEQUEL_API_RETRY_BACKOFF", "2.0")),
            cache_enabled=os.getenv("SEQUEL_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl_projects=int(os.getenv("SEQUEL_CACHE_TTL_PROJECTS", "600")),
            cache_ttl_resources=int(os.getenv("SEQUEL_CACHE_TTL_RESOURCES", "300")),
            log_level=log_level,
            log_file=log_file,
            enable_credential_scrubbing=os.getenv(
                "SEQUEL_ENABLE_CREDENTIAL_SCRUBBING", "true"
            ).lower()
            == "true",
            gcloud_project_id=os.getenv("SEQUEL_GCLOUD_PROJECT_ID"),
            gcloud_quota_wait_time=int(os.getenv("SEQUEL_GCLOUD_QUOTA_WAIT_TIME", "60")),
            project_filter_regex=project_filter_regex,
            dns_zone_filter=dns_zone_filter,
            theme=theme,
        )


# Global config instance (lazy-loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        Config instance (loads from environment on first call)
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    """Reset the global configuration (mainly for testing)."""
    global _config
    _config = None
