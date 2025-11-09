import os
import time
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from blur_tasks import analyze_single_photo
from tag_detector import ai_tagger

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import requests

import json
from worker import enqueue_photo_analysis
from redis_client import redis_client
from pydantic import BaseModel

class BatchRequest(BaseModel):
    user_id: UUID
    photo_ids: List[UUID]
    threshold: float = 0.30
    method: str = "hybrid"
    use_face_detection: bool = True

from schemas import (
    BlurAnalysisResult,
    BlurAnalysisRequest,
    ErrorResponse,
    HealthResponse
)
from blur_detector import blur_detector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Classify Blur Detection Servicey", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PHOTOS_SERVICE_URL = os.getenv("PHOTOS_SERVICE_URL", "http://photos-service:8000")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        service="blur-detection-service",
        timestamp=datetime.utcnow()
    )

@app.post("/analyze/batch")
async def analyze_batch_photo(req: BatchRequest):
    logger.info(f"Received batch request: {req}")
    for photo_id in req.photo_ids:
        enqueue_photo_analysis(photo_id, req.user_id, req.threshold, req.method, req.use_face_detection)
    return {"status": "queued", "count": len(req.photo_ids)}

@app.post("/analyze/{photo_id}", response_model=BlurAnalysisResult)
async def analyze_single_photo(
    photo_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    request_body: Optional[BlurAnalysisRequest] = BlurAnalysisRequest(),
):
    start_time = time.time()

    try:
        response = requests.get(
            f"{PHOTOS_SERVICE_URL}/photos/{photo_id}/meta",
            params={"user_id": str(user_id)},
            timeout=10
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        photo = response.json()
        if not photo:
            raise HTTPException(status_code=404, detail=f"Photo not found: {photo_id}")

        logger.info(f"Analysis started: photo_id={photo_id}, user_id={user_id}")
        threshold = request_body.threshold
        method = request_body.method
        use_face_detection = request_body.use_face_detection
        image_bytes = await _fetch_image_from_photo_service(
            photo["google_photo_id"],
            user_id
        )

        logger.info(f"Detection started: photo_id={photo_id}, user_id={user_id}, face_detection={use_face_detection}")
        blur_score, is_blurred = blur_detector.detect_blur_from_bytes(
            image_bytes,
            threshold,
            method,
            use_face_detection
        )

        is_blurred = bool(is_blurred)
        blur_score = float(blur_score)

        processed_at = datetime.utcnow().isoformat()
        update_response = requests.patch(
            f"{PHOTOS_SERVICE_URL}/photos/{photo_id}",
            params={"user_id": str(user_id)},
            json={
                "blur_score": float(blur_score),
                "is_blurred": bool(is_blurred),
                "processed_at": datetime.utcnow().isoformat()
            },
            timeout=10
        )
        if update_response.status_code != 200:
            raise HTTPException(status_code=update_response.status_code, detail=update_response.text)

        processing_time = (time.time() - start_time) * 1000  # ms

        logger.info(
            f"Analysis completed: photo_id={photo_id}, "
            f"blur_score={blur_score:.4f}, "
            f"is_blurred={is_blurred}, "
            f"time={processing_time:.2f}ms"
        )

        return BlurAnalysisResult(
            photo_id=photo["id"],
            google_photo_id=photo["google_photo_id"],
            filename=photo.get("filename"),
            blur_score=blur_score,
            is_blurred=is_blurred,
            processed_at=datetime.fromisoformat(processed_at),
            processing_time_ms=processing_time
        )

    except Exception as e:
        logger.error(f"Analysis error: photo_id={photo_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Blur analysis failed: {str(e)}")

async def _fetch_image_from_photo_service(
    google_photo_id: str,
    user_id: UUID
) -> bytes:
    try:
        proxy_url = f"{PHOTOS_SERVICE_URL}/photo/{google_photo_id}"
        params = {"user_id": str(user_id)}

        logger.info(f"Image fetch started: {proxy_url}")

        response = requests.get(
            proxy_url,
            params=params,
            timeout=30,
            stream=True
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Photo not found in Google Photos"
            )
        elif response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="Photo access expired, please refresh photos"
            )
        elif response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch image: {response.text}"
            )

        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {content_type}"
            )

        image_bytes = response.content

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Empty image data received"
            )

        logger.info(
            f"Image fetch completed: size={len(image_bytes)} bytes, "
            f"content_type={content_type}"
        )

        return image_bytes

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=408,
            detail="Timeout while fetching image"
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Photo Service"
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Network error while fetching image: {str(e)}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        detail=str(exc)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )

@app.post("/tag/{photo_id}")
async def tag_photo(
    photo_id: UUID,
    user_id: UUID = Query(..., description="User ID")
):
    try:
        response = requests.get(
            f"{PHOTOS_SERVICE_URL}/photos/{photo_id}/meta",
            params={"user_id": str(user_id)},
            timeout=10
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        photo = response.json()

        image_bytes = await _fetch_image_from_photo_service(
            photo["google_photo_id"],
            user_id
        )

        tag = ai_tagger.generate_tags(image_bytes)

        update_response = requests.patch(
            f"{PHOTOS_SERVICE_URL}/photos/{photo_id}",
            params={"user_id": str(user_id)},
            json={
                "tag": tag,
                "tagged_at": datetime.utcnow().isoformat()
            },
            timeout=10
        )

        if update_response.status_code != 200:
            raise HTTPException(status_code=update_response.status_code, detail=update_response.text)

        return {
            "photo_id": str(photo_id),
            "tag": tag,
            "tagged_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Tagging failed: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))
