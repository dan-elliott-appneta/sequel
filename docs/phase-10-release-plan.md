# Phase 10: Packaging & Release

## Overview

This phase prepares Sequel for public release with automated workflows, PyPI publishing, and comprehensive release management.

**Branch:** `phase-10-release`

**Current State:**
- Version: 0.1.0 (Alpha)
- All features implemented
- Ready for release preparation

## Objectives

- Automated release workflow
- PyPI publishing
- Version management automation
- Release notes generation
- Distribution artifacts

---

## Detailed Tasks

### 10.1 GitHub Actions Release Workflow

**New file:** `.github/workflows/release.yml`

**Trigger:** Git tag push (e.g., `v0.1.0`)

**Steps:**
1. Checkout code
2. Set up Python (3.11 and 3.12)
3. Install dependencies
4. Run full test suite
5. Build distribution packages
6. Create GitHub Release with notes
7. Publish to PyPI (if tests pass)

**Example workflow:**
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install build twine
      - name: Run tests
        run: |
          pytest --cov
      - name: Build package
        run: |
          python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: |
          twine upload dist/*
      - name: Create GitHub Release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body_path: RELEASE_NOTES.md
```

---

### 10.2 Version Management Automation

**New file:** `scripts/bump_version.py`

**Purpose:** Update version in all 3 locations atomically

**Locations:**
- `src/sequel/__init__.py`
- `setup.py`
- `pyproject.toml`

**Usage:**
```bash
python scripts/bump_version.py patch  # 0.1.0 -> 0.1.1
python scripts/bump_version.py minor  # 0.1.0 -> 0.2.0
python scripts/bump_version.py major  # 0.1.0 -> 1.0.0
```

**Features:**
- Validates current version consistency
- Updates all files
- Creates git commit
- Creates git tag
- Prompts for confirmation

---

### 10.3 Automated Changelog Generation

**Tool:** git-changelog or conventional-commits

**Integration:**
- Parse commit messages
- Group by type (feat, fix, docs, etc.)
- Generate CHANGELOG.md section
- Include in release notes

**Commit Message Convention:**
```
feat: Add Cloud DNS support
fix: Resolve cache cleanup race condition
docs: Update installation guide
perf: Optimize tree rendering
```

---

### 10.4 PyPI Configuration

**New file:** `.pypirc` (template, not committed)

**Setup:**
```ini
[pypi]
username = __token__
password = pypi-...  # API token from PyPI
```

**Package Metadata Review:**
- `setup.py` - Ensure all fields complete
- `pyproject.toml` - Build system config
- `README.md` - PyPI description
- `LICENSE` - License file included

**Test PyPI:**
```bash
# Upload to test PyPI first
twine upload --repository testpypi dist/*

# Verify installation from test PyPI
pip install --index-url https://test.pypi.org/simple/ sequel
```

---

### 10.5 Release Notes Template

**New file:** `RELEASE_NOTES_TEMPLATE.md`

**Sections:**
- **Highlights:** Major features
- **New Features:** All new capabilities
- **Bug Fixes:** Fixed issues
- **Performance:** Improvements
- **Breaking Changes:** API changes
- **Deprecations:** Deprecated features
- **Contributors:** Thank contributors

**Generation:**
- Populate from CHANGELOG.md
- Add migration guide if breaking changes
- Include upgrade instructions

---

### 10.6 Distribution Artifacts

**Build outputs:**
- Source distribution (.tar.gz)
- Wheel for Python 3.11
- Wheel for Python 3.12

**Build commands:**
```bash
python -m build
# Produces:
#   dist/sequel-0.1.0.tar.gz
#   dist/sequel-0.1.0-py3-none-any.whl
```

**Verification:**
- Test installation from wheel
- Test installation from source
- Verify entry points work
- Check package metadata

---

### 10.7 Release Checklist

**Pre-release:**
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in all files
- [ ] Git tag created
- [ ] Release notes prepared

**Release:**
- [ ] GitHub Actions workflow succeeds
- [ ] PyPI package uploaded
- [ ] GitHub Release created
- [ ] Documentation deployed

**Post-release:**
- [ ] Announcement (if applicable)
- [ ] Update main branch
- [ ] Close milestone (if using)

---

## Success Criteria

- Release can be created with single `git tag` command
- Version management is automated
- PyPI package installs correctly
- Release notes are comprehensive
- Distribution works on Python 3.11 and 3.12

---

## Related Documentation

- [Phase 7: Performance Optimization](phase-7-performance-plan.md)
- [Phase 8: Error Handling & UX Polish](phase-8-ux-plan.md)
- [Phase 9: Testing & Documentation](phase-9-testing-docs-plan.md)
