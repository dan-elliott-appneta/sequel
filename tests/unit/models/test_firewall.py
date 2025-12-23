"""Unit tests for Firewall models."""

from typing import Any

from sequel.models.firewall import FirewallPolicy


class TestFirewallPolicy:
    """Tests for FirewallPolicy model."""

    def test_create_firewall_policy(self) -> None:
        """Test creating a firewall policy instance."""
        policy = FirewallPolicy(
            id="allow-ssh",
            name="allow-ssh",
            policy_name="allow-ssh",
            description="Allow SSH from anywhere",
            rule_count=1,
            priority=1000,
            direction="INGRESS",
            disabled=False,
        )

        assert policy.id == "allow-ssh"
        assert policy.policy_name == "allow-ssh"
        assert policy.description == "Allow SSH from anywhere"
        assert policy.rule_count == 1
        assert policy.priority == 1000
        assert policy.direction == "INGRESS"
        assert policy.disabled is False

    def test_from_api_response_full(self) -> None:
        """Test creating policy from full API response."""
        data = {
            "name": "allow-ssh",
            "description": "Allow SSH from anywhere",
            "network": "projects/my-project/global/networks/default",
            "priority": 1000,
            "direction": "INGRESS",
            "disabled": False,
            "sourceRanges": ["0.0.0.0/0"],
            "allowed": [
                {"IPProtocol": "tcp", "ports": ["22"]}
            ],
            "creationTimestamp": "2023-01-01T00:00:00.000-00:00",
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.policy_name == "allow-ssh"
        assert policy.description == "Allow SSH from anywhere"
        assert policy.project_id == "my-project"
        assert policy.priority == 1000
        assert policy.direction == "INGRESS"
        assert policy.disabled is False
        assert policy.rule_count == 1
        assert policy.created_at is not None
        assert policy.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating policy from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-policy",
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.policy_name == "minimal-policy"
        assert policy.description is None
        assert policy.project_id is None
        assert policy.priority is None
        assert policy.direction is None
        assert policy.disabled is False
        assert policy.rule_count == 0
        assert policy.created_at is None

    def test_from_api_response_with_allowed_rules(self) -> None:
        """Test rule counting with allowed rules."""
        data = {
            "name": "allow-multiple",
            "allowed": [
                {"IPProtocol": "tcp", "ports": ["22"]},
                {"IPProtocol": "tcp", "ports": ["80", "443"]},
                {"IPProtocol": "udp", "ports": ["53"]},
            ],
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.rule_count == 3

    def test_from_api_response_with_denied_rules(self) -> None:
        """Test rule counting with denied rules."""
        data = {
            "name": "deny-multiple",
            "denied": [
                {"IPProtocol": "tcp", "ports": ["23"]},
                {"IPProtocol": "tcp", "ports": ["3389"]},
            ],
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.rule_count == 2

    def test_from_api_response_with_mixed_rules(self) -> None:
        """Test rule counting with both allowed and denied rules."""
        data = {
            "name": "mixed-rules",
            "allowed": [
                {"IPProtocol": "tcp", "ports": ["22"]},
                {"IPProtocol": "tcp", "ports": ["80"]},
            ],
            "denied": [
                {"IPProtocol": "tcp", "ports": ["23"]},
            ],
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.rule_count == 3

    def test_from_api_response_egress(self) -> None:
        """Test creating egress firewall policy."""
        data = {
            "name": "allow-egress",
            "direction": "EGRESS",
            "priority": 900,
            "allowed": [
                {"IPProtocol": "tcp"},
            ],
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.direction == "EGRESS"
        assert policy.priority == 900

    def test_from_api_response_disabled(self) -> None:
        """Test creating disabled firewall policy."""
        data = {
            "name": "disabled-policy",
            "disabled": True,
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.disabled is True

    def test_from_api_response_no_network(self) -> None:
        """Test creating policy without network field."""
        data = {
            "name": "no-network-policy",
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.project_id is None

    def test_from_api_response_malformed_network(self) -> None:
        """Test creating policy with malformed network path."""
        data = {
            "name": "malformed-network",
            "network": "invalid-network-path",
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.project_id is None

    def test_from_api_response_invalid_timestamp(self) -> None:
        """Test creating policy with invalid timestamp."""
        data = {
            "name": "invalid-timestamp",
            "creationTimestamp": "not-a-timestamp",
        }

        policy = FirewallPolicy.from_api_response(data)

        assert policy.created_at is None

    def test_is_enabled_true(self) -> None:
        """Test is_enabled when policy is not disabled."""
        policy = FirewallPolicy(
            id="enabled-policy",
            name="enabled-policy",
            policy_name="enabled-policy",
            disabled=False,
        )

        assert policy.is_enabled() is True

    def test_is_enabled_false(self) -> None:
        """Test is_enabled when policy is disabled."""
        policy = FirewallPolicy(
            id="disabled-policy",
            name="disabled-policy",
            policy_name="disabled-policy",
            disabled=True,
        )

        assert policy.is_enabled() is False

    def test_is_enabled_default(self) -> None:
        """Test is_enabled with default disabled value."""
        policy = FirewallPolicy(
            id="default-policy",
            name="default-policy",
            policy_name="default-policy",
        )

        # Default disabled is False, so is_enabled should be True
        assert policy.is_enabled() is True
