"""Unit tests for IAM models."""

from typing import Any

from sequel.models.iam import IAMRoleBinding, ServiceAccount


class TestIAMRoleBinding:
    """Tests for IAMRoleBinding model."""

    def test_create_role_binding(self) -> None:
        """Test creating an IAM role binding."""
        binding = IAMRoleBinding(
            id="roles/editor:user@example.com",
            name="roles/editor",
            role="roles/editor",
            member="user@example.com",
            resource="projects/my-project",
        )

        assert binding.id == "roles/editor:user@example.com"
        assert binding.role == "roles/editor"
        assert binding.member == "user@example.com"
        assert binding.resource == "projects/my-project"

    def test_from_api_response(self) -> None:
        """Test creating role binding from API response format."""
        binding = IAMRoleBinding.from_api_response(
            role="roles/viewer",
            member="serviceAccount:sa@project.iam.gserviceaccount.com",
            resource="projects/test-project",
        )

        assert binding.role == "roles/viewer"
        assert binding.member == "serviceAccount:sa@project.iam.gserviceaccount.com"
        assert binding.resource == "projects/test-project"
        assert binding.id == "roles/viewer:serviceAccount:sa@project.iam.gserviceaccount.com"
        assert binding.name == "roles/viewer"

    def test_from_api_response_no_resource(self) -> None:
        """Test creating role binding without resource."""
        binding = IAMRoleBinding.from_api_response(
            role="roles/owner",
            member="user:admin@example.com",
        )

        assert binding.role == "roles/owner"
        assert binding.member == "user:admin@example.com"
        assert binding.resource is None


class TestServiceAccount:
    """Tests for ServiceAccount model."""

    def test_create_service_account(self) -> None:
        """Test creating a service account."""
        sa = ServiceAccount(
            id="sa@project.iam.gserviceaccount.com",
            name="sa",
            email="sa@project.iam.gserviceaccount.com",
            display_name="Service Account",
            description="Test service account",
            disabled=False,
            unique_id="123456789",
        )

        assert sa.email == "sa@project.iam.gserviceaccount.com"
        assert sa.display_name == "Service Account"
        assert sa.description == "Test service account"
        assert sa.disabled is False
        assert sa.unique_id == "123456789"

    def test_from_api_response_full(self) -> None:
        """Test creating service account from full API response."""
        data = {
            "name": "projects/my-project/serviceAccounts/test-sa@my-project.iam.gserviceaccount.com",
            "email": "test-sa@my-project.iam.gserviceaccount.com",
            "displayName": "Test Service Account",
            "description": "A test service account",
            "uniqueId": "987654321",
            "disabled": False,
        }

        sa = ServiceAccount.from_api_response(data)

        assert sa.email == "test-sa@my-project.iam.gserviceaccount.com"
        assert sa.display_name == "Test Service Account"
        assert sa.description == "A test service account"
        assert sa.unique_id == "987654321"
        assert sa.disabled is False
        assert sa.project_id == "my-project"
        assert sa.name == "test-sa"
        assert sa.id == "test-sa@my-project.iam.gserviceaccount.com"

    def test_from_api_response_minimal(self) -> None:
        """Test creating service account from minimal API response."""
        data: dict[str, Any] = {
            "email": "minimal@project.iam.gserviceaccount.com",
        }

        sa = ServiceAccount.from_api_response(data)

        assert sa.email == "minimal@project.iam.gserviceaccount.com"
        assert sa.display_name is None
        assert sa.description is None
        assert sa.unique_id is None
        assert sa.disabled is False  # Default value

    def test_from_api_response_disabled(self) -> None:
        """Test creating disabled service account."""
        data = {
            "email": "disabled-sa@project.iam.gserviceaccount.com",
            "disabled": True,
        }

        sa = ServiceAccount.from_api_response(data)

        assert sa.disabled is True
        assert sa.is_enabled() is False

    def test_is_enabled_true(self) -> None:
        """Test is_enabled when service account is enabled."""
        sa = ServiceAccount(
            id="sa@project.iam.gserviceaccount.com",
            name="sa",
            email="sa@project.iam.gserviceaccount.com",
            disabled=False,
        )

        assert sa.is_enabled() is True

    def test_is_enabled_false(self) -> None:
        """Test is_enabled when service account is disabled."""
        sa = ServiceAccount(
            id="sa@project.iam.gserviceaccount.com",
            name="sa",
            email="sa@project.iam.gserviceaccount.com",
            disabled=True,
        )

        assert sa.is_enabled() is False

    def test_extract_project_id_from_email(self) -> None:
        """Test that project_id is correctly extracted from email."""
        data = {
            "email": "my-sa@fancy-project-123.iam.gserviceaccount.com",
        }

        sa = ServiceAccount.from_api_response(data)

        assert sa.project_id == "fancy-project-123"

    def test_extract_name_from_email(self) -> None:
        """Test that name is correctly extracted from email."""
        data = {
            "email": "backend-api@project.iam.gserviceaccount.com",
        }

        sa = ServiceAccount.from_api_response(data)

        assert sa.name == "backend-api"
