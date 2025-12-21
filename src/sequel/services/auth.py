"""Google Cloud authentication using Application Default Credentials (ADC).

This module handles loading and validating Google Cloud credentials for API access.
"""

import google.auth
import google.auth.transport.requests
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError, RefreshError

from sequel.config import get_config
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class AuthError(Exception):
    """Authentication-related errors."""

    pass


class AuthManager:
    """Manages Google Cloud authentication using ADC.

    The AuthManager loads credentials using Google's Application Default
    Credentials (ADC) mechanism, which checks:
    1. GOOGLE_APPLICATION_CREDENTIALS environment variable
    2. gcloud CLI configuration
    3. GCE/GKE metadata server (when running on Google Cloud)

    Attributes:
        credentials: Google Cloud credentials
        project_id: Project ID associated with the credentials
    """

    def __init__(self) -> None:
        """Initialize the AuthManager."""
        self._credentials: Credentials | None = None
        self._project_id: str | None = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize and load credentials asynchronously.

        Raises:
            AuthError: If credentials cannot be loaded
        """
        if self._initialized:
            return

        try:
            logger.info("Loading Google Cloud Application Default Credentials...")
            credentials, project_id = google.auth.default(  # type: ignore[no-untyped-call]
                scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"]
            )

            # Validate credentials
            if not credentials:
                raise AuthError("Failed to load credentials")

            if not credentials.valid and credentials.expired:
                logger.info("Credentials expired, refreshing...")
                try:
                    credentials.refresh(google.auth.transport.requests.Request())  # type: ignore[no-untyped-call]
                except RefreshError as e:
                    raise AuthError(
                        f"Failed to refresh expired credentials: {e}. "
                        "Please run 'gcloud auth application-default login'"
                    ) from e

            self._credentials = credentials
            self._project_id = project_id or get_config().gcloud_project_id

            if not self._project_id:
                logger.warning(
                    "No project ID detected from credentials. "
                    "Set SEQUEL_GCLOUD_PROJECT_ID environment variable if needed."
                )

            logger.info(
                "Successfully loaded credentials"
                + (f" for project: {self._project_id}" if self._project_id else "")
            )
            self._initialized = True

        except DefaultCredentialsError as e:
            raise AuthError(
                "Google Cloud credentials not found. Please set up authentication using:\n"
                "  1. 'gcloud auth application-default login' (recommended), or\n"
                "  2. Set GOOGLE_APPLICATION_CREDENTIALS to a service account key file\n"
                f"Error: {e}"
            ) from e
        except Exception as e:
            raise AuthError(f"Failed to load credentials: {e}") from e

    @property
    def credentials(self) -> Credentials:
        """Get the loaded credentials.

        Returns:
            Google Cloud credentials

        Raises:
            AuthError: If credentials haven't been initialized
        """
        if not self._initialized or self._credentials is None:
            raise AuthError(
                "AuthManager not initialized. Call initialize() first."
            )
        return self._credentials

    @property
    def project_id(self) -> str | None:
        """Get the project ID associated with the credentials.

        Returns:
            Project ID or None if not available
        """
        return self._project_id

    def validate_scopes(self, required_scopes: list[str]) -> bool:
        """Validate that credentials have required scopes.

        Args:
            required_scopes: List of required OAuth scopes

        Returns:
            True if all required scopes are present

        Note:
            This is a best-effort check. Some credential types don't expose scopes.
        """
        if not self._credentials:
            return False

        # Check if credentials have scopes attribute
        if not hasattr(self._credentials, "scopes"):
            logger.debug("Credentials do not expose scopes, skipping validation")
            return True

        cred_scopes = getattr(self._credentials, "scopes", [])
        if not cred_scopes:
            logger.debug("No scopes found in credentials")
            return True

        missing_scopes = set(required_scopes) - set(cred_scopes)
        if missing_scopes:
            logger.warning(f"Missing required scopes: {missing_scopes}")
            return False

        return True


# Global auth manager instance
_auth_manager: AuthManager | None = None


async def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance.

    Returns:
        Initialized AuthManager

    Raises:
        AuthError: If authentication fails
    """
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
        await _auth_manager.initialize()
    return _auth_manager


def reset_auth_manager() -> None:
    """Reset the global auth manager (mainly for testing)."""
    global _auth_manager
    _auth_manager = None
