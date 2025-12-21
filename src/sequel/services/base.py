"""Base service class for Google Cloud API interactions.

This module provides a base class for all GCloud service wrappers with
common error handling, retry logic, and timeout management.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from google.api_core.exceptions import (
    DeadlineExceeded,
    Forbidden,
    GoogleAPIError,
    NotFound,
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
    Unauthenticated,
)

from sequel.config import get_config
from sequel.services.auth import AuthError, AuthManager, get_auth_manager
from sequel.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class PermissionError(Exception):
    """Permission denied error."""

    pass


class QuotaExceededError(Exception):
    """API quota exceeded error."""

    pass


class NetworkError(Exception):
    """Network or connectivity error."""

    pass


class ServiceNotEnabledError(Exception):
    """GCloud API service not enabled error."""

    pass


class ResourceNotFoundError(Exception):
    """Resource not found error."""

    pass


class BaseService:
    """Base class for Google Cloud service wrappers.

    This class provides:
    - Automatic retry with exponential backoff
    - Timeout handling
    - Error categorization and handling
    - Authentication integration
    """

    def __init__(self) -> None:
        """Initialize the base service."""
        self.config = get_config()
        self._auth_manager: AuthManager | None = None

    async def _get_auth_manager(self) -> "AuthManager":
        """Get the auth manager (lazy-loaded).

        Returns:
            AuthManager instance
        """
        if self._auth_manager is None:
            self._auth_manager = await get_auth_manager()
        return self._auth_manager

    async def _execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_name: str,
    ) -> T:
        """Execute an operation with retry logic.

        Args:
            operation: Async callable to execute
            operation_name: Human-readable operation name for logging

        Returns:
            Result of the operation

        Raises:
            Various service-specific exceptions based on error type
        """
        max_retries = self.config.api_max_retries
        retry_delay = self.config.api_retry_delay
        backoff = self.config.api_retry_backoff

        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"Executing {operation_name} (attempt {attempt + 1}/{max_retries + 1})"
                )

                # Execute with timeout
                result: T = await asyncio.wait_for(
                    operation(),
                    timeout=self.config.api_timeout,
                )

                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt + 1} attempts")

                return result

            except TimeoutError:
                last_exception = NetworkError(
                    f"{operation_name} timed out after {self.config.api_timeout}s"
                )
                logger.warning(f"{operation_name} timed out on attempt {attempt + 1}")

            except (ServiceUnavailable, DeadlineExceeded) as e:
                last_exception = NetworkError(f"{operation_name} failed: {e}")
                logger.warning(f"{operation_name} failed (network/timeout): {e}")

            except ResourceExhausted as e:
                last_exception = QuotaExceededError(
                    f"API quota exceeded for {operation_name}. "
                    f"Please wait {self.config.gcloud_quota_wait_time}s or request quota increase. "
                    f"Error: {e}"
                )
                logger.error(f"{operation_name} failed due to quota: {e}")
                # Don't retry quota errors
                raise last_exception from e

            except (PermissionDenied, Forbidden) as e:
                # Extract permission details if available
                permission_msg = self._extract_permission_error(e)
                last_exception = PermissionError(
                    f"Permission denied for {operation_name}: {permission_msg}"
                )
                logger.error(f"{operation_name} failed due to permissions: {e}")
                # Don't retry permission errors
                raise last_exception from e

            except Unauthenticated as e:
                last_exception = AuthError(
                    f"Authentication failed for {operation_name}. "
                    "Please run 'gcloud auth application-default login'. "
                    f"Error: {e}"
                )
                logger.error(f"{operation_name} failed due to authentication: {e}")
                # Don't retry auth errors
                raise last_exception from e

            except NotFound as e:
                last_exception = ResourceNotFoundError(
                    f"Resource not found for {operation_name}: {e}"
                )
                logger.error(f"{operation_name} failed - resource not found: {e}")
                # Don't retry not found errors
                raise last_exception from e

            except GoogleAPIError as e:
                # Check if API is not enabled
                if "has not been used" in str(e) or "API has not been enabled" in str(e):
                    api_name = self._extract_api_name(e)
                    last_exception = ServiceNotEnabledError(
                        f"Google Cloud API not enabled: {api_name}. "
                        f"Enable it at: https://console.cloud.google.com/apis/library/{api_name}. "
                        f"Error: {e}"
                    )
                    logger.error(f"{operation_name} failed - API not enabled: {e}")
                    raise last_exception from e
                else:
                    last_exception = Exception(f"{operation_name} failed: {e}")
                    logger.warning(f"{operation_name} failed with API error: {e}")

            except Exception as e:
                last_exception = Exception(f"{operation_name} failed unexpectedly: {e}")
                logger.error(f"{operation_name} failed with unexpected error: {e}")
                # Don't retry unexpected errors
                raise last_exception from e

            # Retry logic - only reached if we didn't raise
            if attempt < max_retries:
                wait_time = retry_delay * (backoff**attempt)
                logger.info(f"Retrying {operation_name} in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

        # All retries exhausted
        if last_exception:
            logger.error(
                f"{operation_name} failed after {max_retries + 1} attempts"
            )
            raise last_exception
        else:
            raise Exception(f"{operation_name} failed after all retries")

    def _extract_permission_error(self, error: Exception) -> str:
        """Extract permission details from error.

        Args:
            error: Permission error

        Returns:
            Human-readable permission error message
        """
        error_str = str(error)

        # Try to extract permission name
        if "Permission" in error_str:
            # Example: "Permission 'compute.instances.list' denied"
            import re

            match = re.search(r"Permission ['\"]([^'\"]+)['\"]", error_str)
            if match:
                permission = match.group(1)
                return (
                    f"Missing permission: {permission}. "
                    f"Grant this permission in IAM or contact your administrator."
                )

        return error_str

    def _extract_api_name(self, error: Exception) -> str:
        """Extract API name from error message.

        Args:
            error: API error

        Returns:
            API name or generic message
        """
        error_str = str(error)

        # Common patterns
        patterns = [
            r"([a-z]+\.googleapis\.com)",
            r"API \[([^\]]+)\]",
        ]

        for pattern in patterns:
            import re

            match = re.search(pattern, error_str)
            if match:
                return match.group(1)

        return "the required API"
