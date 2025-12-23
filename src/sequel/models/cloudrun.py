"""Google Cloud Run models for services and jobs."""

from datetime import datetime
from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class CloudRunService(BaseModel):
    """Model for a Google Cloud Run service.

    Represents a Cloud Run service with metadata.
    """

    service_name: str = Field(..., description="Service name")
    url: str | None = Field(None, description="Service URL")
    image: str | None = Field(None, description="Container image")
    status: str | None = Field(None, description="Service status")
    region: str | None = Field(None, description="Service region")
    traffic_percent: int = Field(default=100, description="Traffic allocation percentage")
    labels_count: int = Field(default=0, description="Number of labels")
    last_modified: datetime | None = Field(None, description="Last modification time")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "CloudRunService":
        """Create CloudRunService from Cloud Run API response.

        Args:
            data: API response data from services.get()

        Returns:
            CloudRunService instance

        Example API response structure:
            {
                "name": "projects/123/locations/us-central1/services/my-service",
                "uid": "abc123",
                "createTime": "2023-01-01T00:00:00.000000Z",
                "updateTime": "2023-01-02T00:00:00.000000Z",
                "template": {
                    "containers": [
                        {
                            "image": "gcr.io/project/image:tag"
                        }
                    ]
                },
                "traffic": [
                    {
                        "percent": 100,
                        "latestRevision": true
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
                    "env": "prod"
                }
            }
        """
        # Extract service name from full resource path
        # Format: projects/{project}/locations/{location}/services/{service}
        full_name = data.get("name", "")
        service_name = full_name.split("/")[-1] if "/" in full_name else full_name

        # Extract region from name
        region = None
        if "locations/" in full_name:
            parts = full_name.split("/")
            try:
                location_idx = parts.index("locations")
                region = parts[location_idx + 1]
            except (ValueError, IndexError):
                pass

        # Extract project_id from name
        project_id = None
        if "projects/" in full_name:
            parts = full_name.split("/")
            try:
                project_idx = parts.index("projects")
                project_id = parts[project_idx + 1]
            except (ValueError, IndexError):
                pass

        # Extract container image from template
        image = None
        template = data.get("template", {})
        if isinstance(template, dict):
            containers = template.get("containers", [])
            if containers and isinstance(containers, list):
                image = containers[0].get("image")

        # Calculate traffic allocation (sum of all traffic percents)
        traffic_percent = 0
        traffic = data.get("traffic", [])
        if isinstance(traffic, list):
            for route in traffic:
                if isinstance(route, dict):
                    traffic_percent += route.get("percent", 0)

        # Determine status from conditions
        status = "UNKNOWN"
        conditions = data.get("conditions", [])
        if isinstance(conditions, list):
            for condition in conditions:
                if isinstance(condition, dict) and condition.get("type") == "Ready":
                    state = condition.get("state", "")
                    if state == "CONDITION_SUCCEEDED":
                        status = "READY"
                    elif state == "CONDITION_FAILED":
                        status = "FAILED"
                    else:
                        status = state
                    break

        # Count labels
        labels_count = 0
        labels = data.get("labels", {})
        if isinstance(labels, dict):
            labels_count = len(labels)

        # Parse timestamps
        created_at = None
        if "createTime" in data:
            try:
                timestamp = data["createTime"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        last_modified = None
        if "updateTime" in data:
            try:
                timestamp = data["updateTime"].replace("Z", "+00:00")
                last_modified = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        return cls(
            id=service_name,
            name=service_name,
            project_id=project_id,
            created_at=created_at,
            service_name=service_name,
            url=data.get("uri"),
            image=image,
            status=status,
            region=region,
            traffic_percent=traffic_percent,
            labels_count=labels_count,
            last_modified=last_modified,
            raw_data=data.copy(),
        )


class CloudRunJob(BaseModel):
    """Model for a Google Cloud Run job.

    Represents a Cloud Run job with metadata.
    """

    job_name: str = Field(..., description="Job name")
    image: str | None = Field(None, description="Container image")
    status: str | None = Field(None, description="Job status")
    region: str | None = Field(None, description="Job region")
    execution_count: int = Field(default=0, description="Total number of executions")
    last_execution_time: datetime | None = Field(
        None, description="Last execution time"
    )
    labels_count: int = Field(default=0, description="Number of labels")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "CloudRunJob":
        """Create CloudRunJob from Cloud Run API response.

        Args:
            data: API response data from jobs.get()

        Returns:
            CloudRunJob instance

        Example API response structure:
            {
                "name": "projects/123/locations/us-central1/jobs/my-job",
                "uid": "abc123",
                "createTime": "2023-01-01T00:00:00.000000Z",
                "updateTime": "2023-01-02T00:00:00.000000Z",
                "template": {
                    "template": {
                        "containers": [
                            {
                                "image": "gcr.io/project/image:tag"
                            }
                        ]
                    }
                },
                "latestCreatedExecution": {
                    "name": "my-job-abc123",
                    "createTime": "2023-01-03T00:00:00.000000Z"
                },
                "executionCount": 5,
                "conditions": [
                    {
                        "type": "Ready",
                        "state": "CONDITION_SUCCEEDED"
                    }
                ],
                "labels": {
                    "env": "prod"
                }
            }
        """
        # Extract job name from full resource path
        # Format: projects/{project}/locations/{location}/jobs/{job}
        full_name = data.get("name", "")
        job_name = full_name.split("/")[-1] if "/" in full_name else full_name

        # Extract region from name
        region = None
        if "locations/" in full_name:
            parts = full_name.split("/")
            try:
                location_idx = parts.index("locations")
                region = parts[location_idx + 1]
            except (ValueError, IndexError):
                pass

        # Extract project_id from name
        project_id = None
        if "projects/" in full_name:
            parts = full_name.split("/")
            try:
                project_idx = parts.index("projects")
                project_id = parts[project_idx + 1]
            except (ValueError, IndexError):
                pass

        # Extract container image from template
        image = None
        template = data.get("template", {})
        if isinstance(template, dict):
            task_template = template.get("template", {})
            if isinstance(task_template, dict):
                containers = task_template.get("containers", [])
                if containers and isinstance(containers, list):
                    image = containers[0].get("image")

        # Get execution count
        execution_count = data.get("executionCount", 0)

        # Get last execution time
        last_execution_time = None
        latest_execution = data.get("latestCreatedExecution", {})
        if isinstance(latest_execution, dict) and "createTime" in latest_execution:
            try:
                timestamp = latest_execution["createTime"].replace("Z", "+00:00")
                last_execution_time = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        # Determine status from conditions
        status = "UNKNOWN"
        conditions = data.get("conditions", [])
        if isinstance(conditions, list):
            for condition in conditions:
                if isinstance(condition, dict) and condition.get("type") == "Ready":
                    state = condition.get("state", "")
                    if state == "CONDITION_SUCCEEDED":
                        status = "READY"
                    elif state == "CONDITION_FAILED":
                        status = "FAILED"
                    else:
                        status = state
                    break

        # Count labels
        labels_count = 0
        labels = data.get("labels", {})
        if isinstance(labels, dict):
            labels_count = len(labels)

        # Parse creation timestamp
        created_at = None
        if "createTime" in data:
            try:
                timestamp = data["createTime"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        return cls(
            id=job_name,
            name=job_name,
            project_id=project_id,
            created_at=created_at,
            job_name=job_name,
            image=image,
            status=status,
            region=region,
            execution_count=execution_count,
            last_execution_time=last_execution_time,
            labels_count=labels_count,
            raw_data=data.copy(),
        )
