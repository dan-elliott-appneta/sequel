"""Unit tests for CloudSQL models."""

from typing import Any

from sequel.models.cloudsql import CloudSQLInstance


class TestCloudSQLInstance:
    """Tests for CloudSQLInstance model."""

    def test_create_cloudsql_instance(self) -> None:
        """Test creating a CloudSQL instance."""
        instance = CloudSQLInstance(
            id="my-instance",
            name="my-instance",
            instance_name="my-instance",
            database_version="POSTGRES_14",
            state="RUNNABLE",
            region="us-central1",
            tier="db-f1-micro",
            ip_addresses=["10.0.0.1"],
        )

        assert instance.id == "my-instance"
        assert instance.instance_name == "my-instance"
        assert instance.database_version == "POSTGRES_14"
        assert instance.state == "RUNNABLE"
        assert instance.region == "us-central1"
        assert instance.tier == "db-f1-micro"
        assert instance.ip_addresses == ["10.0.0.1"]

    def test_from_api_response_full(self) -> None:
        """Test creating instance from full API response."""
        data = {
            "name": "production-db",
            "databaseVersion": "MYSQL_8_0",
            "state": "RUNNABLE",
            "region": "europe-west1",
            "settings": {
                "tier": "db-n1-standard-2",
            },
            "ipAddresses": [
                {"ipAddress": "10.128.0.5"},
                {"ipAddress": "35.192.0.10"},
            ],
            "project": "my-project",
        }

        instance = CloudSQLInstance.from_api_response(data)

        assert instance.instance_name == "production-db"
        assert instance.database_version == "MYSQL_8_0"
        assert instance.state == "RUNNABLE"
        assert instance.region == "europe-west1"
        assert instance.tier == "db-n1-standard-2"
        assert instance.ip_addresses == ["10.128.0.5", "35.192.0.10"]
        assert instance.project_id == "my-project"
        assert instance.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating instance from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-instance",
        }

        instance = CloudSQLInstance.from_api_response(data)

        assert instance.instance_name == "minimal-instance"
        assert instance.database_version == "UNKNOWN"
        assert instance.state == "UNKNOWN"
        assert instance.region is None
        assert instance.tier == "unknown"  # Default value when no settings provided
        assert instance.ip_addresses == []
        assert instance.project_id == ""

    def test_from_api_response_no_ip_addresses(self) -> None:
        """Test creating instance without IP addresses."""
        data = {
            "name": "no-ip-instance",
            "databaseVersion": "POSTGRES_13",
            "state": "RUNNABLE",
        }

        instance = CloudSQLInstance.from_api_response(data)

        assert instance.ip_addresses == []

    def test_is_running_true(self) -> None:
        """Test is_running when instance is runnable."""
        instance = CloudSQLInstance(
            id="instance",
            name="instance",
            instance_name="instance",
            database_version="POSTGRES_14",
            tier="db-f1-micro",
            state="RUNNABLE",
        )

        assert instance.is_running() is True

    def test_is_running_false(self) -> None:
        """Test is_running when instance is not runnable."""
        instance = CloudSQLInstance(
            id="instance",
            name="instance",
            instance_name="instance",
            database_version="MYSQL_8_0",
            tier="db-n1-standard-1",
            state="SUSPENDED",
        )

        assert instance.is_running() is False
