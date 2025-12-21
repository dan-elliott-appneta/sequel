"""Configuration management for Sequel.

This module provides centralized configuration loaded from environment variables.
"""

import os
from dataclasses import dataclass


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

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables.

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

        Returns:
            Config instance with values from environment
        """
        return cls(
            api_timeout=int(os.getenv("SEQUEL_API_TIMEOUT", "30")),
            api_max_retries=int(os.getenv("SEQUEL_API_MAX_RETRIES", "3")),
            api_retry_delay=float(os.getenv("SEQUEL_API_RETRY_DELAY", "1.0")),
            api_retry_backoff=float(os.getenv("SEQUEL_API_RETRY_BACKOFF", "2.0")),
            cache_enabled=os.getenv("SEQUEL_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl_projects=int(os.getenv("SEQUEL_CACHE_TTL_PROJECTS", "600")),
            cache_ttl_resources=int(os.getenv("SEQUEL_CACHE_TTL_RESOURCES", "300")),
            log_level=os.getenv("SEQUEL_LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("SEQUEL_LOG_FILE"),
            enable_credential_scrubbing=os.getenv(
                "SEQUEL_ENABLE_CREDENTIAL_SCRUBBING", "true"
            ).lower()
            == "true",
            gcloud_project_id=os.getenv("SEQUEL_GCLOUD_PROJECT_ID"),
            gcloud_quota_wait_time=int(os.getenv("SEQUEL_GCLOUD_QUOTA_WAIT_TIME", "60")),
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
