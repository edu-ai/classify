# blur_tasks.py
import os
import time
import logging
from datetime import datetime
from uuid import UUID
import requests
from blur_detector import blur_detector
from schemas import BlurAnalysisResult
from fastapi import HTTPException

logger = logging.getLogger(__name__)

PHOTOS_SERVICE_URL = os.getenv("PHOTOS_SERVICE_URL", "http://photos-service:8000")

def analyze_single_photo(photo_id: UUID, user_id: UUID, threshold: float = 0.30, method: str = "hybrid", use_face_detection: bool = True) -> dict:
    """Blur analysis processing for a single photo"""
    start_time = time.time()

    try:
        # Fetch metadata
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

        # Fetch image
        image_bytes = _fetch_image_from_photo_service(photo["google_photo_id"], user_id)

        # Blur analysis
        blur_score, is_blurred = blur_detector.detect_blur_from_bytes(image_bytes, threshold, method, use_face_detection)
        is_blurred = bool(is_blurred)
        blur_score = float(blur_score)

        processed_at = datetime.utcnow().isoformat()

        # Update results
        update_response = requests.patch(
            f"{PHOTOS_SERVICE_URL}/photos/{photo_id}",
            params={"user_id": str(user_id)},
            json={
                "blur_score": blur_score,
                "is_blurred": is_blurred,
                "processed_at": processed_at
            },
            timeout=10
        )
        if update_response.status_code != 200:
            raise HTTPException(status_code=update_response.status_code, detail=update_response.text)

        processing_time = (time.time() - start_time) * 1000  # ms

        logger.info(
            f"Analysis completed: photo_id={photo_id}, blur_score={blur_score:.4f}, "
            f"is_blurred={is_blurred}, time={processing_time:.2f}ms"
        )

        return {
            "photo_id": photo["id"],
            "google_photo_id": photo["google_photo_id"],
            "filename": photo.get("filename"),
            "blur_score": blur_score,
            "is_blurred": is_blurred,
            "processed_at": processed_at,
            "processing_time_ms": processing_time
        }

    except Exception as e:
        logger.error(f"Analysis error: photo_id={photo_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Blur analysis failed: {str(e)}")

def _fetch_image_from_photo_service(google_photo_id: str, user_id: UUID) -> bytes:
    """Fetch image from Photo Service"""
    try:
        proxy_url = f"{PHOTOS_SERVICE_URL}/photo/{google_photo_id}"
        response = requests.get(proxy_url, params={"user_id": str(user_id)}, timeout=30, stream=True)

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Photo not found")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail="Photo access expired")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch image: {response.text}")

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"Invalid content type: {content_type}")

        return response.content

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network error while fetching image: {str(e)}")
