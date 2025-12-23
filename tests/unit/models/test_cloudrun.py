"""Unit tests for Cloud Run models."""

from datetime import datetime
from typing import Any

from sequel.models.cloudrun import CloudRunJob, CloudRunService


class TestCloudRunService:
    """Tests for CloudRunService model."""

    def test_create_service(self) -> None:
        """Test creating a Cloud Run service instance."""
        service = CloudRunService(
            id="my-service",
            name="my-service",
            service_name="my-service",
            url="https://my-service-abc123-uc.a.run.app",
            image="gcr.io/project/image:tag",
            status="READY",
            region="us-central1",
            traffic_percent=100,
            labels_count=2,
        )

        assert service.id == "my-service"
        assert service.service_name == "my-service"
        assert service.url == "https://my-service-abc123-uc.a.run.app"
        assert service.image == "gcr.io/project/image:tag"
        assert service.status == "READY"
        assert service.region == "us-central1"
        assert service.traffic_percent == 100
        assert service.labels_count == 2

    def test_from_api_response_full(self) -> None:
        """Test creating service from full API response."""
        data = {
            "name": "projects/test-project/locations/us-central1/services/my-service",
            "uid": "abc123",
            "createTime": "2023-01-01T00:00:00.000000Z",
            "updateTime": "2023-01-02T00:00:00.000000Z",
            "template": {
                "containers": [
                    {
                        "image": "gcr.io/test-project/my-image:v1.0.0"
                    }
                ]
            },
            "traffic": [
                {
                    "percent": 100,
                    "latestRevision": True
                }
            ],
            "uri": "https://my-service-abc123-uc.a.run.app",
            "conditions": [
                {
                    "type": "Ready",
                    "state": "CONDITION_SUCCEEDED"
                }
            ],
            "labels": {
                "env": "prod",
                "team": "platform"
            }
        }

        service = CloudRunService.from_api_response(data)

        assert service.service_name == "my-service"
        assert service.project_id == "test-project"
        assert service.region == "us-central1"
        assert service.url == "https://my-service-abc123-uc.a.run.app"
        assert service.image == "gcr.io/test-project/my-image:v1.0.0"
        assert service.status == "READY"
        assert service.traffic_percent == 100
        assert service.labels_count == 2
        assert service.created_at is not None
        assert service.last_modified is not None
        assert service.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating service from minimal API response."""
        data: dict[str, Any] = {
            "name": "projects/123/locations/us-east1/services/minimal-service",
        }

        service = CloudRunService.from_api_response(data)

        assert service.service_name == "minimal-service"
        assert service.project_id == "123"
        assert service.region == "us-east1"
        assert service.url is None
        assert service.image is None
        assert service.status == "UNKNOWN"
        assert service.traffic_percent == 0
        assert service.labels_count == 0
        assert service.created_at is None
        assert service.last_modified is None

    def test_from_api_response_split_traffic(self) -> None:
        """Test creating service with split traffic."""
        data = {
            "name": "projects/test/locations/us-west1/services/test-service",
            "traffic": [
                {"percent": 70, "revisionName": "test-service-rev1"},
                {"percent": 30, "revisionName": "test-service-rev2"}
            ],
        }

        service = CloudRunService.from_api_response(data)

        # Traffic percent should be sum of all routes
        assert service.traffic_percent == 100

    def test_from_api_response_failed_status(self) -> None:
        """Test creating service with failed status."""
        data = {
            "name": "projects/test/locations/us-west1/services/failed-service",
            "conditions": [
                {
                    "type": "Ready",
                    "state": "CONDITION_FAILED"
                }
            ],
        }

        service = CloudRunService.from_api_response(data)

        assert service.status == "FAILED"

    def test_from_api_response_no_conditions(self) -> None:
        """Test creating service with no conditions."""
        data = {
            "name": "projects/test/locations/us-west1/services/test-service",
        }

        service = CloudRunService.from_api_response(data)

        assert service.status == "UNKNOWN"

    def test_from_api_response_multiple_containers(self) -> None:
        """Test creating service with multiple containers (uses first)."""
        data = {
            "name": "projects/test/locations/us-west1/services/multi-container",
            "template": {
                "containers": [
                    {"image": "gcr.io/project/primary:v1"},
                    {"image": "gcr.io/project/sidecar:v1"}
                ]
            },
        }

        service = CloudRunService.from_api_response(data)

        # Should use first container
        assert service.image == "gcr.io/project/primary:v1"

    def test_from_api_response_invalid_timestamp(self) -> None:
        """Test creating service with invalid timestamp."""
        data = {
            "name": "projects/test/locations/us-west1/services/test-service",
            "createTime": "invalid-timestamp",
            "updateTime": "also-invalid",
        }

        service = CloudRunService.from_api_response(data)

        # Should handle invalid timestamps gracefully
        assert service.created_at is None
        assert service.last_modified is None

    def test_from_api_response_empty_labels(self) -> None:
        """Test creating service with empty labels."""
        data = {
            "name": "projects/test/locations/us-west1/services/test-service",
            "labels": {},
        }

        service = CloudRunService.from_api_response(data)

        assert service.labels_count == 0

    def test_from_api_response_path_without_slashes(self) -> None:
        """Test creating service from name without slashes."""
        data = {
            "name": "simple-service-name",
        }

        service = CloudRunService.from_api_response(data)

        assert service.service_name == "simple-service-name"
        assert service.project_id is None
        assert service.region is None


class TestCloudRunJob:
    """Tests for CloudRunJob model."""

    def test_create_job(self) -> None:
        """Test creating a Cloud Run job instance."""
        job = CloudRunJob(
            id="my-job",
            name="my-job",
            job_name="my-job",
            image="gcr.io/project/job-image:tag",
            status="READY",
            region="us-central1",
            execution_count=5,
            labels_count=1,
        )

        assert job.id == "my-job"
        assert job.job_name == "my-job"
        assert job.image == "gcr.io/project/job-image:tag"
        assert job.status == "READY"
        assert job.region == "us-central1"
        assert job.execution_count == 5
        assert job.labels_count == 1

    def test_from_api_response_full(self) -> None:
        """Test creating job from full API response."""
        data = {
            "name": "projects/test-project/locations/us-central1/jobs/my-job",
            "uid": "xyz789",
            "createTime": "2023-01-01T00:00:00.000000Z",
            "updateTime": "2023-01-02T00:00:00.000000Z",
            "template": {
                "template": {
                    "containers": [
                        {
                            "image": "gcr.io/test-project/batch-job:v2.0.0"
                        }
                    ]
                }
            },
            "latestCreatedExecution": {
                "name": "my-job-exec-abc123",
                "createTime": "2023-01-03T00:00:00.000000Z"
            },
            "executionCount": 12,
            "conditions": [
                {
                    "type": "Ready",
                    "state": "CONDITION_SUCCEEDED"
                }
            ],
            "labels": {
                "type": "batch"
            }
        }

        job = CloudRunJob.from_api_response(data)

        assert job.job_name == "my-job"
        assert job.project_id == "test-project"
        assert job.region == "us-central1"
        assert job.image == "gcr.io/test-project/batch-job:v2.0.0"
        assert job.status == "READY"
        assert job.execution_count == 12
        assert job.last_execution_time is not None
        assert job.labels_count == 1
        assert job.created_at is not None
        assert job.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating job from minimal API response."""
        data: dict[str, Any] = {
            "name": "projects/456/locations/europe-west1/jobs/minimal-job",
        }

        job = CloudRunJob.from_api_response(data)

        assert job.job_name == "minimal-job"
        assert job.project_id == "456"
        assert job.region == "europe-west1"
        assert job.image is None
        assert job.status == "UNKNOWN"
        assert job.execution_count == 0
        assert job.last_execution_time is None
        assert job.labels_count == 0
        assert job.created_at is None

    def test_from_api_response_no_executions(self) -> None:
        """Test creating job that has never been executed."""
        data = {
            "name": "projects/test/locations/us-west1/jobs/new-job",
            "executionCount": 0,
        }

        job = CloudRunJob.from_api_response(data)

        assert job.execution_count == 0
        assert job.last_execution_time is None

    def test_from_api_response_failed_status(self) -> None:
        """Test creating job with failed status."""
        data = {
            "name": "projects/test/locations/us-west1/jobs/failed-job",
            "conditions": [
                {
                    "type": "Ready",
                    "state": "CONDITION_FAILED"
                }
            ],
        }

        job = CloudRunJob.from_api_response(data)

        assert job.status == "FAILED"

    def test_from_api_response_nested_template(self) -> None:
        """Test creating job with nested template structure."""
        data = {
            "name": "projects/test/locations/us-west1/jobs/test-job",
            "template": {
                "template": {
                    "containers": [
                        {"image": "gcr.io/project/job:v1"}
                    ]
                }
            },
        }

        job = CloudRunJob.from_api_response(data)

        assert job.image == "gcr.io/project/job:v1"

    def test_from_api_response_invalid_template(self) -> None:
        """Test creating job with invalid template structure."""
        data = {
            "name": "projects/test/locations/us-west1/jobs/test-job",
            "template": {
                # Missing nested template
                "containers": [
                    {"image": "gcr.io/project/job:v1"}
                ]
            },
        }

        job = CloudRunJob.from_api_response(data)

        # Should handle invalid structure gracefully
        assert job.image is None

    def test_from_api_response_invalid_execution_time(self) -> None:
        """Test creating job with invalid execution timestamp."""
        data = {
            "name": "projects/test/locations/us-west1/jobs/test-job",
            "latestCreatedExecution": {
                "name": "test-job-exec-1",
                "createTime": "not-a-timestamp"
            },
        }

        job = CloudRunJob.from_api_response(data)

        # Should handle invalid timestamp gracefully
        assert job.last_execution_time is None

    def test_from_api_response_empty_labels(self) -> None:
        """Test creating job with empty labels."""
        data = {
            "name": "projects/test/locations/us-west1/jobs/test-job",
            "labels": {},
        }

        job = CloudRunJob.from_api_response(data)

        assert job.labels_count == 0

    def test_from_api_response_path_without_slashes(self) -> None:
        """Test creating job from name without slashes."""
        data = {
            "name": "simple-job-name",
        }

        job = CloudRunJob.from_api_response(data)

        assert job.job_name == "simple-job-name"
        assert job.project_id is None
        assert job.region is None
