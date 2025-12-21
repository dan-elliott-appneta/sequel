"""Unit tests for secure logging utilities."""

import logging

import pytest

from sequel.utils.logging import CredentialScrubbingFilter, get_logger, setup_logging


class TestCredentialScrubbingFilter:
    """Test credential scrubbing filter."""

    def test_scrub_json_token(self) -> None:
        """Test scrubbing JSON-style token."""
        text = '"token": "secret123"'
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert scrubbed == '"token": "[REDACTED]"'
        assert "secret123" not in scrubbed

    def test_scrub_private_key(self) -> None:
        """Test scrubbing private key."""
        text = '"private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBg..."'
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert scrubbed == '"private_key": "[REDACTED]"'
        assert "BEGIN PRIVATE KEY" not in scrubbed

    def test_scrub_api_key(self) -> None:
        """Test scrubbing API key."""
        text = '"api_key": "AIzaSyD1234567890"'
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert scrubbed == '"api_key": "[REDACTED]"'
        assert "AIzaSyD" not in scrubbed

    def test_scrub_bearer_token(self) -> None:
        """Test scrubbing Bearer token."""
        text = "Authorization: Bearer ya29.a0AfH6SMBx..."
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert scrubbed == "Authorization: [REDACTED]"
        assert "ya29" not in scrubbed

    def test_scrub_bearer_token_case_insensitive(self) -> None:
        """Test scrubbing Bearer token (case insensitive)."""
        text = "Authorization: bearer ya29.a0AfH6SMBx..."
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert "ya29" not in scrubbed

    def test_scrub_python_style_token(self) -> None:
        """Test scrubbing Python-style parameter."""
        text = "token=abc123def456"
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert scrubbed == "token=[REDACTED]"
        assert "abc123" not in scrubbed

    def test_scrub_multiple_credentials(self) -> None:
        """Test scrubbing multiple credentials in one string."""
        text = '"token": "secret1", "api_key": "secret2", "private_key": "secret3"'
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert "secret1" not in scrubbed
        assert "secret2" not in scrubbed
        assert "secret3" not in scrubbed
        assert scrubbed.count("[REDACTED]") == 3

    def test_scrub_password(self) -> None:
        """Test scrubbing password field."""
        text = '"password": "mypassword123"'
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert scrubbed == '"password": "[REDACTED]"'
        assert "mypassword" not in scrubbed

    def test_scrub_preserves_normal_text(self) -> None:
        """Test that normal text is preserved."""
        text = "This is a normal log message with no credentials"
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert scrubbed == text

    def test_scrub_base64_like_strings(self) -> None:
        """Test scrubbing long base64-like strings."""
        text = '"key": "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVmZ2g="'
        scrubbed = CredentialScrubbingFilter.scrub(text)
        assert "YWJjZGVm" not in scrubbed
        assert "[REDACTED_BASE64]" in scrubbed

    def test_filter_log_record_with_string_message(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test filter modifies log record with string message."""
        filter_instance = CredentialScrubbingFilter()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='"token": "secret123"',
            args=(),
            exc_info=None,
        )

        # Apply filter
        result = filter_instance.filter(record)

        assert result is True
        assert "secret123" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_filter_allows_record_through(self) -> None:
        """Test that filter always returns True (allows record through)."""
        filter_instance = CredentialScrubbingFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        assert filter_instance.filter(record) is True


class TestSetupLogging:
    """Test logging setup."""

    def test_setup_logging_default(self) -> None:
        """Test setup_logging with defaults."""
        # Clear existing handlers to avoid state from previous tests
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging()

        assert root_logger.level == logging.INFO

    def test_setup_logging_custom_level(self) -> None:
        """Test setup_logging with custom level."""
        # Clear existing handlers to avoid state from previous tests
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(level="DEBUG")

        assert root_logger.level == logging.DEBUG

    def test_setup_logging_adds_scrubbing_filter(self) -> None:
        """Test that setup_logging adds credential scrubbing filter."""
        setup_logging(enable_credential_scrubbing=True)

        root_logger = logging.getLogger()
        has_scrubber = any(
            isinstance(f, CredentialScrubbingFilter)
            for handler in root_logger.handlers
            for f in handler.filters
        )

        assert has_scrubber

    def test_setup_logging_can_disable_scrubbing(self) -> None:
        """Test that credential scrubbing can be disabled."""
        # Clear existing handlers first
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(enable_credential_scrubbing=False)

        has_scrubber = any(
            isinstance(f, CredentialScrubbingFilter)
            for handler in root_logger.handlers
            for f in handler.filters
        )

        assert not has_scrubber


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
