"""Custom exceptions for API Gateway."""

from typing import Optional


class ServiceError(Exception):
    """Base exception for service errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        service_name: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """Initialize service error.

        Args:
            message: Error message
            status_code: HTTP status code
            service_name: Name of the service that raised the error
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.service_name = service_name
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON response."""
        error_dict = {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
        }
        if self.service_name:
            error_dict["service"] = self.service_name
        if self.details:
            error_dict["details"] = self.details
        return error_dict


class ServiceUnavailableError(ServiceError):
    """Raised when a backend service is unavailable.

    This typically occurs due to:
    - Network connectivity issues
    - Service timeout
    - Service not running
    """

    def __init__(
        self,
        message: str = "Service is temporarily unavailable",
        service_name: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            status_code=503,
            service_name=service_name,
            details=details,
        )


class AuthenticationError(ServiceError):
    """Raised when authentication fails.

    This occurs when:
    - Token is invalid or expired
    - Token verification fails
    - User credentials are incorrect
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        service_name: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            service_name=service_name,
            details=details,
        )


class AuthorizationError(ServiceError):
    """Raised when user doesn't have permission.

    This occurs when:
    - User tries to access resources they don't own
    - User lacks required permissions
    - Invalid scope for OAuth token
    """

    def __init__(
        self,
        message: str = "Insufficient permissions",
        service_name: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            service_name=service_name,
            details=details,
        )


class ResourceNotFoundError(ServiceError):
    """Raised when requested resource doesn't exist.

    This occurs when:
    - Photo ID not found
    - User not found
    - Job ID not found
    """

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        service_name: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            status_code=404,
            service_name=service_name,
            details=details,
        )


class ValidationError(ServiceError):
    """Raised when request validation fails.

    This occurs when:
    - Invalid input parameters
    - Missing required fields
    - Data type mismatch
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        validation_details = details or {}
        if field:
            validation_details["field"] = field

        super().__init__(
            message=message,
            status_code=422,
            details=validation_details,
        )


class RateLimitError(ServiceError):
    """Raised when rate limit is exceeded.

    This occurs when:
    - Too many requests in a time window
    - Google Photos API quota exceeded
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        service_name: Optional[str] = None,
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            service_name=service_name,
            details=details,
        )
