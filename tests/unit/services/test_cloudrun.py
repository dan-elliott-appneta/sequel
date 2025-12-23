"""Unit tests for Cloud Run service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.cloudrun import CloudRunJob, CloudRunService
from sequel.services.cloudrun import (
    CloudRunService as CloudRunServiceClass,
)
from sequel.services.cloudrun import (
    get_cloudrun_service,
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
def mock_cloudrun_client() -> MagicMock:
    """Create mock Cloud Run API client."""
    return MagicMock()


@pytest.fixture
def cloudrun_service() -> CloudRunServiceClass:
    """Create Cloud Run service instance."""
    return CloudRunServiceClass()


class TestCloudRunService:
    """Tests for CloudRunService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, cloudrun_service: CloudRunServiceClass, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Cloud Run client."""
        with (
            patch("sequel.services.cloudrun.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.cloudrun.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await cloudrun_service._get_client()

            mock_build.assert_called_once_with(
                "run",
                "v2",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert cloudrun_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        cloudrun_service._client = mock_client

        client = await cloudrun_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_services_success(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test listing services successfully."""
        mock_response = {
            "services": [
                {
                    "name": "projects/test-project/locations/us-central1/services/service-1",
                    "uri": "https://service-1-abc123-uc.a.run.app",
                    "template": {
                        "containers": [{"image": "gcr.io/test-project/image:v1"}]
                    },
                    "traffic": [{"percent": 100}],
                    "conditions": [{"type": "Ready", "state": "CONDITION_SUCCEEDED"}],
                    "labels": {"env": "prod"},
                },
                {
                    "name": "projects/test-project/locations/us-west1/services/service-2",
                    "uri": "https://service-2-xyz789-uw.a.run.app",
                    "template": {
                        "containers": [{"image": "gcr.io/test-project/image:v2"}]
                    },
                    "traffic": [{"percent": 70}, {"percent": 30}],
                    "conditions": [{"type": "Ready", "state": "CONDITION_SUCCEEDED"}],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_cloudrun_client.projects().locations().services().list.return_value = mock_request

        cloudrun_service._client = mock_cloudrun_client

        services = await cloudrun_service.list_services("test-project", use_cache=False)

        assert len(services) == 2
        assert isinstance(services[0], CloudRunService)
        assert services[0].service_name == "service-1"
        assert services[0].region == "us-central1"
        assert services[0].url == "https://service-1-abc123-uc.a.run.app"
        assert services[0].image == "gcr.io/test-project/image:v1"
        assert services[0].status == "READY"
        assert services[0].traffic_percent == 100
        assert services[0].labels_count == 1
        assert services[1].service_name == "service-2"
        assert services[1].region == "us-west1"
        assert services[1].traffic_percent == 100  # 70 + 30

    @pytest.mark.asyncio
    async def test_list_services_empty(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test listing services when none exist."""
        mock_response: dict[str, Any] = {"services": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_cloudrun_client.projects().locations().services().list.return_value = mock_request

        cloudrun_service._client = mock_cloudrun_client

        services = await cloudrun_service.list_services("test-project", use_cache=False)

        assert len(services) == 0

    @pytest.mark.asyncio
    async def test_list_services_pagination(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test listing services with pagination."""
        mock_response_page1 = {
            "services": [
                {"name": "projects/test/locations/us-central1/services/service-1"},
                {"name": "projects/test/locations/us-west1/services/service-2"},
            ],
            "nextPageToken": "page2token",
        }
        mock_response_page2 = {
            "services": [
                {"name": "projects/test/locations/europe-west1/services/service-3"},
            ],
            # No nextPageToken means this is the last page
        }

        mock_request_page1 = MagicMock()
        mock_request_page1.execute = MagicMock(return_value=mock_response_page1)
        mock_request_page2 = MagicMock()
        mock_request_page2.execute = MagicMock(return_value=mock_response_page2)

        # Mock the list() method to return different requests based on pageToken
        def mock_list(**kwargs: Any) -> MagicMock:
            if kwargs.get("pageToken") == "page2token":
                return mock_request_page2
            return mock_request_page1

        mock_cloudrun_client.projects().locations().services().list.side_effect = mock_list
        cloudrun_service._client = mock_cloudrun_client

        services = await cloudrun_service.list_services("test-project", use_cache=False)

        # Should have all 3 services from both pages
        assert len(services) == 3
        assert mock_cloudrun_client.projects().locations().services().list.call_count == 2

    @pytest.mark.asyncio
    async def test_list_services_error_returns_empty(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test that errors return empty list."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_cloudrun_client.projects().locations().services().list.return_value = mock_request

        cloudrun_service._client = mock_cloudrun_client

        services = await cloudrun_service.list_services("test-project", use_cache=False)

        assert services == []

    @pytest.mark.asyncio
    async def test_list_jobs_success(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test listing jobs successfully."""
        mock_response = {
            "jobs": [
                {
                    "name": "projects/test-project/locations/us-central1/jobs/job-1",
                    "template": {
                        "template": {
                            "containers": [{"image": "gcr.io/test-project/batch:v1"}]
                        }
                    },
                    "executionCount": 5,
                    "latestCreatedExecution": {
                        "name": "job-1-exec-5",
                        "createTime": "2023-01-03T00:00:00.000000Z"
                    },
                    "conditions": [{"type": "Ready", "state": "CONDITION_SUCCEEDED"}],
                    "labels": {"type": "batch"},
                },
                {
                    "name": "projects/test-project/locations/us-west1/jobs/job-2",
                    "template": {
                        "template": {
                            "containers": [{"image": "gcr.io/test-project/etl:v2"}]
                        }
                    },
                    "executionCount": 12,
                    "conditions": [{"type": "Ready", "state": "CONDITION_SUCCEEDED"}],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_cloudrun_client.projects().locations().jobs().list.return_value = mock_request

        cloudrun_service._client = mock_cloudrun_client

        jobs = await cloudrun_service.list_jobs("test-project", use_cache=False)

        assert len(jobs) == 2
        assert isinstance(jobs[0], CloudRunJob)
        assert jobs[0].job_name == "job-1"
        assert jobs[0].region == "us-central1"
        assert jobs[0].image == "gcr.io/test-project/batch:v1"
        assert jobs[0].status == "READY"
        assert jobs[0].execution_count == 5
        assert jobs[0].last_execution_time is not None
        assert jobs[0].labels_count == 1
        assert jobs[1].job_name == "job-2"
        assert jobs[1].region == "us-west1"
        assert jobs[1].execution_count == 12

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test listing jobs when none exist."""
        mock_response: dict[str, Any] = {"jobs": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_cloudrun_client.projects().locations().jobs().list.return_value = mock_request

        cloudrun_service._client = mock_cloudrun_client

        jobs = await cloudrun_service.list_jobs("test-project", use_cache=False)

        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test listing jobs with pagination."""
        mock_response_page1 = {
            "jobs": [
                {"name": "projects/test/locations/us-central1/jobs/job-1"},
                {"name": "projects/test/locations/us-west1/jobs/job-2"},
            ],
            "nextPageToken": "page2token",
        }
        mock_response_page2 = {
            "jobs": [
                {"name": "projects/test/locations/europe-west1/jobs/job-3"},
            ],
            # No nextPageToken means this is the last page
        }

        mock_request_page1 = MagicMock()
        mock_request_page1.execute = MagicMock(return_value=mock_response_page1)
        mock_request_page2 = MagicMock()
        mock_request_page2.execute = MagicMock(return_value=mock_response_page2)

        # Mock the list() method to return different requests based on pageToken
        def mock_list(**kwargs: Any) -> MagicMock:
            if kwargs.get("pageToken") == "page2token":
                return mock_request_page2
            return mock_request_page1

        mock_cloudrun_client.projects().locations().jobs().list.side_effect = mock_list
        cloudrun_service._client = mock_cloudrun_client

        jobs = await cloudrun_service.list_jobs("test-project", use_cache=False)

        # Should have all 3 jobs from both pages
        assert len(jobs) == 3
        assert mock_cloudrun_client.projects().locations().jobs().list.call_count == 2

    @pytest.mark.asyncio
    async def test_list_jobs_error_returns_empty(
        self, cloudrun_service: CloudRunServiceClass, mock_cloudrun_client: MagicMock
    ) -> None:
        """Test that errors return empty list."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_cloudrun_client.projects().locations().jobs().list.return_value = mock_request

        cloudrun_service._client = mock_cloudrun_client

        jobs = await cloudrun_service.list_jobs("test-project", use_cache=False)

        assert jobs == []

    @pytest.mark.asyncio
    async def test_get_cloudrun_service_singleton(self) -> None:
        """Test that get_cloudrun_service returns singleton."""
        service1 = await get_cloudrun_service()
        service2 = await get_cloudrun_service()

        assert service1 is service2
