"""Pub/Sub models."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class Topic(BaseModel):
    """Represents a Pub/Sub topic."""

    topic_name: str = Field(..., description="Topic name")
    labels_count: int = Field(default=0, description="Number of labels")
    schema_name: str | None = Field(None, description="Schema name if using schema")
    message_retention_duration: str | None = Field(
        None, description="Message retention duration"
    )
    kms_key_name: str | None = Field(None, description="KMS key name if encrypted")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Topic":
        """Create Topic from Pub/Sub API response.

        Args:
            data: API response data from topics.get()

        Returns:
            Topic instance

        Example API response structure:
            {
                "name": "projects/my-project/topics/my-topic",
                "labels": {
                    "env": "prod"
                },
                "messageRetentionDuration": "86400s",
                "schemaSettings": {
                    "schema": "projects/my-project/schemas/my-schema",
                    "encoding": "JSON"
                },
                "kmsKeyName": "projects/my-project/locations/us/keyRings/my-ring/cryptoKeys/my-key"
            }
        """
        # Extract topic name from full resource path
        # Format: "projects/{project}/topics/{topic}"
        full_name = data.get("name", "")
        topic_name = full_name.split("/")[-1] if "/" in full_name else full_name

        # Extract project_id from full name
        project_id = None
        if "projects/" in full_name:
            parts = full_name.split("/")
            try:
                project_idx = parts.index("projects")
                project_id = parts[project_idx + 1]
            except (ValueError, IndexError):
                pass

        # Count labels
        labels_count = 0
        labels = data.get("labels", {})
        if isinstance(labels, dict):
            labels_count = len(labels)

        # Extract schema name if present
        schema_name = None
        schema_settings = data.get("schemaSettings", {})
        if isinstance(schema_settings, dict):
            schema_full_name = schema_settings.get("schema", "")
            if schema_full_name:  # Only set if non-empty
                schema_name = (
                    schema_full_name.split("/")[-1] if "/" in schema_full_name else schema_full_name
                )

        return cls(
            id=topic_name,
            name=topic_name,
            project_id=project_id,
            created_at=None,
            topic_name=topic_name,
            labels_count=labels_count,
            schema_name=schema_name,
            message_retention_duration=data.get("messageRetentionDuration"),
            kms_key_name=data.get("kmsKeyName"),
            raw_data=data.copy(),
        )


class Subscription(BaseModel):
    """Represents a Pub/Sub subscription."""

    subscription_name: str = Field(..., description="Subscription name")
    topic_name: str = Field(..., description="Parent topic name")
    ack_deadline_seconds: int = Field(default=10, description="Acknowledgment deadline in seconds")
    retain_acked_messages: bool = Field(
        default=False, description="Whether to retain acknowledged messages"
    )
    message_retention_duration: str | None = Field(
        None, description="Message retention duration"
    )
    labels_count: int = Field(default=0, description="Number of labels")
    push_endpoint: str | None = Field(None, description="Push endpoint if push subscription")
    filter_expression: str | None = Field(None, description="Message filter expression")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Subscription":
        """Create Subscription from Pub/Sub API response.

        Args:
            data: API response data from subscriptions.get()

        Returns:
            Subscription instance

        Example API response structure:
            {
                "name": "projects/my-project/subscriptions/my-subscription",
                "topic": "projects/my-project/topics/my-topic",
                "pushConfig": {
                    "pushEndpoint": "https://example.com/push"
                },
                "ackDeadlineSeconds": 10,
                "retainAckedMessages": false,
                "messageRetentionDuration": "604800s",
                "labels": {
                    "env": "prod"
                },
                "filter": "attributes.event_type = \"order\""
            }
        """
        # Extract subscription name from full resource path
        # Format: "projects/{project}/subscriptions/{subscription}"
        full_name = data.get("name", "")
        subscription_name = full_name.split("/")[-1] if "/" in full_name else full_name

        # Extract topic name from full topic path
        # Format: "projects/{project}/topics/{topic}"
        topic_full_name = data.get("topic", "")
        topic_name = topic_full_name.split("/")[-1] if "/" in topic_full_name else topic_full_name

        # Extract project_id from full name
        project_id = None
        if "projects/" in full_name:
            parts = full_name.split("/")
            try:
                project_idx = parts.index("projects")
                project_id = parts[project_idx + 1]
            except (ValueError, IndexError):
                pass

        # Count labels
        labels_count = 0
        labels = data.get("labels", {})
        if isinstance(labels, dict):
            labels_count = len(labels)

        # Extract push endpoint if present
        push_endpoint = None
        push_config = data.get("pushConfig", {})
        if isinstance(push_config, dict):
            push_endpoint = push_config.get("pushEndpoint")

        return cls(
            id=subscription_name,
            name=subscription_name,
            project_id=project_id,
            created_at=None,
            subscription_name=subscription_name,
            topic_name=topic_name,
            ack_deadline_seconds=data.get("ackDeadlineSeconds", 10),
            retain_acked_messages=data.get("retainAckedMessages", False),
            message_retention_duration=data.get("messageRetentionDuration"),
            labels_count=labels_count,
            push_endpoint=push_endpoint,
            filter_expression=data.get("filter"),
            raw_data=data.copy(),
        )

    def is_push(self) -> bool:
        """Check if this is a push subscription.

        Returns:
            True if push subscription, False if pull
        """
        return self.push_endpoint is not None

    def get_subscription_type(self) -> str:
        """Get the subscription type as a display string.

        Returns:
            "Push" or "Pull"
        """
        return "Push" if self.is_push() else "Pull"
