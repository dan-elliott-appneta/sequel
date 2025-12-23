"""Unit tests for Cloud Run service."""

from unittest.mock import AsyncMock, patch

import pytest

from sequel.models.cloudrun import CloudRunJob, CloudRunService
from sequel.services.cloudrun import (
    CloudRunService as CloudRunServiceClass,
)
from sequel.services.cloudrun import (
    get_cloudrun_service,
)


@pytest.fixture
def cloudrun_service() -> CloudRunServiceClass:
    """Create Cloud Run service instance."""
    return CloudRunServiceClass()


class TestCloudRunService:
    """Tests for CloudRunService class."""

    @pytest.mark.asyncio
    async def test_run_gcloud_command_success(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that _run_gcloud_command executes gcloud and parses JSON."""
        mock_stdout = b'[{"name": "test-service"}]'
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(mock_stdout, b""))
        mock_process.returncode = 0

        with patch(
            "sequel.services.cloudrun.asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            result = await cloudrun_service._run_gcloud_command(
                ["run", "services", "list"]
            )

            assert len(result) == 1
            assert result[0]["name"] == "test-service"

    @pytest.mark.asyncio
    async def test_run_gcloud_command_error(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that _run_gcloud_command handles errors gracefully."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error: Not found"))
        mock_process.returncode = 1

        with patch(
            "sequel.services.cloudrun.asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            result = await cloudrun_service._run_gcloud_command(
                ["run", "services", "list"]
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_run_gcloud_command_timeout(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that _run_gcloud_command handles timeout."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=TimeoutError())

        with patch(
            "sequel.services.cloudrun.asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            result = await cloudrun_service._run_gcloud_command(
                ["run", "services", "list"], timeout=1.0
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_list_services_success(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test listing services successfully via gcloud CLI."""
        # gcloud returns Knative format
        mock_gcloud_response = [
            {
                "metadata": {
                    "name": "service-1",
                    "namespace": "123456789",
                    "creationTimestamp": "2025-01-21T21:14:21.483114Z",
                    "labels": {
                        "cloud.googleapis.com/location": "us-east1",
                        "env": "prod",
                    },
                },
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{"image": "gcr.io/test-project/image:v1"}]
                        }
                    },
                    "traffic": [{"percent": 100, "latestRevision": True}],
                },
                "status": {
                    "url": "https://service-1-abc.run.app",
                    "conditions": [{"type": "Ready", "status": "True"}],
                },
            },
            {
                "metadata": {
                    "name": "service-2",
                    "namespace": "123456789",
                    "creationTimestamp": "2025-01-22T10:00:00.000000Z",
                    "labels": {"cloud.googleapis.com/location": "us-west1"},
                },
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{"image": "gcr.io/test-project/image:v2"}]
                        }
                    },
                    "traffic": [{"percent": 70}, {"percent": 30}],
                },
                "status": {
                    "url": "https://service-2-xyz.run.app",
                    "conditions": [{"type": "Ready", "status": "True"}],
                },
            },
        ]

        with patch.object(
            cloudrun_service, "_run_gcloud_command", return_value=mock_gcloud_response
        ):
            services = await cloudrun_service.list_services(
                "test-project", use_cache=False
            )

            assert len(services) == 2
            assert isinstance(services[0], CloudRunService)
            assert services[0].service_name == "service-1"
            assert services[0].region == "us-east1"
            assert services[0].url == "https://service-1-abc.run.app"
            assert services[0].image == "gcr.io/test-project/image:v1"
            assert services[0].status == "READY"
            assert services[0].traffic_percent == 100
            assert services[0].labels_count == 2
            assert services[1].service_name == "service-2"
            assert services[1].region == "us-west1"
            assert services[1].traffic_percent == 100  # 70 + 30

    @pytest.mark.asyncio
    async def test_list_services_empty(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test listing services when none exist."""
        with patch.object(cloudrun_service, "_run_gcloud_command", return_value=[]):
            services = await cloudrun_service.list_services(
                "test-project", use_cache=False
            )

            assert len(services) == 0

    @pytest.mark.asyncio
    async def test_list_services_error_returns_empty(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that errors return empty list."""
        with patch.object(
            cloudrun_service,
            "_run_gcloud_command",
            side_effect=Exception("gcloud error"),
        ):
            services = await cloudrun_service.list_services(
                "test-project", use_cache=False
            )

            assert services == []

    @pytest.mark.asyncio
    async def test_list_services_with_cache(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that list_services uses cache when available."""
        mock_cached_services = [
            CloudRunService(
                id="cached-service",
                name="cached-service",
                service_name="cached-service",
            )
        ]

        # Mock the cache to return cached data
        with patch.object(
            cloudrun_service._cache, "get", return_value=mock_cached_services
        ):
            services = await cloudrun_service.list_services(
                "test-project", use_cache=True
            )

            assert len(services) == 1
            assert services[0].service_name == "cached-service"

    @pytest.mark.asyncio
    async def test_list_jobs_success(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test listing jobs successfully via gcloud CLI."""
        # gcloud returns Cloud Run v1 format for jobs
        mock_gcloud_response = [
            {
                "metadata": {
                    "name": "job-1",
                    "namespace": "123456789",
                    "creationTimestamp": "2025-09-11T21:44:18.800633Z",
                    "labels": {
                        "cloud.googleapis.com/location": "us-east1",
                        "type": "batch",
                    },
                },
                "spec": {
                    "template": {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [
                                        {"image": "gcr.io/test-project/batch:v1"}
                                    ]
                                }
                            }
                        }
                    }
                },
                "status": {
                    "conditions": [{"type": "Ready", "status": "True"}],
                    "executionCount": 5,
                    "latestCreatedExecution": {
                        "name": "job-1-exec-5",
                        "creationTime": "2025-09-11T22:00:00.000000Z",
                    },
                },
            },
            {
                "metadata": {
                    "name": "job-2",
                    "namespace": "123456789",
                    "creationTimestamp": "2025-09-12T10:00:00.000000Z",
                    "labels": {"cloud.googleapis.com/location": "us-west1"},
                },
                "spec": {
                    "template": {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [
                                        {"image": "gcr.io/test-project/etl:v2"}
                                    ]
                                }
                            }
                        }
                    }
                },
                "status": {
                    "conditions": [{"type": "Ready", "status": "True"}],
                    "executionCount": 12,
                },
            },
        ]

        with patch.object(
            cloudrun_service, "_run_gcloud_command", return_value=mock_gcloud_response
        ):
            jobs = await cloudrun_service.list_jobs("test-project", use_cache=False)

            assert len(jobs) == 2
            assert isinstance(jobs[0], CloudRunJob)
            assert jobs[0].job_name == "job-1"
            assert jobs[0].region == "us-east1"
            assert jobs[0].image == "gcr.io/test-project/batch:v1"
            assert jobs[0].status == "READY"
            assert jobs[0].execution_count == 5
            assert jobs[0].last_execution_time is not None
            assert jobs[0].labels_count == 2
            assert jobs[1].job_name == "job-2"
            assert jobs[1].region == "us-west1"
            assert jobs[1].execution_count == 12

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test listing jobs when none exist."""
        with patch.object(cloudrun_service, "_run_gcloud_command", return_value=[]):
            jobs = await cloudrun_service.list_jobs("test-project", use_cache=False)

            assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_list_jobs_error_returns_empty(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that errors return empty list."""
        with patch.object(
            cloudrun_service,
            "_run_gcloud_command",
            side_effect=Exception("gcloud error"),
        ):
            jobs = await cloudrun_service.list_jobs("test-project", use_cache=False)

            assert jobs == []

    @pytest.mark.asyncio
    async def test_list_jobs_with_cache(
        self, cloudrun_service: CloudRunServiceClass
    ) -> None:
        """Test that list_jobs uses cache when available."""
        mock_cached_jobs = [
            CloudRunJob(
                id="cached-job",
                name="cached-job",
                job_name="cached-job",
            )
        ]

        # Mock the cache to return cached data
        with patch.object(
            cloudrun_service._cache, "get", return_value=mock_cached_jobs
        ):
            jobs = await cloudrun_service.list_jobs("test-project", use_cache=True)

            assert len(jobs) == 1
            assert jobs[0].job_name == "cached-job"

    @pytest.mark.asyncio
    async def test_get_cloudrun_service_singleton(self) -> None:
        """Test that get_cloudrun_service returns singleton."""
        service1 = await get_cloudrun_service()
        service2 = await get_cloudrun_service()

        assert service1 is service2
