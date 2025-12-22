"""Regex validation utilities to prevent ReDoS and syntax errors.

This module provides validation for user-provided regex patterns to prevent:
1. Syntax errors that would crash the application
2. ReDoS (Regular Expression Denial of Service) attacks via catastrophic backtracking
3. Excessively complex patterns that could cause performance issues
"""

import re
from typing import Any

# Known dangerous patterns that can cause catastrophic backtracking (ReDoS)
REDOS_PATTERNS = [
    # Nested quantifiers
    re.compile(r'\([^)]*\+\)[*+{]'),  # (a+)*, (a+)+, (a+){n,m}
    re.compile(r'\([^)]*\*\)[*+{]'),  # (a*)*, (a*)+, (a*){n,m}
    re.compile(r'\([^)]*\{[^}]+\}\)[*+{]'),  # (a{n,m})*, (a{n,m})+

    # Overlapping alternations with quantifiers
    re.compile(r'\([^)]*\|[^)]*\)[*+]'),  # (a|ab)*, (a|ab)+

    # Multiple consecutive unbounded quantifiers
    re.compile(r'[*+]\s*[*+]'),  # a*+, a++
]


class RegexValidationError(ValueError):
    """Exception raised when regex validation fails."""
    pass


def validate_regex_syntax(pattern: str) -> None:
    """Validate that a regex pattern has valid syntax.

    Args:
        pattern: Regex pattern string to validate

    Raises:
        RegexValidationError: If pattern has invalid syntax
    """
    if not pattern:
        return  # Empty pattern is valid (matches nothing)

    try:
        re.compile(pattern)
    except re.error as e:
        raise RegexValidationError(f"Invalid regex syntax: {e}") from e


def check_redos_vulnerability(pattern: str) -> list[str]:
    """Check if a regex pattern has known ReDoS vulnerabilities.

    This function detects common ReDoS patterns like:
    - Nested quantifiers: (a+)+, (a*)*
    - Overlapping alternations: (a|ab)*
    - Multiple consecutive quantifiers: a*+

    Args:
        pattern: Regex pattern string to check

    Returns:
        List of warnings about potential ReDoS issues (empty if safe)
    """
    if not pattern:
        return []

    warnings: list[str] = []

    # Check for known dangerous patterns
    for idx, dangerous_pattern in enumerate(REDOS_PATTERNS):
        if dangerous_pattern.search(pattern):
            if idx < 3:
                warnings.append(
                    "Nested quantifiers detected (e.g., (a+)*) - may cause catastrophic backtracking"
                )
            elif idx == 3:
                warnings.append(
                    "Overlapping alternation with quantifier detected - may cause slow matching"
                )
            elif idx == 4:
                warnings.append(
                    "Multiple consecutive quantifiers detected - invalid regex syntax"
                )

    # Check for excessive complexity
    if pattern.count('(') > 20:
        warnings.append(
            f"Pattern has {pattern.count('(')} capturing groups - may be overly complex"
        )

    if len(pattern) > 500:
        warnings.append(
            f"Pattern is {len(pattern)} characters long - may be overly complex"
        )

    return warnings


def validate_regex(pattern: str, warn_on_redos: bool = True) -> None:
    """Validate a regex pattern for both syntax and security issues.

    Args:
        pattern: Regex pattern string to validate
        warn_on_redos: If True, raise error on potential ReDoS patterns

    Raises:
        RegexValidationError: If pattern is invalid or has security issues
    """
    # Check syntax first
    validate_regex_syntax(pattern)

    if not pattern:
        return  # Empty is valid

    # Check for ReDoS vulnerabilities
    if warn_on_redos:
        warnings = check_redos_vulnerability(pattern)
        if warnings:
            raise RegexValidationError(
                f"Potentially unsafe regex pattern: {'; '.join(warnings)}"
            )


def safe_regex_compile(pattern: str, flags: int = 0) -> re.Pattern[Any]:
    """Safely compile a regex pattern with validation.

    Args:
        pattern: Regex pattern string
        flags: Regex flags (e.g., re.IGNORECASE)

    Returns:
        Compiled regex pattern

    Raises:
        RegexValidationError: If pattern is invalid or unsafe
    """
    validate_regex(pattern, warn_on_redos=True)
    return re.compile(pattern, flags)
