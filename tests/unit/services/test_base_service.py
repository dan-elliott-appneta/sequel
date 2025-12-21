"""Unit tests for base service."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import (
    DeadlineExceeded,
    Forbidden,
    NotFound,
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
    Unauthenticated,
)

from sequel.services.auth import AuthError
from sequel.services.base import (
    BaseService,
    NetworkError,
    PermissionError,
    QuotaExceededError,
    ResourceNotFoundError,
    ServiceNotEnabledError,
)


class ConcreteService(BaseService):
    """Concrete implementation of BaseService for testing."""

    pass


class TestBaseService:
    """Test BaseService class."""

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self) -> None:
        """Test successful operation on first attempt."""
        service = ConcreteService()

        async def operation() -> str:
            return "success"

        result = await service._execute_with_retry(operation, "test_operation")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self) -> None:
        """Test successful operation after retries."""
        service = ConcreteService()
        service.config.api_max_retries = 2
        service.config.api_retry_delay = 0.1

        attempt_count = 0

        async def operation() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ServiceUnavailable("Temporary error")
            return "success"

        result = await service._execute_with_retry(operation, "test_operation")

        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_timeout_error(self) -> None:
        """Test operation that times out."""
        service = ConcreteService()
        service.config.api_timeout = 0.1
        service.config.api_max_retries = 1
        service.config.api_retry_delay = 0.05

        async def operation() -> str:
            await asyncio.sleep(1.0)  # Sleep longer than timeout
            return "success"

        with pytest.raises(NetworkError) as exc_info:
            await service._execute_with_retry(operation, "test_operation")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry_quota_exceeded(self) -> None:
        """Test operation that exceeds quota."""
        service = ConcreteService()

        async def operation() -> str:
            raise ResourceExhausted("Quota exceeded")

        with pytest.raises(QuotaExceededError) as exc_info:
            await service._execute_with_retry(operation, "test_operation")

        assert "quota exceeded" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry_permission_denied(self) -> None:
        """Test operation with permission denied."""
        service = ConcreteService()

        async def operation() -> str:
            raise PermissionDenied("Permission denied")

        with pytest.raises(PermissionError) as exc_info:
            await service._execute_with_retry(operation, "test_operation")

        assert "permission denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry_forbidden(self) -> None:
        """Test operation with forbidden error."""
        service = ConcreteService()

        async def operation() -> str:
            raise Forbidden("Forbidden")

        with pytest.raises(PermissionError) as exc_info:
            await service._execute_with_retry(operation, "test_operation")

        assert "permission denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry_unauthenticated(self) -> None:
        """Test operation with unauthenticated error."""
        service = ConcreteService()

        async def operation() -> str:
            raise Unauthenticated("Unauthenticated")

        with pytest.raises(AuthError) as exc_info:
            await service._execute_with_retry(operation, "test_operation")

        assert "authentication failed" in str(exc_info.value).lower()
        assert "gcloud auth" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry_not_found(self) -> None:
        """Test operation with resource not found."""
        service = ConcreteService()

        async def operation() -> str:
            raise NotFound("Resource not found")

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service._execute_with_retry(operation, "test_operation")

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry_service_not_enabled(self) -> None:
        """Test operation when API is not enabled."""
        service = ConcreteService()

        async def operation() -> str:
            from google.api_core.exceptions import GoogleAPIError

            raise GoogleAPIError("API has not been enabled for project")

        with pytest.raises(ServiceNotEnabledError) as exc_info:
            await service._execute_with_retry(operation, "test_operation")

        assert "not enabled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry_deadline_exceeded(self) -> None:
        """Test operation with deadline exceeded (retryable)."""
        service = ConcreteService()
        service.config.api_max_retries = 1
        service.config.api_retry_delay = 0.05

        attempt_count = 0

        async def operation() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise DeadlineExceeded("Deadline exceeded")
            return "success"

        result = await service._execute_with_retry(operation, "test_operation")

        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausts_retries(self) -> None:
        """Test operation that exhausts all retries."""
        service = ConcreteService()
        service.config.api_max_retries = 2
        service.config.api_retry_delay = 0.05

        async def operation() -> str:
            raise ServiceUnavailable("Always fails")

        with pytest.raises(NetworkError):
            await service._execute_with_retry(operation, "test_operation")

    @pytest.mark.asyncio
    async def test_execute_with_retry_exponential_backoff(self) -> None:
        """Test that retry delay uses exponential backoff."""
        service = ConcreteService()
        service.config.api_max_retries = 3
        service.config.api_retry_delay = 0.1
        service.config.api_retry_backoff = 2.0

        attempt_count = 0
        delays = []

        async def operation() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise ServiceUnavailable("Temporary error")
            return "success"

        # Patch asyncio.sleep to capture delays
        original_sleep = asyncio.sleep

        async def mock_sleep(delay: float) -> None:
            delays.append(delay)
            await original_sleep(0.01)  # Use small delay for test speed

        with patch("asyncio.sleep", side_effect=mock_sleep):
            result = await service._execute_with_retry(operation, "test_operation")

        assert result == "success"
        # Verify exponential backoff: 0.1, 0.2, 0.4
        assert len(delays) == 3
        assert delays[0] == pytest.approx(0.1)
        assert delays[1] == pytest.approx(0.2)
        assert delays[2] == pytest.approx(0.4)

    def test_extract_permission_error_with_permission_name(self) -> None:
        """Test extracting permission name from error."""
        service = ConcreteService()
        error = Exception("Permission 'compute.instances.list' denied")

        result = service._extract_permission_error(error)

        assert "compute.instances.list" in result
        assert "Missing permission" in result

    def test_extract_permission_error_generic(self) -> None:
        """Test extracting permission error without specific permission."""
        service = ConcreteService()
        error = Exception("Access denied")

        result = service._extract_permission_error(error)

        assert result == "Access denied"

    def test_extract_api_name_from_googleapis_url(self) -> None:
        """Test extracting API name from googleapis.com URL."""
        service = ConcreteService()
        error = Exception("The API compute.googleapis.com is not enabled")

        result = service._extract_api_name(error)

        assert result == "compute.googleapis.com"

    def test_extract_api_name_from_api_brackets(self) -> None:
        """Test extracting API name from [API] format."""
        service = ConcreteService()
        error = Exception("API [Cloud SQL Admin API] has not been used")

        result = service._extract_api_name(error)

        assert result == "Cloud SQL Admin API"

    def test_extract_api_name_generic(self) -> None:
        """Test extracting API name when pattern doesn't match."""
        service = ConcreteService()
        error = Exception("Some other error")

        result = service._extract_api_name(error)

        assert result == "the required API"

    @pytest.mark.asyncio
    async def test_get_auth_manager_lazy_load(self) -> None:
        """Test that auth manager is lazy-loaded."""
        service = ConcreteService()

        assert service._auth_manager is None

        # Mock the global get_auth_manager function
        mock_auth = MagicMock()
        with patch(
            "sequel.services.base.get_auth_manager",
            return_value=mock_auth,
        ):
            result = await service._get_auth_manager()

            assert result is mock_auth
            assert service._auth_manager is mock_auth

    @pytest.mark.asyncio
    async def test_get_auth_manager_returns_cached(self) -> None:
        """Test that auth manager is cached after first load."""
        service = ConcreteService()

        mock_auth = MagicMock()
        service._auth_manager = mock_auth

        result = await service._get_auth_manager()

        assert result is mock_auth
