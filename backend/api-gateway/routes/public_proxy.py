"""Public proxy endpoints to bridge frontend calls to internal services.

This router exposes minimal proxy endpoints under /api to match the
frontend's current expectations (which were previously calling services
directly). Authentication is not enforced here because the underlying
photos-service handles user authorization via auth-service and the
frontend currently does not attach a bearer token for these specific
calls.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse

from config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Public Proxy"])


@router.get("/sessions/{user_id}")
async def proxy_picker_session(user_id: str):
    """Proxy to photos-service to create a Google Photos Picker session.

    Forwards to: photos-service GET /sessions/{user_id}
    """
    url = f"{settings.photos_service_url}/sessions/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.get(url)
        if r.status_code != 200:
            logger.error(f"photos-service /sessions returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=200, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy picker session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create picker session")


@router.get("/mediaItems/{user_id}")
async def proxy_media_items(user_id: str, sessionId: str = Query(...)):
    """Proxy to photos-service to import media items from a picker session.

    Forwards to: photos-service GET /mediaItems/{user_id}?sessionId=...
    """
    url = f"{settings.photos_service_url}/mediaItems/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.get(url, params={"sessionId": sessionId})
        if r.status_code != 200:
            logger.error(f"photos-service /mediaItems returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        # photos-service returns boolean true/false; forward as JSON true/false
        if r.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse(status_code=200, content=r.json())
        return JSONResponse(status_code=200, content={"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy media items: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch media items")


@router.post("/register")
async def proxy_auth_register(payload: dict):
    """Proxy to auth-service for user registration/login bootstrap.

    Forwards to: auth-service POST /register
    """
    url = f"{settings.auth_service_url}/register"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.post(url, json=payload)
        if r.status_code >= 400:
            logger.error(f"auth-service /register returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy auth register: {e}")
        raise HTTPException(status_code=500, detail="Failed to register user")


@router.post("/oauth/store-token")
async def proxy_auth_store_token(payload: dict):
    """Proxy to auth-service to store OAuth tokens from NextAuth.

    Forwards to: auth-service POST /oauth/store-token
    """
    url = f"{settings.auth_service_url}/oauth/store-token"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.post(url, json=payload)
        if r.status_code >= 400:
            logger.error(f"auth-service /oauth/store-token returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy auth store-token: {e}")
        raise HTTPException(status_code=500, detail="Failed to store token")


@router.get("/tokens/{user_id}")
async def proxy_auth_get_token(user_id: str):
    """Proxy to auth-service to fetch a valid access token for a user.

    Forwards to: auth-service GET /tokens/{user_id}
    """
    url = f"{settings.auth_service_url}/tokens/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.get(url)
        if r.status_code >= 400:
            logger.error(f"auth-service /tokens returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy auth tokens: {e}")
        raise HTTPException(status_code=500, detail="Failed to get access token")


@router.get("/photos/{user_id}")
async def proxy_user_photos(user_id: str):
    """Proxy to photos-service for listing user's photos in frontend format.

    Forwards to: photos-service GET /photos/{user_id}
    """
    url = f"{settings.photos_service_url}/photos/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.get(url)
        if r.status_code != 200:
            logger.error(f"photos-service /photos/{user_id} returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=200, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy user photos: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch photos")


@router.get("/photo/{media_item_id}")
async def proxy_photo(media_item_id: str, user_id: str):
    """Proxy photo from photos-service.

    Args:
        media_item_id: Google Photos media item ID
        user_id: User UUID

    Returns:
        Photo content as Response
    """
    try:
        url = f"{settings.photos_service_url}/photo/{media_item_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Bulk fetch (to avoid StreamingResponse issues)
            response = await client.get(url, params={"user_id": user_id})
            response.raise_for_status()

            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={
                    "Cache-Control": "public, max-age=31536000",
                    "Content-Length": str(len(response.content)),
                    "Content-Disposition": f"inline; filename={media_item_id}.jpg"
                }
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while proxying photo (status={e.response.status_code}): {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to fetch photo from upstream: {e.response.status_code}"
        )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout while proxying photo: {e}")
        raise HTTPException(status_code=504, detail="Upstream service timeout")
    except Exception as e:
        logger.error(f"Failed to proxy photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch photo")


@router.post("/analyze/batch")
async def proxy_blur_analyze_batch(payload: dict):
    """Proxy to blur-detection-service for batch analysis.

    Forwards to: blur-detection-service POST /analyze/batch
    Body is forwarded as-is.
    """
    url = f"{settings.blur_detection_service_url}/analyze/batch"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.post(url, json=payload)
        if r.status_code >= 400:
            logger.error(f"blur-detection /analyze/batch returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy blur analyze batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue batch analysis")


@router.post("/analyze/{photo_id}")
async def proxy_blur_analyze(photo_id: str, user_id: str, threshold: Optional[float] = None):
    """Proxy to blur-detection-service to analyze a single photo.

    Forwards to: blur-detection-service POST /analyze/{photo_id}?user_id=... with optional JSON body
    {"threshold": <float>}.
    """
    url = f"{settings.blur_detection_service_url}/analyze/{photo_id}"
    json_body = {"threshold": threshold} if threshold is not None else None
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.post(url, params={"user_id": user_id}, json=json_body)
        if r.status_code >= 400:
            logger.error(f"blur-detection /analyze returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy blur analyze: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze photo")


@router.post("/tag/{photo_id}")
async def proxy_blur_tag(photo_id: str, user_id: str = Query(...)):
    """Proxy to blur-detection-service to generate AI tags for a photo.

    Forwards to: blur-detection-service POST /tag/{photo_id}?user_id=...
    """
    url = f"{settings.blur_detection_service_url}/tag/{photo_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.post(url, params={"user_id": user_id})
        if r.status_code >= 400:
            logger.error(f"blur-detection /tag returned {r.status_code}: {r.text}")
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy blur tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate tags for photo")


@router.get("/service/auth/health")
async def proxy_auth_health():
    """Proxy to auth-service health check.

    Forwards to: auth-service GET /health
    """
    url = f"{settings.auth_service_url}/health"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception as e:
        logger.error(f"Failed to proxy auth health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check auth service health")


@router.get("/service/photos/health")
async def proxy_photos_health():
    """Proxy to photos-service health check.

    Forwards to: photos-service GET /health
    """
    url = f"{settings.photos_service_url}/health"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception as e:
        logger.error(f"Failed to proxy photos health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check photos service health")


@router.get("/service/blur/health")
async def proxy_blur_health():
    """Proxy to blur-detection-service health check.

    Forwards to: blur-detection-service GET /health
    """
    url = f"{settings.blur_detection_service_url}/health"
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout) as client:
            r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception as e:
        logger.error(f"Failed to proxy blur health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check blur detection service health")
