"""Blur detection request and response schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status for blur analysis."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BlurAnalysisJobResponse(BaseModel):
    """Response schema for blur analysis job."""

    job_id: str = Field(..., description="Job ID for tracking")
    photo_id: str = Field(..., description="Photo ID being analyzed")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    error: Optional[str] = Field(None, description="Error message if job failed")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_123abc",
                "photo_id": "photo_123abc",
                "status": "pending",
                "created_at": "2025-01-15T10:00:00Z",
                "completed_at": None,
                "error": None,
            }
        }


class BlurAnalysisResultResponse(BaseModel):
    """Response schema for blur analysis result."""

    photo_id: str = Field(..., description="Photo ID")
    blur_score: float = Field(..., description="Blur score (0-100, lower = more blurred)")
    is_blurred: bool = Field(..., description="Whether photo is blurred")
    analysis_method: str = Field(..., description="Analysis method used (e.g., 'opencv', 'laplacian')")
    processed_at: datetime = Field(..., description="Analysis completion timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_id": "photo_123abc",
                "blur_score": 45.2,
                "is_blurred": True,
                "analysis_method": "opencv_laplacian",
                "processed_at": "2025-01-15T10:00:30Z",
            }
        }


class AnalyzePhotoRequest(BaseModel):
    """Request schema for analyzing a photo (optional parameters)."""

    use_face_detection: bool = Field(
        default=False,
        description="Whether to use face detection for focused blur analysis"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "use_face_detection": False,
            }
        }


class BatchAnalyzeRequest(BaseModel):
    """Request schema for batch blur analysis."""

    photo_ids: List[str] = Field(..., min_length=1, max_length=100, description="List of photo IDs to analyze (1-100)")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_ids": ["photo_123abc", "photo_456def", "photo_789ghi"],
            }
        }


class BatchAnalyzeResponse(BaseModel):
    """Response schema for batch blur analysis."""

    jobs: List[BlurAnalysisJobResponse] = Field(..., description="List of created jobs")
    total: int = Field(..., description="Total number of jobs created")

    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [
                    {
                        "job_id": "job_1",
                        "photo_id": "photo_123abc",
                        "status": "pending",
                        "created_at": "2025-01-15T10:00:00Z",
                        "completed_at": None,
                        "error": None,
                    },
                    {
                        "job_id": "job_2",
                        "photo_id": "photo_456def",
                        "status": "pending",
                        "created_at": "2025-01-15T10:00:01Z",
                        "completed_at": None,
                        "error": None,
                    },
                ],
                "total": 2,
            }
        }
