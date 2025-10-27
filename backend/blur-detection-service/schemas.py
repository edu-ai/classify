from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BlurAnalysisResult(BaseModel):
    photo_id: str = Field(..., description="Photos ID")
    google_photo_id: str = Field(..., description="Google Photos ID")
    filename: Optional[str] = Field(None, description="File Name")
    blur_score: float = Field(..., description="Detection Score (0.0-1.0)")
    is_blurred: bool = Field(..., description="Detection Result")
    processed_at: datetime = Field(..., description="Processed At")
    processing_time_ms: float = Field(..., description="Processed In")

    class Config:
        from_attributes = True

class BlurAnalysisRequest(BaseModel):
    threshold: Optional[float] = Field(
        0.30,
        ge=0.0,
        le=1.0,
        description="Threshold"
    )
    method: Optional[str] = Field(
        "hybrid",
        description="Detection method (laplacian, fft, hybrid, or other for blur-detector fallback)"
    )
    use_face_detection: Optional[bool] = Field(
        True,
        description="Enable face detection for more accurate blur analysis on portrait photos"
    )

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error Type")
    message: str = Field(..., description="Error Message")
    detail: Optional[str] = Field(None, description="Details")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service Status")
    service: str = Field(..., description="Service Name")
    timestamp: datetime = Field(..., description="Date At")
    version: str = Field("1.0.0", description="Service Version")
