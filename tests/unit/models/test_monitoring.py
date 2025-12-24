"""Unit tests for Cloud Monitoring models."""

from typing import Any

from sequel.models.monitoring import AlertPolicy


class TestAlertPolicy:
    """Tests for AlertPolicy model."""

    def test_create_alert_policy(self) -> None:
        """Test creating an alert policy instance."""
        policy = AlertPolicy(
            id="1234567890",
            name="High CPU Usage",
            policy_name="1234567890",
            display_name="High CPU Usage",
            enabled=True,
            condition_count=1,
            notification_channel_count=2,
            combiner="OR",
            documentation_content="Check the instance and consider scaling.",
        )

        assert policy.id == "1234567890"
        assert policy.policy_name == "1234567890"
        assert policy.display_name == "High CPU Usage"
        assert policy.enabled is True
        assert policy.condition_count == 1
        assert policy.notification_channel_count == 2
        assert policy.combiner == "OR"
        assert policy.documentation_content == "Check the instance and consider scaling."

    def test_from_api_response_full(self) -> None:
        """Test creating policy from full API response."""
        data = {
            "name": "projects/my-project/alertPolicies/1234567890",
            "displayName": "High CPU Usage",
            "enabled": True,
            "conditions": [
                {
                    "name": "projects/my-project/alertPolicies/1234567890/conditions/5678",
                    "displayName": "CPU usage above 80%",
                    "conditionThreshold": {
                        "filter": 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
                        "comparison": "COMPARISON_GT",
                        "thresholdValue": 0.8,
                        "duration": "60s",
                    },
                }
            ],
            "combiner": "OR",
            "notificationChannels": [
                "projects/my-project/notificationChannels/9876543210",
                "projects/my-project/notificationChannels/9876543211",
            ],
            "documentation": {
                "content": "Check the instance and consider scaling.",
                "mimeType": "text/markdown",
            },
            "creationRecord": {
                "mutateTime": "2023-01-01T00:00:00.000Z",
                "mutatedBy": "user@example.com",
            },
            "mutationRecord": {
                "mutateTime": "2023-06-01T00:00:00.000Z",
                "mutatedBy": "user@example.com",
            },
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.policy_name == "1234567890"
        assert policy.display_name == "High CPU Usage"
        assert policy.project_id == "my-project"
        assert policy.enabled is True
        assert policy.condition_count == 1
        assert policy.notification_channel_count == 2
        assert policy.combiner == "OR"
        assert policy.documentation_content == "Check the instance and consider scaling."
        assert policy.created_at is not None
        assert policy.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating policy from minimal API response."""
        data: dict[str, Any] = {
            "name": "projects/my-project/alertPolicies/minimal-policy",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.policy_name == "minimal-policy"
        assert policy.display_name == "minimal-policy"  # Falls back to policy_name
        assert policy.project_id == "my-project"
        assert policy.enabled is True  # Default
        assert policy.condition_count == 0
        assert policy.notification_channel_count == 0
        assert policy.combiner is None
        assert policy.documentation_content is None
        assert policy.created_at is None

    def test_from_api_response_disabled(self) -> None:
        """Test creating disabled alert policy."""
        data = {
            "name": "projects/my-project/alertPolicies/disabled-policy",
            "enabled": False,
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.enabled is False

    def test_from_api_response_multiple_conditions(self) -> None:
        """Test creating policy with multiple conditions."""
        data = {
            "name": "projects/my-project/alertPolicies/multi-condition",
            "conditions": [
                {
                    "name": "condition1",
                    "conditionThreshold": {},
                },
                {
                    "name": "condition2",
                    "conditionThreshold": {},
                },
                {
                    "name": "condition3",
                    "conditionThreshold": {},
                },
            ],
            "combiner": "AND",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.condition_count == 3
        assert policy.combiner == "AND"

    def test_from_api_response_multiple_notification_channels(self) -> None:
        """Test creating policy with multiple notification channels."""
        data = {
            "name": "projects/my-project/alertPolicies/multi-channel",
            "notificationChannels": [
                "projects/my-project/notificationChannels/channel1",
                "projects/my-project/notificationChannels/channel2",
                "projects/my-project/notificationChannels/channel3",
            ],
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.notification_channel_count == 3

    def test_from_api_response_no_conditions(self) -> None:
        """Test creating policy with empty conditions list."""
        data = {
            "name": "projects/my-project/alertPolicies/no-conditions",
            "conditions": [],
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.condition_count == 0

    def test_from_api_response_invalid_conditions(self) -> None:
        """Test creating policy with invalid conditions (not a list)."""
        data = {
            "name": "projects/my-project/alertPolicies/invalid-conditions",
            "conditions": "not-a-list",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.condition_count == 0

    def test_from_api_response_no_notification_channels(self) -> None:
        """Test creating policy with empty notification channels list."""
        data = {
            "name": "projects/my-project/alertPolicies/no-channels",
            "notificationChannels": [],
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.notification_channel_count == 0

    def test_from_api_response_invalid_notification_channels(self) -> None:
        """Test creating policy with invalid notification channels (not a list)."""
        data = {
            "name": "projects/my-project/alertPolicies/invalid-channels",
            "notificationChannels": "not-a-list",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.notification_channel_count == 0

    def test_from_api_response_with_display_name(self) -> None:
        """Test creating policy with explicit display name."""
        data = {
            "name": "projects/my-project/alertPolicies/12345",
            "displayName": "Custom Alert Name",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.policy_name == "12345"
        assert policy.display_name == "Custom Alert Name"
        assert policy.name == "Custom Alert Name"  # BaseModel name field

    def test_from_api_response_without_display_name(self) -> None:
        """Test creating policy without display name (uses policy name)."""
        data = {
            "name": "projects/my-project/alertPolicies/67890",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.policy_name == "67890"
        assert policy.display_name == "67890"
        assert policy.name == "67890"  # BaseModel name field

    def test_from_api_response_simple_name(self) -> None:
        """Test creating policy with simple name (no project path)."""
        data = {
            "name": "simple-name",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.policy_name == "simple-name"
        assert policy.project_id is None

    def test_from_api_response_invalid_name_format(self) -> None:
        """Test creating policy with invalid name format."""
        data = {
            "name": "projects/",
        }

        policy = AlertPolicy.from_api_response(data)

        # Should still extract the last part after split
        assert policy.policy_name == ""

    def test_from_api_response_combiner_and(self) -> None:
        """Test creating policy with AND combiner."""
        data = {
            "name": "projects/my-project/alertPolicies/combiner-and",
            "combiner": "AND",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.combiner == "AND"

    def test_from_api_response_combiner_or_with_matching_resource(self) -> None:
        """Test creating policy with OR_WITH_MATCHING_RESOURCE combiner."""
        data = {
            "name": "projects/my-project/alertPolicies/combiner-or-match",
            "combiner": "AND_WITH_MATCHING_RESOURCE",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.combiner == "AND_WITH_MATCHING_RESOURCE"

    def test_from_api_response_documentation_dict(self) -> None:
        """Test extracting documentation content from dict."""
        data = {
            "name": "projects/my-project/alertPolicies/with-docs",
            "documentation": {
                "content": "This is the documentation content.",
                "mimeType": "text/markdown",
            },
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.documentation_content == "This is the documentation content."

    def test_from_api_response_documentation_empty(self) -> None:
        """Test with empty documentation dict."""
        data = {
            "name": "projects/my-project/alertPolicies/empty-docs",
            "documentation": {},
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.documentation_content is None

    def test_from_api_response_documentation_invalid(self) -> None:
        """Test with invalid documentation (not a dict)."""
        data = {
            "name": "projects/my-project/alertPolicies/invalid-docs",
            "documentation": "not-a-dict",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.documentation_content is None

    def test_from_api_response_invalid_creation_timestamp(self) -> None:
        """Test creating policy with invalid creation timestamp."""
        data = {
            "name": "projects/my-project/alertPolicies/invalid-timestamp",
            "creationRecord": {
                "mutateTime": "not-a-timestamp",
            },
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.created_at is None

    def test_from_api_response_no_creation_record(self) -> None:
        """Test creating policy without creation record."""
        data = {
            "name": "projects/my-project/alertPolicies/no-creation",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.created_at is None

    def test_from_api_response_invalid_creation_record(self) -> None:
        """Test creating policy with invalid creation record (not a dict)."""
        data = {
            "name": "projects/my-project/alertPolicies/invalid-creation",
            "creationRecord": "not-a-dict",
        }

        policy = AlertPolicy.from_api_response(data)

        assert policy.created_at is None

    def test_is_enabled_true(self) -> None:
        """Test is_enabled when policy is enabled."""
        policy = AlertPolicy(
            id="enabled-policy",
            name="enabled-policy",
            policy_name="enabled-policy",
            enabled=True,
        )

        assert policy.is_enabled() is True

    def test_is_enabled_false(self) -> None:
        """Test is_enabled when policy is disabled."""
        policy = AlertPolicy(
            id="disabled-policy",
            name="disabled-policy",
            policy_name="disabled-policy",
            enabled=False,
        )

        assert policy.is_enabled() is False

    def test_is_enabled_default(self) -> None:
        """Test is_enabled with default enabled value."""
        policy = AlertPolicy(
            id="default-policy",
            name="default-policy",
            policy_name="default-policy",
        )

        # Default enabled is True
        assert policy.is_enabled() is True

    def test_get_condition_summary_no_conditions(self) -> None:
        """Test condition summary with no conditions."""
        policy = AlertPolicy(
            id="no-conditions",
            name="no-conditions",
            policy_name="no-conditions",
            condition_count=0,
        )

        assert policy.get_condition_summary() == "No conditions"

    def test_get_condition_summary_one_condition(self) -> None:
        """Test condition summary with one condition."""
        policy = AlertPolicy(
            id="one-condition",
            name="one-condition",
            policy_name="one-condition",
            condition_count=1,
        )

        assert policy.get_condition_summary() == "1 condition"

    def test_get_condition_summary_multiple_conditions_with_combiner(self) -> None:
        """Test condition summary with multiple conditions and combiner."""
        policy = AlertPolicy(
            id="multi-conditions",
            name="multi-conditions",
            policy_name="multi-conditions",
            condition_count=3,
            combiner="AND",
        )

        assert policy.get_condition_summary() == "3 conditions (AND)"

    def test_get_condition_summary_multiple_conditions_no_combiner(self) -> None:
        """Test condition summary with multiple conditions but no combiner."""
        policy = AlertPolicy(
            id="multi-no-combiner",
            name="multi-no-combiner",
            policy_name="multi-no-combiner",
            condition_count=5,
        )

        assert policy.get_condition_summary() == "5 conditions"
