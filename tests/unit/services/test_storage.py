"""Unit tests for Storage service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.storage import Bucket
from sequel.services.storage import (
    StorageService,
    get_storage_service,
)


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Create mock credentials."""
    creds = MagicMock()
    creds.valid = True
    return creds


@pytest.fixture
def mock_auth_manager(mock_credentials: MagicMock) -> AsyncMock:
    """Create mock auth manager."""
    manager = AsyncMock()
    manager.credentials = mock_credentials
    manager.project_id = "test-project"
    return manager


@pytest.fixture
def mock_storage_client() -> MagicMock:
    """Create mock Cloud Storage API client."""
    return MagicMock()


@pytest.fixture
def storage_service() -> StorageService:
    """Create Storage service instance."""
    return StorageService()


class TestStorageService:
    """Tests for StorageService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, storage_service: StorageService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Cloud Storage client."""
        with (
            patch("sequel.services.storage.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.storage.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await storage_service._get_client()

            mock_build.assert_called_once_with(
                "storage",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert storage_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, storage_service: StorageService
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        storage_service._client = mock_client

        client = await storage_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_buckets_success(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing buckets successfully."""
        mock_response = {
            "items": [
                {
                    "name": "my-bucket-1",
                    "location": "US",
                    "storageClass": "STANDARD",
                    "timeCreated": "2023-01-01T00:00:00.000Z",
                    "versioning": {"enabled": True},
                    "labels": {"env": "prod"},
                },
                {
                    "name": "my-bucket-2",
                    "location": "US-CENTRAL1",
                    "storageClass": "NEARLINE",
                    "timeCreated": "2023-02-01T00:00:00.000Z",
                    "versioning": {"enabled": False},
                    "lifecycle": {
                        "rule": [
                            {"action": {"type": "Delete"}, "condition": {"age": 30}},
                        ]
                    },
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        buckets = await storage_service.list_buckets("test-project", use_cache=False)

        assert len(buckets) == 2
        assert isinstance(buckets[0], Bucket)
        assert buckets[0].bucket_name == "my-bucket-1"
        assert buckets[0].storage_class == "STANDARD"
        assert buckets[0].versioning_enabled is True
        assert buckets[0].labels_count == 1
        assert buckets[1].bucket_name == "my-bucket-2"
        assert buckets[1].storage_class == "NEARLINE"
        assert buckets[1].lifecycle_rules_count == 1

    @pytest.mark.asyncio
    async def test_list_buckets_empty(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing buckets when none exist."""
        mock_response: dict[str, Any] = {"items": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        buckets = await storage_service.list_buckets("test-project", use_cache=False)

        assert len(buckets) == 0

    @pytest.mark.asyncio
    async def test_list_buckets_no_items_key(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing buckets when response has no items key."""
        mock_response: dict[str, Any] = {}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        buckets = await storage_service.list_buckets("test-project", use_cache=False)

        assert len(buckets) == 0

    @pytest.mark.asyncio
    async def test_list_buckets_error(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test error handling when listing buckets."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        buckets = await storage_service.list_buckets("test-project", use_cache=False)

        # Should return empty list on error
        assert len(buckets) == 0

    @pytest.mark.asyncio
    async def test_list_buckets_with_cache(
        self, storage_service: StorageService
    ) -> None:
        """Test listing buckets with caching."""
        mock_bucket = Bucket(
            id="cached-bucket",
            name="cached-bucket",
            bucket_name="cached-bucket",
            location="US",
            storage_class="STANDARD",
        )

        with patch.object(storage_service._cache, "get", return_value=[mock_bucket]):
            buckets = await storage_service.list_buckets("test-project", use_cache=True)

            assert len(buckets) == 1
            assert buckets[0] == mock_bucket

    @pytest.mark.asyncio
    async def test_list_buckets_various_storage_classes(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing buckets with various storage classes."""
        mock_response = {
            "items": [
                {"name": "standard-bucket", "storageClass": "STANDARD"},
                {"name": "nearline-bucket", "storageClass": "NEARLINE"},
                {"name": "coldline-bucket", "storageClass": "COLDLINE"},
                {"name": "archive-bucket", "storageClass": "ARCHIVE"},
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        buckets = await storage_service.list_buckets("test-project", use_cache=False)

        assert len(buckets) == 4
        assert buckets[0].storage_class == "STANDARD"
        assert buckets[1].storage_class == "NEARLINE"
        assert buckets[2].storage_class == "COLDLINE"
        assert buckets[3].storage_class == "ARCHIVE"

    @pytest.mark.asyncio
    async def test_list_buckets_caching(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test that results are cached."""
        mock_response = {
            "items": [
                {
                    "name": "test-bucket",
                    "location": "US",
                    "storageClass": "STANDARD",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        with patch.object(storage_service._cache, "set") as mock_set:
            await storage_service.list_buckets("test-project", use_cache=False)

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "storage:buckets:test-project"
            # Second argument should be the buckets list
            assert len(mock_set.call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_list_buckets_with_versioning(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing buckets with versioning configuration."""
        mock_response = {
            "items": [
                {
                    "name": "versioned-bucket",
                    "versioning": {"enabled": True},
                },
                {
                    "name": "no-version-bucket",
                    "versioning": {"enabled": False},
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        buckets = await storage_service.list_buckets("test-project", use_cache=False)

        assert len(buckets) == 2
        assert buckets[0].versioning_enabled is True
        assert buckets[1].versioning_enabled is False

    @pytest.mark.asyncio
    async def test_list_buckets_with_lifecycle_rules(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing buckets with lifecycle rules."""
        mock_response = {
            "items": [
                {
                    "name": "lifecycle-bucket",
                    "lifecycle": {
                        "rule": [
                            {"action": {"type": "Delete"}, "condition": {"age": 30}},
                            {"action": {"type": "SetStorageClass", "storageClass": "NEARLINE"}, "condition": {"age": 7}},
                        ]
                    },
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.buckets().list.return_value = mock_request

        storage_service._client = mock_storage_client

        buckets = await storage_service.list_buckets("test-project", use_cache=False)

        assert len(buckets) == 1
        assert buckets[0].lifecycle_rules_count == 2


class TestGetStorageService:
    """Tests for get_storage_service function."""

    @pytest.mark.asyncio
    async def test_get_storage_service_creates_instance(self) -> None:
        """Test that get_storage_service creates a global instance."""
        service1 = await get_storage_service()
        service2 = await get_storage_service()

        assert service1 is service2
        assert isinstance(service1, StorageService)
    @pytest.mark.asyncio
    async def test_list_objects_success(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing objects successfully."""
        mock_response = {
            "items": [
                {
                    "name": "file1.txt",
                    "bucket": "my-bucket",
                    "size": "1024",
                    "contentType": "text/plain",
                    "storageClass": "STANDARD",
                    "crc32c": "AAAAAA==",
                    "timeCreated": "2023-01-01T00:00:00.000Z",
                    "generation": "1234567890",
                },
                {
                    "name": "docs/report.pdf",
                    "bucket": "my-bucket",
                    "size": "2048576",
                    "contentType": "application/pdf",
                    "storageClass": "STANDARD",
                    "crc32c": "BBBBBB==",
                    "timeCreated": "2023-02-01T00:00:00.000Z",
                    "generation": "9876543210",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.objects().list.return_value = mock_request

        storage_service._client = mock_storage_client

        from sequel.models.storage import StorageObject
        objects = await storage_service.list_objects(
            "test-project", "my-bucket", use_cache=False
        )

        assert len(objects) == 2
        assert isinstance(objects[0], StorageObject)
        assert objects[0].object_name == "file1.txt"
        assert objects[0].size == 1024
        assert objects[0].content_type == "text/plain"
        assert objects[1].object_name == "docs/report.pdf"
        assert objects[1].size == 2048576

    @pytest.mark.asyncio
    async def test_list_objects_empty(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing objects when bucket is empty."""
        mock_response: dict[str, Any] = {"items": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.objects().list.return_value = mock_request

        storage_service._client = mock_storage_client

        objects = await storage_service.list_objects(
            "test-project", "my-bucket", use_cache=False
        )

        assert len(objects) == 0

    @pytest.mark.asyncio
    async def test_list_objects_with_max_results(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test listing objects with max_results parameter."""
        mock_response = {
            "items": [
                {
                    "name": "file.txt",
                    "bucket": "my-bucket",
                    "size": "1024",
                }
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.objects().list.return_value = mock_request

        storage_service._client = mock_storage_client

        objects = await storage_service.list_objects(
            "test-project", "my-bucket", use_cache=False, max_results=50
        )

        # Verify maxResults was passed
        mock_storage_client.objects().list.assert_called_once_with(
            bucket="my-bucket",
            maxResults=50,
        )
        assert len(objects) == 1

    @pytest.mark.asyncio
    async def test_list_objects_error(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test error handling when listing objects."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_storage_client.objects().list.return_value = mock_request

        storage_service._client = mock_storage_client

        objects = await storage_service.list_objects(
            "test-project", "my-bucket", use_cache=False
        )

        # Should return empty list on error
        assert len(objects) == 0

    @pytest.mark.asyncio
    async def test_list_objects_with_cache(
        self, storage_service: StorageService
    ) -> None:
        """Test listing objects with caching."""
        from sequel.models.storage import StorageObject
        mock_object = StorageObject(
            id="my-bucket:cached.txt",
            name="cached.txt",
            object_name="cached.txt",
            bucket_name="my-bucket",
            size=1024,
        )

        with patch.object(storage_service._cache, "get", return_value=[mock_object]):
            objects = await storage_service.list_objects(
                "test-project", "my-bucket", use_cache=True
            )

            assert len(objects) == 1
            assert objects[0] == mock_object

    @pytest.mark.asyncio
    async def test_list_objects_caching(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test that object results are cached."""
        mock_response = {
            "items": [
                {
                    "name": "file.txt",
                    "bucket": "my-bucket",
                    "size": "1024",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.objects().list.return_value = mock_request

        storage_service._client = mock_storage_client

        with patch.object(storage_service._cache, "set") as mock_set:
            await storage_service.list_objects(
                "test-project", "my-bucket", use_cache=False
            )

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "storage:objects:test-project:my-bucket"
            # Second argument should be the objects list
            assert len(mock_set.call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_list_objects_sets_project_id(
        self, storage_service: StorageService, mock_storage_client: MagicMock
    ) -> None:
        """Test that project_id is set on returned objects."""
        mock_response = {
            "items": [
                {
                    "name": "file.txt",
                    "bucket": "my-bucket",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_storage_client.objects().list.return_value = mock_request

        storage_service._client = mock_storage_client

        objects = await storage_service.list_objects(
            "test-project", "my-bucket", use_cache=False
        )

        assert len(objects) == 1
        assert objects[0].project_id == "test-project"


