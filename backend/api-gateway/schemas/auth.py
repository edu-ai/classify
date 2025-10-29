"""Authentication request and response schemas."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class TokenRequest(BaseModel):
    """Request schema for exchanging Google OAuth code for tokens."""

    code: str = Field(..., description="Google OAuth authorization code")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "4/0AY0e-g7xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            }
        }


class TokenResponse(BaseModel):
    """Response schema for token endpoints."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token for obtaining new access tokens")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "1//0gxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""

    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "1//0gxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            }
        }


class UserResponse(BaseModel):
    """Response schema for user information."""

    id: str = Field(..., description="User ID")
    google_id: str = Field(..., description="Google account ID")
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "user_123abc",
                "google_id": "1234567890",
                "email": "user@example.com",
                "name": "John Doe",
                "profile_picture_url": "https://lh3.googleusercontent.com/a/...",
                "created_at": "2025-01-01T00:00:00Z",
                "last_login_at": "2025-01-15T10:30:00Z",
            }
        }


class LogoutResponse(BaseModel):
    """Response schema for logout endpoint."""

    success: bool = Field(default=True, description="Logout success status")
    message: str = Field(..., description="Logout confirmation message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Logged out successfully",
            }
        }
