"""Unit tests for Secrets models."""

from typing import Any

from sequel.models.secrets import Secret


class TestSecret:
    """Tests for Secret model."""

    def test_create_secret(self) -> None:
        """Test creating a secret instance."""
        secret = Secret(
            id="api-key",
            name="api-key",
            secret_name="api-key",
            replication_policy="automatic",
            version_count=3,
        )

        assert secret.id == "api-key"
        assert secret.secret_name == "api-key"
        assert secret.replication_policy == "automatic"
        assert secret.version_count == 3

    def test_from_api_response_automatic_replication(self) -> None:
        """Test creating secret with automatic replication."""
        data = {
            "name": "projects/123456/secrets/database-password",
            "replication": {
                "automatic": {}
            },
            "createTime": "2023-01-01T00:00:00Z",
            "labels": {"env": "production"},
        }

        secret = Secret.from_api_response(data)

        assert secret.secret_name == "database-password"
        assert secret.project_id == "123456"
        assert secret.replication_policy == "automatic"
        assert secret.labels == {"env": "production"}
        assert secret.created_at is not None
        assert secret.raw_data == data

    def test_from_api_response_user_managed_replication(self) -> None:
        """Test creating secret with user-managed replication."""
        data = {
            "name": "projects/my-project/secrets/api-token",
            "replication": {
                "userManaged": {
                    "replicas": [
                        {"location": "us-central1"},
                        {"location": "us-east1"},
                    ]
                }
            },
            "createTime": "2023-06-15T12:30:00Z",
        }

        secret = Secret.from_api_response(data)

        assert secret.secret_name == "api-token"
        assert secret.project_id == "my-project"
        assert secret.replication_policy == "user-managed"

    def test_from_api_response_minimal(self) -> None:
        """Test creating secret from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-secret",
        }

        secret = Secret.from_api_response(data)

        assert secret.secret_name == "minimal-secret"
        assert secret.project_id is None
        assert secret.replication_policy == "unknown"
        assert secret.created_at is None
        assert secret.version_count == 0

    def test_from_api_response_with_full_path(self) -> None:
        """Test extracting secret name from full path."""
        data = {
            "name": "projects/987654/secrets/my-secret-key",
        }

        secret = Secret.from_api_response(data)

        assert secret.secret_name == "my-secret-key"
        assert secret.project_id == "987654"

    def test_from_api_response_no_replication(self) -> None:
        """Test creating secret without replication info."""
        data = {
            "name": "projects/test/secrets/no-replication",
        }

        secret = Secret.from_api_response(data)

        assert secret.replication_policy == "unknown"

    def test_from_api_response_with_labels(self) -> None:
        """Test creating secret with labels."""
        data = {
            "name": "projects/test/secrets/labeled-secret",
            "labels": {
                "environment": "staging",
                "team": "backend",
                "critical": "true",
            },
        }

        secret = Secret.from_api_response(data)

        assert secret.labels["environment"] == "staging"
        assert secret.labels["team"] == "backend"
        assert secret.labels["critical"] == "true"
