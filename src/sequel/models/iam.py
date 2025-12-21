"""Google Cloud IAM models."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


class IAMRoleBinding(BaseModel):
    """Model for an IAM role binding."""

    role: str = Field(..., description="Role name (e.g., roles/editor)")
    member: str = Field(..., description="Member (e.g., serviceAccount:email@project.iam.gserviceaccount.com)")
    resource: str | None = Field(None, description="Resource the binding applies to")

    @classmethod
    def from_api_response(cls, role: str, member: str, resource: str | None = None) -> "IAMRoleBinding":  # type: ignore[override]
        """Create IAMRoleBinding from role and member.

        Note: This method has a different signature than the base class,
        which is intentional for this specific model type.

        Args:
            role: Role name
            member: Member identifier
            resource: Optional resource identifier

        Returns:
            IAMRoleBinding instance
        """
        return cls(
            id=f"{role}:{member}",
            name=role,
            project_id=None,
            created_at=None,
            role=role,
            member=member,
            resource=resource,
            raw_data={"role": role, "member": member, "resource": resource},
        )


class ServiceAccount(BaseModel):
    """Model for a Google Cloud IAM Service Account."""

    email: str = Field(..., description="Service account email address")
    display_name: str | None = Field(None, description="Display name")
    description: str | None = Field(None, description="Service account description")
    disabled: bool = Field(default=False, description="Whether the service account is disabled")
    unique_id: str | None = Field(None, description="Unique numeric ID")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ServiceAccount":
        """Create ServiceAccount from IAM API response.

        Args:
            data: API response data from serviceAccounts.get()

        Returns:
            ServiceAccount instance

        Example API response structure:
            {
                "name": "projects/my-project/serviceAccounts/my-sa@my-project.iam.gserviceaccount.com",
                "email": "my-sa@my-project.iam.gserviceaccount.com",
                "displayName": "My Service Account",
                "description": "Service account for XYZ",
                "uniqueId": "123456789",
                "disabled": false
            }
        """
        email = data.get("email", "")

        # Extract project_id from email
        project_id = None
        if "@" in email:
            domain = email.split("@")[1]
            if "." in domain:
                project_id = domain.split(".")[0]

        # Extract name from email (before @)
        name = email.split("@")[0] if "@" in email else email

        return cls(
            id=email,
            name=name,
            project_id=project_id,
            created_at=None,  # IAM service accounts don't have creation timestamps in API
            email=email,
            display_name=data.get("displayName"),
            description=data.get("description"),
            disabled=data.get("disabled", False),
            unique_id=data.get("uniqueId"),
            raw_data=data.copy(),
        )

    def is_enabled(self) -> bool:
        """Check if service account is enabled.

        Returns:
            True if enabled, False if disabled
        """
        return not self.disabled
