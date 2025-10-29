"""Photo management request and response schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PhotoFilter(str, Enum):
    """Photo filter options for listing photos."""

    ALL = "all"
    BLURRED = "blurred"
    NOT_BLURRED = "not_blurred"
    UNPROCESSED = "unprocessed"


class PhotoResponse(BaseModel):
    """Response schema for photo information."""

    id: str = Field(..., description="Photo ID")
    user_id: str = Field(..., description="Owner user ID")
    google_photo_id: str = Field(..., description="Google Photos ID")
    filename: Optional[str] = Field(None, description="Photo filename")
    media_type: str = Field(default="IMAGE", description="Media type (IMAGE, VIDEO)")
    blur_score: Optional[float] = Field(None, description="Blur detection score (0-100, lower = more blurred)")
    is_blurred: Optional[bool] = Field(None, description="Whether photo is blurred")
    processed_at: Optional[datetime] = Field(None, description="Blur analysis completion timestamp")
    google_created_time: Optional[datetime] = Field(None, description="Photo creation time in Google Photos")
    width: Optional[int] = Field(None, description="Photo width in pixels")
    height: Optional[int] = Field(None, description="Photo height in pixels")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type (e.g., image/jpeg)")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "photo_123abc",
                "user_id": "user_123abc",
                "google_photo_id": "AKPKj3...",
                "filename": "IMG_1234.jpg",
                "media_type": "IMAGE",
                "blur_score": 45.2,
                "is_blurred": True,
                "processed_at": "2025-01-15T10:30:00Z",
                "google_created_time": "2025-01-10T08:00:00Z",
                "width": 4032,
                "height": 3024,
                "file_size": 2048576,
                "mime_type": "image/jpeg",
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
            }
        }


class PhotosListResponse(BaseModel):
    """Response schema for photo list endpoint."""

    items: List[PhotoResponse] = Field(..., description="List of photos")
    total: int = Field(..., description="Total number of photos matching filter")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Current offset")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "photo_123abc",
                        "user_id": "user_123abc",
                        "google_photo_id": "AKPKj3...",
                        "filename": "IMG_1234.jpg",
                        "media_type": "IMAGE",
                        "blur_score": 45.2,
                        "is_blurred": True,
                        "processed_at": "2025-01-15T10:30:00Z",
                        "google_created_time": "2025-01-10T08:00:00Z",
                        "width": 4032,
                        "height": 3024,
                        "file_size": 2048576,
                        "mime_type": "image/jpeg",
                        "created_at": "2025-01-15T10:00:00Z",
                        "updated_at": "2025-01-15T10:30:00Z",
                    }
                ],
                "total": 150,
                "limit": 50,
                "offset": 0,
            }
        }


class CreatePhotoRequest(BaseModel):
    """Request schema for creating photo metadata."""

    google_photo_id: str = Field(..., description="Google Photos ID")
    filename: Optional[str] = Field(None, description="Photo filename")
    media_type: str = Field(default="IMAGE", description="Media type (IMAGE, VIDEO)")
    google_created_time: Optional[datetime] = Field(None, description="Photo creation time in Google Photos")
    width: Optional[int] = Field(None, ge=1, description="Photo width in pixels")
    height: Optional[int] = Field(None, ge=1, description="Photo height in pixels")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type (e.g., image/jpeg)")

    class Config:
        json_schema_extra = {
            "example": {
                "google_photo_id": "AKPKj3...",
                "filename": "IMG_1234.jpg",
                "media_type": "IMAGE",
                "google_created_time": "2025-01-10T08:00:00Z",
                "width": 4032,
                "height": 3024,
                "file_size": 2048576,
                "mime_type": "image/jpeg",
            }
        }


class DeletePhotoResponse(BaseModel):
    """Response schema for photo deletion."""

    success: bool = Field(default=True, description="Deletion success status")
    message: str = Field(..., description="Deletion confirmation message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Photo deleted successfully",
            }
        }


class UnblurredAlbumResponse(BaseModel):
    """Response schema for unblurred album creation."""

    albumId: str = Field(..., description="Google Photos album ID")
    albumTitle: str = Field(..., description="Album title")
    uploadedCount: int = Field(..., description="Number of photos uploaded to the album")

    class Config:
        json_schema_extra = {
            "example": {
                "albumId": "AKPKj3...",
                "albumTitle": "Unblurred Photos 2025-01-15",
                "uploadedCount": 12,
            }
        }
