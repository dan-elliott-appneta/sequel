"""Tests for regex validation utilities."""

import re

import pytest

from sequel.utils.regex_validator import (
    RegexValidationError,
    check_redos_vulnerability,
    safe_regex_compile,
    validate_regex,
    validate_regex_syntax,
)


class TestValidateRegexSyntax:
    """Test regex syntax validation."""

    def test_valid_simple_pattern(self) -> None:
        """Test that valid simple patterns pass validation."""
        validate_regex_syntax("test")
        validate_regex_syntax("^test$")
        validate_regex_syntax("test.*pattern")
        # Should not raise

    def test_valid_complex_pattern(self) -> None:
        """Test that valid complex patterns pass validation."""
        validate_regex_syntax(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$")
        validate_regex_syntax(r"\d{3}-\d{2}-\d{4}")
        # Should not raise

    def test_empty_pattern(self) -> None:
        """Test that empty pattern is valid."""
        validate_regex_syntax("")
        # Should not raise

    def test_invalid_syntax_unclosed_bracket(self) -> None:
        """Test that invalid syntax raises error."""
        with pytest.raises(RegexValidationError, match="Invalid regex syntax"):
            validate_regex_syntax("[abc")

    def test_invalid_syntax_unclosed_paren(self) -> None:
        """Test that unclosed parenthesis raises error."""
        with pytest.raises(RegexValidationError, match="Invalid regex syntax"):
            validate_regex_syntax("(abc")

    def test_invalid_syntax_bad_quantifier(self) -> None:
        """Test that invalid quantifier raises error."""
        with pytest.raises(RegexValidationError, match="Invalid regex syntax"):
            validate_regex_syntax("a{5,2}")  # min > max

    def test_invalid_syntax_trailing_backslash(self) -> None:
        """Test that trailing backslash raises error."""
        with pytest.raises(RegexValidationError, match="Invalid regex syntax"):
            validate_regex_syntax("test\\")


class TestCheckRedosVulnerability:
    """Test ReDoS vulnerability detection."""

    def test_safe_pattern_no_warnings(self) -> None:
        """Test that safe patterns return no warnings."""
        warnings = check_redos_vulnerability("^test$")
        assert warnings == []

        warnings = check_redos_vulnerability("simple")
        assert warnings == []

        warnings = check_redos_vulnerability(r"\d{3}-\d{2}-\d{4}")
        assert warnings == []

    def test_empty_pattern_no_warnings(self) -> None:
        """Test that empty pattern returns no warnings."""
        warnings = check_redos_vulnerability("")
        assert warnings == []

    def test_nested_star_quantifier(self) -> None:
        """Test detection of nested star quantifiers."""
        warnings = check_redos_vulnerability("(a*)*")
        assert len(warnings) > 0
        assert any("catastrophic backtracking" in w.lower() for w in warnings)

    def test_nested_plus_quantifier(self) -> None:
        """Test detection of nested plus quantifiers."""
        warnings = check_redos_vulnerability("(a+)+")
        assert len(warnings) > 0
        assert any("catastrophic backtracking" in w.lower() for w in warnings)

    def test_nested_range_quantifier(self) -> None:
        """Test detection of nested range quantifiers."""
        warnings = check_redos_vulnerability("(a{2,5})*")
        assert len(warnings) > 0
        assert any("catastrophic backtracking" in w.lower() for w in warnings)

    def test_overlapping_alternation(self) -> None:
        """Test detection of overlapping alternations."""
        warnings = check_redos_vulnerability("(a|ab)*")
        assert len(warnings) > 0
        assert any("overlapping" in w.lower() or "slow" in w.lower() for w in warnings)

    def test_consecutive_quantifiers(self) -> None:
        """Test detection of consecutive quantifiers."""
        warnings = check_redos_vulnerability("a*+")
        assert len(warnings) > 0

    def test_excessive_capturing_groups(self) -> None:
        """Test detection of excessive capturing groups."""
        # Create pattern with 25 groups (exceeds limit of 20)
        pattern = "".join(["(a)" for _ in range(25)])
        warnings = check_redos_vulnerability(pattern)
        assert len(warnings) > 0
        assert any("capturing groups" in w.lower() for w in warnings)

    def test_overly_long_pattern(self) -> None:
        """Test detection of overly long patterns."""
        pattern = "a" * 600  # Exceeds limit of 500
        warnings = check_redos_vulnerability(pattern)
        assert len(warnings) > 0
        assert any("characters long" in w.lower() for w in warnings)

    def test_real_world_safe_pattern(self) -> None:
        """Test that real-world safe patterns pass."""
        # Project ID pattern (typical use case)
        warnings = check_redos_vulnerability(r"^[a-z][a-z0-9-]*[a-z0-9]$")
        assert warnings == []

        # Email-like pattern
        warnings = check_redos_vulnerability(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        assert warnings == []


class TestValidateRegex:
    """Test full regex validation."""

    def test_valid_pattern_no_redos_check(self) -> None:
        """Test that valid pattern passes when ReDoS check is disabled."""
        validate_regex("(a+)+", warn_on_redos=False)
        # Should not raise even with ReDoS pattern

    def test_valid_pattern_with_redos_check(self) -> None:
        """Test that valid safe pattern passes with ReDoS check."""
        validate_regex("^test$", warn_on_redos=True)
        # Should not raise

    def test_redos_pattern_fails_when_enabled(self) -> None:
        """Test that ReDoS pattern fails when ReDoS check is enabled."""
        with pytest.raises(RegexValidationError, match="Potentially unsafe"):
            validate_regex("(a+)+", warn_on_redos=True)

    def test_invalid_syntax_always_fails(self) -> None:
        """Test that invalid syntax fails regardless of ReDoS check."""
        with pytest.raises(RegexValidationError, match="Invalid regex syntax"):
            validate_regex("[abc", warn_on_redos=False)

        with pytest.raises(RegexValidationError, match="Invalid regex syntax"):
            validate_regex("[abc", warn_on_redos=True)

    def test_empty_pattern(self) -> None:
        """Test that empty pattern is valid."""
        validate_regex("", warn_on_redos=True)
        # Should not raise


class TestSafeRegexCompile:
    """Test safe regex compilation."""

    def test_compile_valid_pattern(self) -> None:
        """Test that valid pattern compiles successfully."""
        pattern = safe_regex_compile("^test$")
        assert isinstance(pattern, re.Pattern)
        assert pattern.match("test")
        assert not pattern.match("testing")

    def test_compile_with_flags(self) -> None:
        """Test compilation with regex flags."""
        pattern = safe_regex_compile("TEST", re.IGNORECASE)
        assert pattern.match("test")
        assert pattern.match("TEST")
        assert pattern.match("Test")

    def test_compile_invalid_syntax(self) -> None:
        """Test that invalid syntax raises error."""
        with pytest.raises(RegexValidationError, match="Invalid regex syntax"):
            safe_regex_compile("[abc")

    def test_compile_redos_pattern(self) -> None:
        """Test that ReDoS pattern raises error."""
        with pytest.raises(RegexValidationError, match="Potentially unsafe"):
            safe_regex_compile("(a+)+")

    def test_compile_empty_pattern(self) -> None:
        """Test that empty pattern compiles."""
        pattern = safe_regex_compile("")
        assert isinstance(pattern, re.Pattern)


class TestRealWorldScenarios:
    """Test real-world use cases."""

    def test_project_id_filter(self) -> None:
        """Test typical project ID filter pattern."""
        # Common GCP project ID pattern
        pattern_str = r"^[a-z][-a-z0-9]*[a-z0-9]$"
        validate_regex(pattern_str, warn_on_redos=True)

        pattern = safe_regex_compile(pattern_str)
        assert pattern.match("my-project-123")
        assert pattern.match("test-prod")
        assert not pattern.match("-invalid")
        assert not pattern.match("invalid-")
        assert not pattern.match("UPPERCASE")

    def test_prefix_filter(self) -> None:
        """Test prefix-based filter pattern."""
        pattern_str = r"^prod-.*"
        validate_regex(pattern_str, warn_on_redos=True)

        pattern = safe_regex_compile(pattern_str)
        assert pattern.match("prod-service-1")
        assert pattern.match("prod-db")
        assert not pattern.match("dev-service")

    def test_suffix_filter(self) -> None:
        """Test suffix-based filter pattern."""
        pattern_str = r".*-prod$"
        validate_regex(pattern_str, warn_on_redos=True)

        pattern = safe_regex_compile(pattern_str)
        assert pattern.match("service-prod")
        assert pattern.match("db-prod")
        assert not pattern.match("service-dev")

    def test_alternation_filter(self) -> None:
        """Test alternation-based filter pattern."""
        pattern_str = r"^(prod|staging|dev)-.*"
        validate_regex(pattern_str, warn_on_redos=True)

        pattern = safe_regex_compile(pattern_str)
        assert pattern.match("prod-service")
        assert pattern.match("staging-db")
        assert pattern.match("dev-app")
        assert not pattern.match("test-service")
