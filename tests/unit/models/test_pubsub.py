"""Unit tests for Pub/Sub models."""

from typing import Any

from sequel.models.pubsub import Subscription, Topic


class TestTopic:
    """Tests for Topic model."""

    def test_create_topic(self) -> None:
        """Test creating a topic instance."""
        topic = Topic(
            id="my-topic",
            name="my-topic",
            topic_name="my-topic",
            labels_count=2,
            schema_name="my-schema",
            message_retention_duration="86400s",
        )

        assert topic.id == "my-topic"
        assert topic.topic_name == "my-topic"
        assert topic.labels_count == 2
        assert topic.schema_name == "my-schema"
        assert topic.message_retention_duration == "86400s"

    def test_from_api_response_full(self) -> None:
        """Test creating topic from full API response."""
        data = {
            "name": "projects/my-project/topics/my-topic",
            "labels": {
                "env": "prod",
                "team": "platform",
            },
            "messageRetentionDuration": "86400s",
            "schemaSettings": {
                "schema": "projects/my-project/schemas/my-schema",
                "encoding": "JSON",
            },
            "kmsKeyName": "projects/my-project/locations/us/keyRings/my-ring/cryptoKeys/my-key",
        }

        topic = Topic.from_api_response(data)

        assert topic.topic_name == "my-topic"
        assert topic.project_id == "my-project"
        assert topic.labels_count == 2
        assert topic.schema_name == "my-schema"
        assert topic.message_retention_duration == "86400s"
        assert topic.kms_key_name == data["kmsKeyName"]
        assert topic.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating topic from minimal API response."""
        data: dict[str, Any] = {
            "name": "projects/test-project/topics/minimal-topic",
        }

        topic = Topic.from_api_response(data)

        assert topic.topic_name == "minimal-topic"
        assert topic.project_id == "test-project"
        assert topic.labels_count == 0
        assert topic.schema_name is None
        assert topic.message_retention_duration is None
        assert topic.kms_key_name is None

    def test_from_api_response_with_labels(self) -> None:
        """Test label counting."""
        data = {
            "name": "projects/test-project/topics/labeled-topic",
            "labels": {
                "env": "prod",
                "team": "platform",
                "cost-center": "engineering",
                "owner": "alice",
            },
        }

        topic = Topic.from_api_response(data)

        assert topic.labels_count == 4

    def test_from_api_response_no_labels(self) -> None:
        """Test topic without labels."""
        data = {
            "name": "projects/test-project/topics/no-labels",
        }

        topic = Topic.from_api_response(data)

        assert topic.labels_count == 0

    def test_from_api_response_empty_labels(self) -> None:
        """Test topic with empty labels dict."""
        data = {
            "name": "projects/test-project/topics/empty-labels",
            "labels": {},
        }

        topic = Topic.from_api_response(data)

        assert topic.labels_count == 0

    def test_from_api_response_with_schema(self) -> None:
        """Test topic with schema settings."""
        data = {
            "name": "projects/test-project/topics/schema-topic",
            "schemaSettings": {
                "schema": "projects/test-project/schemas/order-schema",
                "encoding": "JSON",
            },
        }

        topic = Topic.from_api_response(data)

        assert topic.schema_name == "order-schema"

    def test_from_api_response_no_schema(self) -> None:
        """Test topic without schema."""
        data = {
            "name": "projects/test-project/topics/no-schema",
        }

        topic = Topic.from_api_response(data)

        assert topic.schema_name is None

    def test_from_api_response_invalid_schema_settings(self) -> None:
        """Test handling invalid schema settings type."""
        data = {
            "name": "projects/test-project/topics/invalid-schema",
            "schemaSettings": "not-a-dict",
        }

        topic = Topic.from_api_response(data)

        assert topic.schema_name is None

    def test_from_api_response_invalid_labels_type(self) -> None:
        """Test handling invalid labels field type."""
        data = {
            "name": "projects/test-project/topics/invalid-labels",
            "labels": "not-a-dict",
        }

        topic = Topic.from_api_response(data)

        assert topic.labels_count == 0


class TestSubscription:
    """Tests for Subscription model."""

    def test_create_subscription(self) -> None:
        """Test creating a subscription instance."""
        subscription = Subscription(
            id="my-subscription",
            name="my-subscription",
            subscription_name="my-subscription",
            topic_name="my-topic",
            ack_deadline_seconds=30,
            retain_acked_messages=True,
            labels_count=1,
            push_endpoint="https://example.com/push",
        )

        assert subscription.id == "my-subscription"
        assert subscription.subscription_name == "my-subscription"
        assert subscription.topic_name == "my-topic"
        assert subscription.ack_deadline_seconds == 30
        assert subscription.retain_acked_messages is True
        assert subscription.labels_count == 1
        assert subscription.push_endpoint == "https://example.com/push"

    def test_from_api_response_full(self) -> None:
        """Test creating subscription from full API response."""
        data = {
            "name": "projects/my-project/subscriptions/my-subscription",
            "topic": "projects/my-project/topics/my-topic",
            "pushConfig": {
                "pushEndpoint": "https://example.com/push",
            },
            "ackDeadlineSeconds": 30,
            "retainAckedMessages": True,
            "messageRetentionDuration": "604800s",
            "labels": {
                "env": "prod",
            },
            "filter": 'attributes.event_type = "order"',
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.subscription_name == "my-subscription"
        assert subscription.topic_name == "my-topic"
        assert subscription.project_id == "my-project"
        assert subscription.ack_deadline_seconds == 30
        assert subscription.retain_acked_messages is True
        assert subscription.message_retention_duration == "604800s"
        assert subscription.labels_count == 1
        assert subscription.push_endpoint == "https://example.com/push"
        assert subscription.filter_expression == 'attributes.event_type = "order"'
        assert subscription.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating subscription from minimal API response."""
        data: dict[str, Any] = {
            "name": "projects/test-project/subscriptions/minimal-sub",
            "topic": "projects/test-project/topics/test-topic",
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.subscription_name == "minimal-sub"
        assert subscription.topic_name == "test-topic"
        assert subscription.project_id == "test-project"
        assert subscription.ack_deadline_seconds == 10  # default
        assert subscription.retain_acked_messages is False  # default
        assert subscription.labels_count == 0
        assert subscription.push_endpoint is None
        assert subscription.filter_expression is None

    def test_from_api_response_push_subscription(self) -> None:
        """Test creating push subscription."""
        data = {
            "name": "projects/test-project/subscriptions/push-sub",
            "topic": "projects/test-project/topics/test-topic",
            "pushConfig": {
                "pushEndpoint": "https://example.com/webhook",
            },
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.push_endpoint == "https://example.com/webhook"
        assert subscription.is_push() is True
        assert subscription.get_subscription_type() == "Push"

    def test_from_api_response_pull_subscription(self) -> None:
        """Test creating pull subscription."""
        data = {
            "name": "projects/test-project/subscriptions/pull-sub",
            "topic": "projects/test-project/topics/test-topic",
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.push_endpoint is None
        assert subscription.is_push() is False
        assert subscription.get_subscription_type() == "Pull"

    def test_from_api_response_with_filter(self) -> None:
        """Test subscription with message filter."""
        data = {
            "name": "projects/test-project/subscriptions/filtered-sub",
            "topic": "projects/test-project/topics/test-topic",
            "filter": 'attributes.priority = "high"',
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.filter_expression == 'attributes.priority = "high"'

    def test_from_api_response_invalid_push_config_type(self) -> None:
        """Test handling invalid pushConfig type."""
        data = {
            "name": "projects/test-project/subscriptions/invalid-push",
            "topic": "projects/test-project/topics/test-topic",
            "pushConfig": "not-a-dict",
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.push_endpoint is None
        assert subscription.is_push() is False

    def test_from_api_response_with_labels(self) -> None:
        """Test label counting."""
        data = {
            "name": "projects/test-project/subscriptions/labeled-sub",
            "topic": "projects/test-project/topics/test-topic",
            "labels": {
                "env": "prod",
                "team": "platform",
                "cost-center": "engineering",
            },
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.labels_count == 3

    def test_from_api_response_invalid_labels_type(self) -> None:
        """Test handling invalid labels field type."""
        data = {
            "name": "projects/test-project/subscriptions/invalid-labels",
            "topic": "projects/test-project/topics/test-topic",
            "labels": "not-a-dict",
        }

        subscription = Subscription.from_api_response(data)

        assert subscription.labels_count == 0

    def test_is_push_with_endpoint(self) -> None:
        """Test is_push returns True when endpoint exists."""
        subscription = Subscription(
            id="push-sub",
            name="push-sub",
            subscription_name="push-sub",
            topic_name="test-topic",
            push_endpoint="https://example.com/push",
        )

        assert subscription.is_push() is True

    def test_is_push_without_endpoint(self) -> None:
        """Test is_push returns False when no endpoint."""
        subscription = Subscription(
            id="pull-sub",
            name="pull-sub",
            subscription_name="pull-sub",
            topic_name="test-topic",
        )

        assert subscription.is_push() is False

    def test_get_subscription_type_push(self) -> None:
        """Test get_subscription_type returns Push."""
        subscription = Subscription(
            id="push-sub",
            name="push-sub",
            subscription_name="push-sub",
            topic_name="test-topic",
            push_endpoint="https://example.com/push",
        )

        assert subscription.get_subscription_type() == "Push"

    def test_get_subscription_type_pull(self) -> None:
        """Test get_subscription_type returns Pull."""
        subscription = Subscription(
            id="pull-sub",
            name="pull-sub",
            subscription_name="pull-sub",
            topic_name="test-topic",
        )

        assert subscription.get_subscription_type() == "Pull"
