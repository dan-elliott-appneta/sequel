"""Unit tests for authentication manager."""

from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import DefaultCredentialsError, RefreshError

from sequel.services.auth import AuthError, AuthManager, get_auth_manager, reset_auth_manager


class TestAuthManager:
    """Test AuthManager class."""

    def setup_method(self) -> None:
        """Reset auth manager before each test."""
        reset_auth_manager()

    @pytest.mark.asyncio
    async def test_initialize_success(self) -> None:
        """Test successful initialization with valid credentials."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, "test-project-123")):
            auth_manager = AuthManager()
            await auth_manager.initialize()

            assert auth_manager._initialized is True
            assert auth_manager.project_id == "test-project-123"
            assert auth_manager.credentials is mock_creds

    @pytest.mark.asyncio
    async def test_initialize_no_project_id(self) -> None:
        """Test initialization when credentials don't include project ID."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, None)):
            auth_manager = AuthManager()
            await auth_manager.initialize()

            assert auth_manager._initialized is True
            assert auth_manager.project_id is None

    @pytest.mark.asyncio
    async def test_initialize_expired_credentials_refresh_success(self) -> None:
        """Test initialization with expired credentials that refresh successfully."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh = MagicMock()

        with (
            patch("google.auth.default", return_value=(mock_creds, "test-project")),
            patch("google.auth.transport.requests.Request"),
        ):
            auth_manager = AuthManager()
            await auth_manager.initialize()

            assert auth_manager._initialized is True
            mock_creds.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_expired_credentials_refresh_fails(self) -> None:
        """Test initialization with expired credentials that fail to refresh."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh = MagicMock(side_effect=RefreshError("Refresh failed"))

        with (
            patch("google.auth.default", return_value=(mock_creds, "test-project")),
            patch("google.auth.transport.requests.Request"),
        ):
            auth_manager = AuthManager()

            with pytest.raises(AuthError) as exc_info:
                await auth_manager.initialize()

            assert "Failed to refresh" in str(exc_info.value)
            assert "gcloud auth application-default login" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_no_credentials(self) -> None:
        """Test initialization when no credentials are found."""
        with patch(
            "google.auth.default",
            side_effect=DefaultCredentialsError("No credentials found"),
        ):
            auth_manager = AuthManager()

            with pytest.raises(AuthError) as exc_info:
                await auth_manager.initialize()

            assert "credentials not found" in str(exc_info.value).lower()
            assert "gcloud auth application-default login" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_only_once(self) -> None:
        """Test that initialize only initializes once."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, "test-project")) as mock_default:
            auth_manager = AuthManager()
            await auth_manager.initialize()
            await auth_manager.initialize()  # Second call

            # google.auth.default should only be called once
            mock_default.assert_called_once()

    @pytest.mark.asyncio
    async def test_credentials_property_before_init(self) -> None:
        """Test accessing credentials before initialization raises error."""
        auth_manager = AuthManager()

        with pytest.raises(AuthError) as exc_info:
            _ = auth_manager.credentials

        assert "not initialized" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_credentials_property_after_init(self) -> None:
        """Test accessing credentials after initialization."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            auth_manager = AuthManager()
            await auth_manager.initialize()

            assert auth_manager.credentials is mock_creds

    @pytest.mark.asyncio
    async def test_project_id_property(self) -> None:
        """Test project_id property."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, "my-project")):
            auth_manager = AuthManager()
            await auth_manager.initialize()

            assert auth_manager.project_id == "my-project"

    def test_validate_scopes_no_credentials(self) -> None:
        """Test validate_scopes when credentials aren't loaded."""
        auth_manager = AuthManager()
        result = auth_manager.validate_scopes(["scope1"])

        assert result is False

    def test_validate_scopes_credentials_without_scopes_attribute(self) -> None:
        """Test validate_scopes when credentials don't have scopes attribute."""
        auth_manager = AuthManager()
        auth_manager._credentials = MagicMock(spec=[])  # No 'scopes' attribute

        result = auth_manager.validate_scopes(["scope1"])

        assert result is True  # Best-effort check passes

    def test_validate_scopes_all_present(self) -> None:
        """Test validate_scopes when all required scopes are present."""
        auth_manager = AuthManager()
        mock_creds = MagicMock()
        mock_creds.scopes = ["scope1", "scope2", "scope3"]
        auth_manager._credentials = mock_creds

        result = auth_manager.validate_scopes(["scope1", "scope2"])

        assert result is True

    def test_validate_scopes_missing_some(self) -> None:
        """Test validate_scopes when some scopes are missing."""
        auth_manager = AuthManager()
        mock_creds = MagicMock()
        mock_creds.scopes = ["scope1"]
        auth_manager._credentials = mock_creds

        result = auth_manager.validate_scopes(["scope1", "scope2"])

        assert result is False


class TestGetAuthManager:
    """Test get_auth_manager function."""

    def setup_method(self) -> None:
        """Reset auth manager before each test."""
        reset_auth_manager()

    @pytest.mark.asyncio
    async def test_get_auth_manager_creates_instance(self) -> None:
        """Test that get_auth_manager creates and initializes an instance."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            auth_manager = await get_auth_manager()

            assert isinstance(auth_manager, AuthManager)
            assert auth_manager._initialized is True

    @pytest.mark.asyncio
    async def test_get_auth_manager_returns_singleton(self) -> None:
        """Test that get_auth_manager returns the same instance (singleton)."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            auth1 = await get_auth_manager()
            auth2 = await get_auth_manager()

            assert auth1 is auth2

    @pytest.mark.asyncio
    async def test_get_auth_manager_raises_on_auth_failure(self) -> None:
        """Test that get_auth_manager raises AuthError on failure."""
        with patch(
            "google.auth.default",
            side_effect=DefaultCredentialsError("No credentials"),
        ), pytest.raises(AuthError):
            await get_auth_manager()


class TestResetAuthManager:
    """Test reset_auth_manager function."""

    @pytest.mark.asyncio
    async def test_reset_auth_manager_clears_singleton(self) -> None:
        """Test that reset_auth_manager clears the singleton instance."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            auth1 = await get_auth_manager()
            reset_auth_manager()
            auth2 = await get_auth_manager()

            # Should be different instances after reset
            assert auth1 is not auth2
