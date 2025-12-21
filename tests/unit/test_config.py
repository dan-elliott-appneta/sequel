"""Unit tests for configuration module."""

import os

import pytest

from sequel.config import Config, get_config, reset_config


class TestConfig:
    """Test Config dataclass."""

    def test_config_defaults(self) -> None:
        """Test that Config has sensible defaults."""
        config = Config()

        assert config.api_timeout == 30
        assert config.api_max_retries == 3
        assert config.api_retry_delay == 1.0
        assert config.api_retry_backoff == 2.0
        assert config.cache_enabled is True
        assert config.cache_ttl_projects == 600
        assert config.cache_ttl_resources == 300
        assert config.log_level == "INFO"
        assert config.log_file is None
        assert config.enable_credential_scrubbing is True
        assert config.gcloud_project_id is None
        assert config.gcloud_quota_wait_time == 60

    def test_config_from_env_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config.from_env() with no environment variables."""
        # Clear all SEQUEL_ env vars
        for key in list(os.environ.keys()):
            if key.startswith("SEQUEL_"):
                monkeypatch.delenv(key, raising=False)

        config = Config.from_env()

        # Should use defaults
        assert config.api_timeout == 30
        assert config.api_max_retries == 3
        assert config.log_level == "INFO"

    def test_config_from_env_with_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config.from_env() with environment variables set."""
        monkeypatch.setenv("SEQUEL_API_TIMEOUT", "60")
        monkeypatch.setenv("SEQUEL_API_MAX_RETRIES", "5")
        monkeypatch.setenv("SEQUEL_LOG_LEVEL", "debug")
        monkeypatch.setenv("SEQUEL_CACHE_ENABLED", "false")
        monkeypatch.setenv("SEQUEL_GCLOUD_PROJECT_ID", "test-project-123")

        config = Config.from_env()

        assert config.api_timeout == 60
        assert config.api_max_retries == 5
        assert config.log_level == "DEBUG"  # Uppercased
        assert config.cache_enabled is False
        assert config.gcloud_project_id == "test-project-123"

    def test_config_from_env_cache_ttl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test cache TTL configuration from environment."""
        monkeypatch.setenv("SEQUEL_CACHE_TTL_PROJECTS", "1200")
        monkeypatch.setenv("SEQUEL_CACHE_TTL_RESOURCES", "600")

        config = Config.from_env()

        assert config.cache_ttl_projects == 1200
        assert config.cache_ttl_resources == 600

    def test_config_from_env_retry_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test retry configuration from environment."""
        monkeypatch.setenv("SEQUEL_API_RETRY_DELAY", "2.0")
        monkeypatch.setenv("SEQUEL_API_RETRY_BACKOFF", "1.5")

        config = Config.from_env()

        assert config.api_retry_delay == 2.0
        assert config.api_retry_backoff == 1.5

    def test_config_from_env_log_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log file configuration from environment."""
        monkeypatch.setenv("SEQUEL_LOG_FILE", "/tmp/sequel.log")

        config = Config.from_env()

        assert config.log_file == "/tmp/sequel.log"

    def test_config_from_env_credential_scrubbing_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test disabling credential scrubbing via environment."""
        monkeypatch.setenv("SEQUEL_ENABLE_CREDENTIAL_SCRUBBING", "false")

        config = Config.from_env()

        assert config.enable_credential_scrubbing is False

    def test_config_from_env_boolean_true_variations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that 'true' is recognized in various cases."""
        monkeypatch.setenv("SEQUEL_CACHE_ENABLED", "True")
        config = Config.from_env()
        assert config.cache_enabled is True

        monkeypatch.setenv("SEQUEL_CACHE_ENABLED", "TRUE")
        config = Config.from_env()
        assert config.cache_enabled is True

    def test_config_from_env_quota_wait_time(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test quota wait time configuration."""
        monkeypatch.setenv("SEQUEL_GCLOUD_QUOTA_WAIT_TIME", "120")

        config = Config.from_env()

        assert config.gcloud_quota_wait_time == 120


class TestGetConfig:
    """Test get_config function."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_config()

    def test_get_config_returns_config(self) -> None:
        """Test that get_config returns a Config instance."""
        config = get_config()
        assert isinstance(config, Config)

    def test_get_config_returns_same_instance(self) -> None:
        """Test that get_config returns the same instance (singleton)."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_get_config_loads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get_config loads from environment."""
        reset_config()
        monkeypatch.setenv("SEQUEL_API_TIMEOUT", "90")

        config = get_config()

        assert config.api_timeout == 90


class TestResetConfig:
    """Test reset_config function."""

    def test_reset_config_clears_singleton(self) -> None:
        """Test that reset_config clears the singleton instance."""
        config1 = get_config()
        reset_config()
        config2 = get_config()

        # Should be different instances after reset
        assert config1 is not config2
