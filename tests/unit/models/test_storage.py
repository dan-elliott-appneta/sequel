"""Unit tests for Storage models."""

from typing import Any

from sequel.models.storage import Bucket


class TestBucket:
    """Tests for Bucket model."""

    def test_create_bucket(self) -> None:
        """Test creating a bucket instance."""
        bucket = Bucket(
            id="my-bucket",
            name="my-bucket",
            bucket_name="my-bucket",
            location="US",
            storage_class="STANDARD",
            versioning_enabled=True,
            lifecycle_rules_count=2,
            labels_count=3,
        )

        assert bucket.id == "my-bucket"
        assert bucket.bucket_name == "my-bucket"
        assert bucket.location == "US"
        assert bucket.storage_class == "STANDARD"
        assert bucket.versioning_enabled is True
        assert bucket.lifecycle_rules_count == 2
        assert bucket.labels_count == 3

    def test_from_api_response_full(self) -> None:
        """Test creating bucket from full API response."""
        data = {
            "name": "my-test-bucket",
            "location": "US-CENTRAL1",
            "storageClass": "STANDARD",
            "timeCreated": "2023-01-01T00:00:00.000Z",
            "updated": "2023-01-02T00:00:00.000Z",
            "projectNumber": "123456789",
            "versioning": {
                "enabled": True
            },
            "lifecycle": {
                "rule": [
                    {"action": {"type": "Delete"}, "condition": {"age": 30}},
                    {"action": {"type": "SetStorageClass", "storageClass": "NEARLINE"}, "condition": {"age": 7}}
                ]
            },
            "labels": {
                "env": "prod",
                "team": "platform",
                "cost-center": "engineering"
            }
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.bucket_name == "my-test-bucket"
        assert bucket.location == "US-CENTRAL1"
        assert bucket.storage_class == "STANDARD"
        assert bucket.project_id == "123456789"
        assert bucket.versioning_enabled is True
        assert bucket.lifecycle_rules_count == 2
        assert bucket.labels_count == 3
        assert bucket.created_at is not None
        assert bucket.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating bucket from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-bucket",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.bucket_name == "minimal-bucket"
        assert bucket.location is None
        assert bucket.storage_class is None
        assert bucket.project_id is None
        assert bucket.versioning_enabled is False
        assert bucket.lifecycle_rules_count == 0
        assert bucket.labels_count == 0
        assert bucket.created_at is None

    def test_from_api_response_with_versioning_enabled(self) -> None:
        """Test creating bucket with versioning enabled."""
        data = {
            "name": "versioned-bucket",
            "versioning": {
                "enabled": True
            },
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.versioning_enabled is True

    def test_from_api_response_with_versioning_disabled(self) -> None:
        """Test creating bucket with versioning disabled."""
        data = {
            "name": "no-version-bucket",
            "versioning": {
                "enabled": False
            },
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.versioning_enabled is False

    def test_from_api_response_with_versioning_missing(self) -> None:
        """Test creating bucket without versioning field."""
        data = {
            "name": "no-version-field-bucket",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.versioning_enabled is False

    def test_from_api_response_with_lifecycle_rules(self) -> None:
        """Test lifecycle rule counting."""
        data = {
            "name": "lifecycle-bucket",
            "lifecycle": {
                "rule": [
                    {"action": {"type": "Delete"}, "condition": {"age": 30}},
                    {"action": {"type": "SetStorageClass", "storageClass": "NEARLINE"}, "condition": {"age": 7}},
                    {"action": {"type": "SetStorageClass", "storageClass": "COLDLINE"}, "condition": {"age": 90}},
                ]
            },
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.lifecycle_rules_count == 3

    def test_from_api_response_with_no_lifecycle_rules(self) -> None:
        """Test bucket without lifecycle rules."""
        data = {
            "name": "no-lifecycle-bucket",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.lifecycle_rules_count == 0

    def test_from_api_response_with_empty_lifecycle_rules(self) -> None:
        """Test bucket with empty lifecycle rules list."""
        data = {
            "name": "empty-lifecycle-bucket",
            "lifecycle": {
                "rule": []
            },
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.lifecycle_rules_count == 0

    def test_from_api_response_with_labels(self) -> None:
        """Test label counting."""
        data = {
            "name": "labeled-bucket",
            "labels": {
                "env": "prod",
                "team": "platform",
                "cost-center": "engineering",
                "owner": "alice",
            }
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.labels_count == 4

    def test_from_api_response_with_no_labels(self) -> None:
        """Test bucket without labels."""
        data = {
            "name": "no-labels-bucket",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.labels_count == 0

    def test_from_api_response_with_empty_labels(self) -> None:
        """Test bucket with empty labels dict."""
        data = {
            "name": "empty-labels-bucket",
            "labels": {}
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.labels_count == 0

    def test_from_api_response_standard_storage(self) -> None:
        """Test creating bucket with STANDARD storage class."""
        data = {
            "name": "standard-bucket",
            "storageClass": "STANDARD",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.storage_class == "STANDARD"

    def test_from_api_response_nearline_storage(self) -> None:
        """Test creating bucket with NEARLINE storage class."""
        data = {
            "name": "nearline-bucket",
            "storageClass": "NEARLINE",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.storage_class == "NEARLINE"

    def test_from_api_response_coldline_storage(self) -> None:
        """Test creating bucket with COLDLINE storage class."""
        data = {
            "name": "coldline-bucket",
            "storageClass": "COLDLINE",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.storage_class == "COLDLINE"

    def test_from_api_response_archive_storage(self) -> None:
        """Test creating bucket with ARCHIVE storage class."""
        data = {
            "name": "archive-bucket",
            "storageClass": "ARCHIVE",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.storage_class == "ARCHIVE"

    def test_from_api_response_multiregion_location(self) -> None:
        """Test creating bucket with multi-region location."""
        data = {
            "name": "multiregion-bucket",
            "location": "US",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.location == "US"

    def test_from_api_response_region_location(self) -> None:
        """Test creating bucket with single region location."""
        data = {
            "name": "region-bucket",
            "location": "US-CENTRAL1",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.location == "US-CENTRAL1"

    def test_from_api_response_invalid_timestamp(self) -> None:
        """Test creating bucket with invalid timestamp."""
        data = {
            "name": "invalid-timestamp-bucket",
            "timeCreated": "not-a-timestamp",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.created_at is None

    def test_from_api_response_timestamp_parsing(self) -> None:
        """Test timestamp parsing with Z timezone."""
        data = {
            "name": "timestamp-bucket",
            "timeCreated": "2023-06-15T12:30:45.123Z",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.created_at is not None
        assert bucket.created_at.year == 2023
        assert bucket.created_at.month == 6
        assert bucket.created_at.day == 15

    def test_from_api_response_invalid_versioning_type(self) -> None:
        """Test handling invalid versioning field type."""
        data = {
            "name": "invalid-versioning-bucket",
            "versioning": "not-a-dict",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.versioning_enabled is False

    def test_from_api_response_invalid_lifecycle_type(self) -> None:
        """Test handling invalid lifecycle field type."""
        data = {
            "name": "invalid-lifecycle-bucket",
            "lifecycle": "not-a-dict",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.lifecycle_rules_count == 0

    def test_from_api_response_invalid_labels_type(self) -> None:
        """Test handling invalid labels field type."""
        data = {
            "name": "invalid-labels-bucket",
            "labels": "not-a-dict",
        }

        bucket = Bucket.from_api_response(data)

        assert bucket.labels_count == 0
