"""Google Cloud IAM Service Account model."""

from typing import Any

from pydantic import Field

from sequel.models.base import BaseModel


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
        )

    def is_enabled(self) -> bool:
        """Check if service account is enabled.

        Returns:
            True if enabled, False if disabled
        """
        return not self.disabled
