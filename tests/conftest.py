"""Pytest configuration and shared fixtures."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_gcloud_credentials() -> MagicMock:
    """Mock Google Cloud credentials for testing."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.project_id = "test-project-123"
    return creds


@pytest.fixture
def mock_project_response() -> dict[str, Any]:
    """Mock Google Cloud project API response."""
    return {
        "name": "projects/test-project-123",
        "projectId": "test-project-123",
        "projectNumber": "123456789",
        "displayName": "Test Project",
        "state": "ACTIVE",
        "createTime": "2024-01-01T00:00:00Z",
        "labels": {"env": "test"},
    }


@pytest.fixture
def mock_cloudsql_response() -> dict[str, Any]:
    """Mock CloudSQL instance API response."""
    return {
        "name": "test-instance",
        "databaseVersion": "POSTGRES_14",
        "region": "us-central1",
        "settings": {
            "tier": "db-f1-micro",
        },
        "state": "RUNNABLE",
        "ipAddresses": [
            {"type": "PRIMARY", "ipAddress": "10.0.0.1"}
        ],
        "createTime": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_auth_manager() -> AsyncMock:
    """Mock authentication manager."""
    auth = AsyncMock()
    auth.get_credentials = AsyncMock(return_value=MagicMock(
        valid=True,
        expired=False,
        project_id="test-project-123"
    ))
    auth.project_id = "test-project-123"
    return auth


@pytest.fixture
async def textual_app_pilot():
    """Fixture for testing Textual apps."""
    # This will be implemented when we create the app
    # Using Textual's run_test() context manager
    pass
