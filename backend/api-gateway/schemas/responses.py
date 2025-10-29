"""Response schemas for API Gateway."""

from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response format.

    All errors from the API Gateway follow this format for consistency.
    """

    error: str = Field(..., description="Error type/class name")
    message: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
    service: Optional[str] = Field(None, description="Service that raised the error")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    request_id: Optional[str] = Field(
        None, description="Request ID for tracking and debugging"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "AuthenticationError",
                "message": "Invalid or expired token",
                "status_code": 401,
                "service": "auth-service",
                "details": {"token_expired": True},
                "request_id": "req_123abc",
            }
        }


class SuccessResponse(BaseModel):
    """Standard success response format for operations without specific data.

    Used for operations like delete, update acknowledgements, etc.
    """

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional response data")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Photo deleted successfully",
                "data": {"photo_id": "photo_123"},
            }
        }


class HealthResponse(BaseModel):
    """Health check response format."""

    status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    checks: Optional[Dict[str, Any]] = Field(
        None, description="Individual health check results"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "api-gateway",
                "version": "1.0.0",
                "checks": {
                    "redis": "connected",
                    "auth_service": "reachable",
                    "photos_service": "reachable",
                },
            }
        }


class PaginatedResponse(BaseModel):
    """Generic paginated response format."""

    items: list[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether there are more items")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [{"id": "1", "name": "Item 1"}],
                "total": 100,
                "limit": 20,
                "offset": 0,
                "has_more": True,
            }
        }
