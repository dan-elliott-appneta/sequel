"""Google Cloud Monitoring models."""

from datetime import datetime
from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class AlertPolicy(BaseModel):
    """Model for a Cloud Monitoring alert policy.

    Represents an alerting policy with conditions and notification channels.
    """

    policy_name: str = Field(..., description="Alert policy name")
    display_name: str | None = Field(None, description="Human-readable display name")
    enabled: bool = Field(default=True, description="Whether policy is enabled")
    condition_count: int = Field(default=0, description="Number of alert conditions")
    notification_channel_count: int = Field(
        default=0, description="Number of notification channels"
    )
    combiner: str | None = Field(None, description="How conditions are combined")
    documentation_content: str | None = Field(
        None, description="Documentation/runbook content"
    )

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "AlertPolicy":
        """Create AlertPolicy from Cloud Monitoring API response.

        Args:
            data: API response data from alertPolicies.list()

        Returns:
            AlertPolicy instance

        Example API response structure:
            {
                "name": "projects/my-project/alertPolicies/1234567890",
                "displayName": "High CPU Usage",
                "enabled": true,
                "conditions": [
                    {
                        "name": "projects/my-project/alertPolicies/1234567890/conditions/5678",
                        "displayName": "CPU usage above 80%",
                        "conditionThreshold": {
                            "filter": "metric.type=\"compute.googleapis.com/instance/cpu/utilization\"",
                            "comparison": "COMPARISON_GT",
                            "thresholdValue": 0.8,
                            "duration": "60s"
                        }
                    }
                ],
                "combiner": "OR",
                "notificationChannels": [
                    "projects/my-project/notificationChannels/9876543210"
                ],
                "documentation": {
                    "content": "Check the instance and consider scaling.",
                    "mimeType": "text/markdown"
                },
                "creationRecord": {
                    "mutateTime": "2023-01-01T00:00:00.000Z",
                    "mutatedBy": "user@example.com"
                },
                "mutationRecord": {
                    "mutateTime": "2023-06-01T00:00:00.000Z",
                    "mutatedBy": "user@example.com"
                }
            }
        """
        # Extract policy name from full resource name
        # Format: projects/[PROJECT_ID]/alertPolicies/[POLICY_ID]
        full_name = data.get("name", "")
        policy_name = full_name.split("/")[-1] if "/" in full_name else full_name

        # Extract project_id from full resource name
        project_id = None
        if "projects/" in full_name:
            parts = full_name.split("/")
            if len(parts) >= 2:
                project_id = parts[1]

        # Get display name (fallback to name if not provided)
        display_name = data.get("displayName", policy_name)

        # Check if policy is enabled
        enabled = data.get("enabled", True)

        # Count conditions
        conditions = data.get("conditions", [])
        condition_count = len(conditions) if isinstance(conditions, list) else 0

        # Count notification channels
        notification_channels = data.get("notificationChannels", [])
        notification_channel_count = (
            len(notification_channels) if isinstance(notification_channels, list) else 0
        )

        # Get combiner (how conditions are combined)
        combiner = data.get("combiner")

        # Extract documentation content
        documentation_content = None
        documentation = data.get("documentation", {})
        if isinstance(documentation, dict):
            documentation_content = documentation.get("content")

        # Parse creation timestamp from creationRecord
        created_at = None
        creation_record = data.get("creationRecord", {})
        if isinstance(creation_record, dict) and "mutateTime" in creation_record:
            try:
                # Cloud Monitoring timestamps are in RFC 3339 format
                timestamp = creation_record["mutateTime"].replace("Z", "+00:00")
                created_at = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass

        return cls(
            id=policy_name,
            name=display_name or policy_name,
            project_id=project_id,
            created_at=created_at,
            policy_name=policy_name,
            display_name=display_name,
            enabled=enabled,
            condition_count=condition_count,
            notification_channel_count=notification_channel_count,
            combiner=combiner,
            documentation_content=documentation_content,
            raw_data=data.copy(),
        )

    def is_enabled(self) -> bool:
        """Check if alert policy is enabled.

        Returns:
            True if policy is enabled, False otherwise
        """
        return self.enabled

    def get_condition_summary(self) -> str:
        """Get a summary of the alert conditions.

        Returns:
            Summary string describing the conditions
        """
        if self.condition_count == 0:
            return "No conditions"
        elif self.condition_count == 1:
            return "1 condition"
        else:
            combiner_text = f" ({self.combiner})" if self.combiner else ""
            return f"{self.condition_count} conditions{combiner_text}"
