"""Test version and package setup."""

import sequel


def test_version_exists() -> None:
    """Test that version is defined."""
    assert hasattr(sequel, "__version__")
    assert isinstance(sequel.__version__, str)
    assert len(sequel.__version__) > 0


def test_version_format() -> None:
    """Test that version follows semantic versioning."""
    version = sequel.__version__
    parts = version.split(".")
    assert len(parts) == 3, "Version should be in format X.Y.Z"
    assert parts[0].isdigit(), "Major version should be numeric"
    assert parts[1].isdigit(), "Minor version should be numeric"
    assert parts[2].isdigit(), "Patch version should be numeric"
