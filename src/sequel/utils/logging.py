"""Secure logging utilities with credential scrubbing.

This module provides logging configuration that automatically scrubs
credentials, tokens, and other sensitive information from log output.
"""

import logging
import re
from typing import ClassVar


class CredentialScrubbingFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials from log messages.

    This filter removes or redacts:
    - OAuth tokens
    - API keys
    - Private keys
    - Bearer tokens in headers
    - Service account credentials
    - Any field matching sensitive patterns
    """

    # Patterns for sensitive data
    PATTERNS: ClassVar = [
        # JSON-style credential fields
        (re.compile(r'"token"\s*:\s*"[^"]*"'), '"token": "[REDACTED]"'),
        (re.compile(r'"private_key"\s*:\s*"[^"]*"'), '"private_key": "[REDACTED]"'),
        (re.compile(r'"api_key"\s*:\s*"[^"]*"'), '"api_key": "[REDACTED]"'),
        (re.compile(r'"secret"\s*:\s*"[^"]*"'), '"secret": "[REDACTED]"'),
        (re.compile(r'"password"\s*:\s*"[^"]*"'), '"password": "[REDACTED]"'),
        (re.compile(r'"client_secret"\s*:\s*"[^"]*"'), '"client_secret": "[REDACTED]"'),
        (re.compile(r'"access_token"\s*:\s*"[^"]*"'), '"access_token": "[REDACTED]"'),
        (re.compile(r'"refresh_token"\s*:\s*"[^"]*"'), '"refresh_token": "[REDACTED]"'),

        # Python-style credential fields
        (re.compile(r"token=\S+"), "token=[REDACTED]"),
        (re.compile(r"api_key=\S+"), "api_key=[REDACTED]"),
        (re.compile(r"private_key=\S+"), "private_key=[REDACTED]"),

        # Bearer tokens in headers
        (re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE), "Authorization: [REDACTED]"),
        (re.compile(r"Authorization:\s*\S+", re.IGNORECASE), "Authorization: [REDACTED]"),

        # Service account JSON keys (base64-like strings in quotes)
        (re.compile(r'"[A-Za-z0-9+/]{40,}={0,2}"'), '"[REDACTED_BASE64]"'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record, scrubbing sensitive information.

        Args:
            record: Log record to filter

        Returns:
            True (always allow the record through after scrubbing)
        """
        # Scrub the message
        if isinstance(record.msg, str):
            record.msg = self.scrub(record.msg)

        # Scrub args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.scrub(str(v)) if isinstance(v, str) else v
                              for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.scrub(str(arg)) if isinstance(arg, str) else arg
                                   for arg in record.args)

        return True

    @classmethod
    def scrub(cls, text: str) -> str:
        """Scrub sensitive information from text.

        Args:
            text: Text to scrub

        Returns:
            Scrubbed text with sensitive information redacted
        """
        scrubbed = text
        for pattern, replacement in cls.PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed


def setup_logging(
    level: str = "INFO",
    format_string: str | None = None,
    enable_credential_scrubbing: bool = True,
    log_file: str | None = None,
) -> None:
    """Set up logging with credential scrubbing.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (uses default if None)
        enable_credential_scrubbing: Whether to enable credential scrubbing filter
        log_file: Path to log file (if None, logs are suppressed for TUI mode)
    """
    if format_string is None:
        format_string = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Configure handler: write to file if specified, otherwise use NullHandler for TUI
    handler: logging.Handler = (
        logging.FileHandler(log_file) if log_file else logging.NullHandler()
    )

    handler.setLevel(getattr(logging, level.upper()))
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Add credential scrubbing filter to all handlers
    if enable_credential_scrubbing:
        scrubbing_filter = CredentialScrubbingFilter()
        for handler in root_logger.handlers:
            handler.addFilter(scrubbing_filter)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with credential scrubbing.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance with credential scrubbing enabled
    """
    logger = logging.getLogger(name)

    # Add scrubbing filter if not already present
    has_scrubber = any(
        isinstance(f, CredentialScrubbingFilter)
        for handler in logger.handlers
        for f in handler.filters
    )

    if not has_scrubber and logger.handlers:
        scrubbing_filter = CredentialScrubbingFilter()
        for handler in logger.handlers:
            handler.addFilter(scrubbing_filter)

    return logger
