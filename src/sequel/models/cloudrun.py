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

    @classmethod
    def from_gcloud_response(cls, data: dict[str, Any]) -> "CloudRunService":
        """Create CloudRunService from gcloud CLI response.

        Args:
            data: JSON response from 'gcloud run services list --format=json'

        Returns:
            CloudRunService instance

        Example gcloud response structure (Knative format):
            {
                "metadata": {
                    "name": "my-service",
                    "namespace": "1234567890",
                    "creationTimestamp": "2025-01-21T21:14:21.483114Z",
                    "labels": {
                        "cloud.googleapis.com/location": "us-east1"
                    }
                },
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "image": "gcr.io/project/image:tag"
                            }]
                        }
                    },
                    "traffic": [{
                        "percent": 100,
                        "latestRevision": true
                    }]
                },
                "status": {
                    "url": "https://my-service-abc.run.app",
                    "conditions": [{
                        "type": "Ready",
                        "status": "True"
                    }]
                }
            }
        """
        metadata = data.get("metadata", {})
        spec = data.get("spec", {})
        status_obj = data.get("status", {})

        # Extract service name
        service_name = metadata.get("name", "")

        # Extract region from labels
        labels = metadata.get("labels", {})
        region = labels.get("cloud.googleapis.com/location")

        # Extract project_id from namespace
        project_id = metadata.get("namespace")

        # Extract container image from spec
        image = None
        template = spec.get("template", {})
        if isinstance(template, dict):
            template_spec = template.get("spec", {})
            if isinstance(template_spec, dict):
                containers = template_spec.get("containers", [])
                if containers and isinstance(containers, list):
                    image = containers[0].get("image")

        # Calculate traffic allocation
        traffic_percent = 0
        traffic = spec.get("traffic", [])
        if isinstance(traffic, list):
            for route in traffic:
                if isinstance(route, dict):
                    traffic_percent += route.get("percent", 0)

        # Determine status from conditions
        status = "UNKNOWN"
        conditions = status_obj.get("conditions", [])
        if isinstance(conditions, list):
            for condition in conditions:
                if isinstance(condition, dict) and condition.get("type") == "Ready":
                    cond_status = condition.get("status", "")
                    if cond_status == "True":
                        status = "READY"
                    elif cond_status == "False":
                        status = "FAILED"
                    break

        # Count labels
        labels_count = len(labels) if isinstance(labels, dict) else 0

        # Parse creation timestamp
        created_at = None
        last_modified = None
        if "creationTimestamp" in metadata:
            try:
                timestamp = metadata["creationTimestamp"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
                last_modified = created_at  # Use creation time as last modified
            except (ValueError, AttributeError):
                pass

        # Extract URL
        url = status_obj.get("url")

        return cls(
            id=service_name,
            name=service_name,
            project_id=project_id,
            created_at=created_at,
            service_name=service_name,
            url=url,
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

    @classmethod
    def from_gcloud_response(cls, data: dict[str, Any]) -> "CloudRunJob":
        """Create CloudRunJob from gcloud CLI response.

        Args:
            data: JSON response from 'gcloud run jobs list --format=json'

        Returns:
            CloudRunJob instance

        Example gcloud response structure:
            {
                "metadata": {
                    "name": "my-job",
                    "namespace": "1234567890",
                    "creationTimestamp": "2025-09-11T21:44:18.800633Z",
                    "labels": {
                        "cloud.googleapis.com/location": "us-east1"
                    }
                },
                "spec": {
                    "template": {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [{
                                        "image": "gcr.io/project/image:tag"
                                    }]
                                }
                            }
                        }
                    }
                },
                "status": {
                    "conditions": [{
                        "type": "Ready",
                        "status": "True"
                    }],
                    "executionCount": 5,
                    "latestCreatedExecution": {
                        "name": "my-job-abc",
                        "creationTime": "2025-09-11T22:00:00.000000Z"
                    }
                }
            }
        """
        metadata = data.get("metadata", {})
        spec = data.get("spec", {})
        status_obj = data.get("status", {})

        # Extract job name
        job_name = metadata.get("name", "")

        # Extract region from labels
        labels = metadata.get("labels", {})
        region = labels.get("cloud.googleapis.com/location")

        # Extract project_id from namespace
        project_id = metadata.get("namespace")

        # Extract container image from deeply nested spec
        image = None
        template = spec.get("template", {})
        if isinstance(template, dict):
            template_spec = template.get("spec", {})
            if isinstance(template_spec, dict):
                task_template = template_spec.get("template", {})
                if isinstance(task_template, dict):
                    task_spec = task_template.get("spec", {})
                    if isinstance(task_spec, dict):
                        containers = task_spec.get("containers", [])
                        if containers and isinstance(containers, list):
                            image = containers[0].get("image")

        # Get execution count from status
        execution_count = status_obj.get("executionCount", 0)

        # Get last execution time from status
        last_execution_time = None
        latest_execution = status_obj.get("latestCreatedExecution", {})
        if isinstance(latest_execution, dict) and "creationTime" in latest_execution:
            try:
                timestamp = latest_execution["creationTime"].replace("Z", "+00:00")
                last_execution_time = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        # Determine status from conditions
        status = "UNKNOWN"
        conditions = status_obj.get("conditions", [])
        if isinstance(conditions, list):
            for condition in conditions:
                if isinstance(condition, dict) and condition.get("type") == "Ready":
                    cond_status = condition.get("status", "")
                    if cond_status == "True":
                        status = "READY"
                    elif cond_status == "False":
                        status = "FAILED"
                    break

        # Count labels
        labels_count = len(labels) if isinstance(labels, dict) else 0

        # Parse creation timestamp
        created_at = None
        if "creationTimestamp" in metadata:
            try:
                timestamp = metadata["creationTimestamp"].replace("Z", "+00:00")
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
