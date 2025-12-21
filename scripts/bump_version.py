#!/usr/bin/env python3
"""Version bumping script for Sequel.

Updates version in all locations atomically:
- src/sequel/__init__.py
- pyproject.toml

Note: setup.py no longer contains version (defers to pyproject.toml)

Usage:
    python scripts/bump_version.py patch  # 0.1.0 -> 0.1.1
    python scripts/bump_version.py minor  # 0.1.0 -> 0.2.0
    python scripts/bump_version.py major  # 0.1.0 -> 1.0.0
"""

import re
import sys
from pathlib import Path


def get_version_from_file(file_path: Path, pattern: str) -> str:
    """Extract version string from a file using regex pattern."""
    content = file_path.read_text()
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find version in {file_path}")
    return match.group(1)


def update_version_in_file(file_path: Path, pattern: str, new_version: str) -> None:
    """Update version in a file using regex pattern."""
    content = file_path.read_text()
    updated = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), new_version), content, flags=re.MULTILINE)
    file_path.write_text(updated)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse version string into (major, minor, patch) tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(version: str, bump_type: str) -> str:
    """Bump version according to bump type."""
    major, minor, patch = parse_version(version)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use: major, minor, or patch")


def get_current_versions() -> dict[str, str]:
    """Get current version from all files."""
    repo_root = Path(__file__).parent.parent

    versions = {
        "__init__.py": get_version_from_file(
            repo_root / "src/sequel/__init__.py",
            r'__version__\s*=\s*"([^"]+)"'
        ),
        "pyproject.toml": get_version_from_file(
            repo_root / "pyproject.toml",
            r'^\s*version\s*=\s*"([^"]+)"'  # Match only at start of line
        ),
    }

    return versions


def validate_versions(versions: dict[str, str]) -> str:
    """Validate that all versions are consistent."""
    unique_versions = set(versions.values())

    if len(unique_versions) != 1:
        print("ERROR: Version mismatch detected!")
        for file, version in versions.items():
            print(f"  {file}: {version}")
        sys.exit(1)

    return next(iter(unique_versions))


def update_all_versions(new_version: str) -> None:
    """Update version in all files."""
    repo_root = Path(__file__).parent.parent

    files_to_update = [
        (
            repo_root / "src/sequel/__init__.py",
            r'__version__\s*=\s*"([^"]+)"'
        ),
        (
            repo_root / "pyproject.toml",
            r'^\s*version\s*=\s*"([^"]+)"'  # Match only at start of line
        ),
    ]

    for file_path, pattern in files_to_update:
        update_version_in_file(file_path, pattern, new_version)
        print(f"✓ Updated {file_path.name}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py {major|minor|patch}")
        sys.exit(1)

    bump_type = sys.argv[1].lower()

    if bump_type not in ["major", "minor", "patch"]:
        print(f"ERROR: Invalid bump type '{bump_type}'")
        print("Valid options: major, minor, patch")
        sys.exit(1)

    # Get and validate current versions
    print("Checking current versions...")
    versions = get_current_versions()
    current_version = validate_versions(versions)
    print(f"Current version: {current_version}")

    # Calculate new version
    new_version = bump_version(current_version, bump_type)
    print(f"New version: {new_version}")

    # Confirm with user
    response = input(f"\nBump version from {current_version} to {new_version}? [y/N]: ")
    if response.lower() not in ["y", "yes"]:
        print("Aborted.")
        sys.exit(0)

    # Update all files
    print("\nUpdating version in all files...")
    update_all_versions(new_version)

    print(f"\n✓ Version bumped to {new_version}")
    print("\nNext steps:")
    print("  1. Review changes: git diff")
    print(f"  2. Commit changes: git add -A && git commit -m 'Bump version to {new_version}'")
    print(f"  3. Create tag: git tag v{new_version}")
    print("  4. Push: git push && git push --tags")


if __name__ == "__main__":
    main()
