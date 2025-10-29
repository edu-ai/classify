"""Photo management endpoints for API Gateway."""

import logging
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional

from clients.photos_client import PhotosServiceClient
from middleware.auth import get_current_user
from schemas.photos import (
    PhotoResponse,
    PhotosListResponse,
    PhotoFilter,
    CreatePhotoRequest,
    DeletePhotoResponse,
)
from exceptions import ResourceNotFoundError, AuthorizationError, ServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/photos", tags=["Photos"])


def _map_filter_to_blur_status(filter_type: PhotoFilter) -> Optional[str]:
    """Map PhotoFilter enum to blur_status parameter for photos-service.

    Args:
        filter_type: PhotoFilter enum value

    Returns:
        blur_status string or None for "all"
    """
    mapping = {
        PhotoFilter.ALL: None,
        PhotoFilter.BLURRED: "blurred",
        PhotoFilter.NOT_BLURRED: "clear",
        PhotoFilter.UNPROCESSED: "null",
    }
    return mapping.get(filter_type)


@router.get(
    "",
    response_model=PhotosListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user photos",
    description="Get a paginated list of photos for the authenticated user. "
    "Supports filtering by blur status.",
)
async def get_photos(
    filter: PhotoFilter = Query(
        PhotoFilter.ALL,
        description="Filter photos by blur status: "
        "all (no filter), blurred (only blurred photos), "
        "not_blurred (only clear photos), unprocessed (not analyzed yet)"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Number of photos to return per page (1-100)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of photos to skip (for pagination)"
    ),
    current_user: dict = Depends(get_current_user),
):
    """Get user's photos with optional filtering and pagination.

    This endpoint retrieves photos belonging to the authenticated user.
    Photos can be filtered by blur analysis status.

    Headers:
        Authorization: Bearer {access_token}

    Args:
        filter: Filter type (all, blurred, not_blurred, unprocessed)
        limit: Number of items per page (1-100)
        offset: Pagination offset
        current_user: User info from authentication middleware

    Returns:
        PhotosListResponse with items, total, limit, offset

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 503 if photos-service is unavailable
    """
    try:
        user_id = current_user.get("user_id")
        token = current_user.get("token")

        if not user_id or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication data",
            )

        logger.info(f"Fetching photos for user {user_id} with filter={filter.value}")

        # Map filter to blur_status parameter
        blur_status = _map_filter_to_blur_status(filter)

        async with PhotosServiceClient() as photos_client:
            photos_data = await photos_client.get_user_photos(
                user_id=user_id,
                token=token,
                limit=limit,
                offset=offset,
                blur_status=blur_status,
            )

        # Extract photos from response
        # photos-service may return {"photos": [...], "total": N} or {"items": [...], "total": N}
        items = photos_data.get("photos") or photos_data.get("items", [])
        total = photos_data.get("total", len(items))

        logger.info(f"Retrieved {len(items)} photos for user {user_id}")

        return PhotosListResponse(
            items=[PhotoResponse(**photo) for photo in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    except (AuthorizationError, ResourceNotFoundError) as e:
        logger.error(f"Authorization/resource error: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except ServiceError as e:
        logger.error(f"Service error getting photos: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting photos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get photos",
        )


@router.get(
    "/{photo_id}",
    response_model=PhotoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get photo details",
    description="Get detailed information about a specific photo. "
    "User must be the owner of the photo.",
)
async def get_photo(
    photo_id: str = Path(..., description="Photo ID"),
    current_user: dict = Depends(get_current_user),
):
    """Get detailed information about a specific photo.

    This endpoint retrieves full metadata for a single photo.
    The authenticated user must be the owner of the photo.

    Headers:
        Authorization: Bearer {access_token}

    Args:
        photo_id: Unique photo identifier
        current_user: User info from authentication middleware

    Returns:
        PhotoResponse with full photo metadata

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if photo not found or user doesn't own it
        HTTPException: 503 if photos-service is unavailable
    """
    try:
        user_id = current_user.get("user_id")
        token = current_user.get("token")

        if not user_id or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication data",
            )

        logger.info(f"Fetching photo {photo_id} for user {user_id}")

        async with PhotosServiceClient() as photos_client:
            photo_data = await photos_client.get_photo(
                photo_id=photo_id,
                user_id=user_id,
                token=token,
            )

        # Verify ownership
        if photo_data.get("user_id") != user_id:
            logger.warning(f"User {user_id} attempted to access photo {photo_id} owned by {photo_data.get('user_id')}")
            raise ResourceNotFoundError(
                message="Photo not found",
                resource_type="photo",
                resource_id=photo_id,
            )

        logger.info(f"Photo {photo_id} retrieved successfully")
        return PhotoResponse(**photo_data)

    except ResourceNotFoundError as e:
        logger.error(f"Photo not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except (AuthorizationError, ServiceError) as e:
        logger.error(f"Error getting photo: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting photo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get photo details",
        )


@router.post(
    "",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create photo metadata",
    description="Create a new photo metadata entry. "
    "This is typically called after importing photos from Google Photos.",
)
async def create_photo(
    request: CreatePhotoRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create new photo metadata entry.

    This endpoint creates a new photo record in the database.
    Typically called after importing photos from Google Photos API.
    The blur analysis can be triggered separately.

    Headers:
        Authorization: Bearer {access_token}

    Args:
        request: Photo metadata to create
        current_user: User info from authentication middleware

    Returns:
        PhotoResponse with created photo data

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 422 if validation fails
        HTTPException: 503 if photos-service is unavailable
    """
    try:
        user_id = current_user.get("user_id")
        token = current_user.get("token")

        if not user_id or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication data",
            )

        logger.info(f"Creating photo for user {user_id}")

        async with PhotosServiceClient() as photos_client:
            photo_data = await photos_client.create_photo(
                user_id=user_id,
                token=token,
                photo_data=request.model_dump(),
            )

        logger.info(f"Photo created successfully: {photo_data.get('id')}")
        return PhotoResponse(**photo_data)

    except (AuthorizationError, ServiceError) as e:
        logger.error(f"Error creating photo: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating photo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create photo",
        )


@router.delete(
    "/{photo_id}",
    response_model=DeletePhotoResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete photo",
    description="Delete a photo and its metadata. "
    "User must be the owner of the photo.",
)
async def delete_photo(
    photo_id: str = Path(..., description="Photo ID"),
    current_user: dict = Depends(get_current_user),
):
    """Delete a photo and its metadata.

    This endpoint permanently deletes a photo record from the database.
    The authenticated user must be the owner of the photo.
    Note: This only deletes metadata, not the actual photo file in Google Photos.

    Headers:
        Authorization: Bearer {access_token}

    Args:
        photo_id: Unique photo identifier
        current_user: User info from authentication middleware

    Returns:
        DeletePhotoResponse with success message

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if photo not found or user doesn't own it
        HTTPException: 503 if photos-service is unavailable
    """
    try:
        user_id = current_user.get("user_id")
        token = current_user.get("token")

        if not user_id or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication data",
            )

        logger.info(f"Deleting photo {photo_id} for user {user_id}")

        async with PhotosServiceClient() as photos_client:
            # First, verify ownership by getting the photo
            photo_data = await photos_client.get_photo(
                photo_id=photo_id,
                user_id=user_id,
                token=token,
            )

            # Verify ownership
            if photo_data.get("user_id") != user_id:
                logger.warning(f"User {user_id} attempted to delete photo {photo_id} owned by {photo_data.get('user_id')}")
                raise ResourceNotFoundError(
                    message="Photo not found",
                    resource_type="photo",
                    resource_id=photo_id,
                )

            # Delete the photo
            await photos_client.delete_photo(
                photo_id=photo_id,
                user_id=user_id,
                token=token,
            )

        logger.info(f"Photo {photo_id} deleted successfully")
        return DeletePhotoResponse(
            success=True,
            message="Photo deleted successfully",
        )

    except ResourceNotFoundError as e:
        logger.error(f"Photo not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except (AuthorizationError, ServiceError) as e:
        logger.error(f"Error deleting photo: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting photo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete photo",
        )
