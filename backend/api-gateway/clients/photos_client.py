"""Photos service client for photo metadata management."""

from typing import Dict, Any, List, Optional
import logging

from clients.base_client import ServiceClient
from exceptions import ResourceNotFoundError, AuthorizationError
from config import settings

logger = logging.getLogger(__name__)


class PhotosServiceClient(ServiceClient):
    """Client for communicating with photos-service.

    Handles:
    - Fetching user photos
    - Getting photo details
    - Updating photo metadata (blur detection results)
    """

    def __init__(self):
        """Initialize photos service client."""
        super().__init__(
            base_url=settings.photos_service_url,
            timeout=settings.service_timeout,
            max_retries=settings.service_max_retries,
        )

    async def get_user_photos(
        self,
        user_id: str,
        token: str,
        limit: int = 50,
        offset: int = 0,
        blur_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get photos for a specific user.

        Note: The actual photos-service endpoint does not support limit, offset,
        or blur_status filtering yet. These parameters are kept for future implementation.

        Args:
            user_id: User ID
            token: JWT access token
            limit: Maximum number of photos to return (not yet supported)
            offset: Offset for pagination (not yet supported)
            blur_status: Filter by blur status (not yet supported)

        Returns:
            Dictionary containing:
            - formattedItems: List of photo objects

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        try:
            logger.info(f"Fetching photos for user {user_id}")

            # TODO: Add support for limit, offset, and blur_status in photos-service
            response = await self.get(
                f"/photos/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            return response

        except Exception as e:
            logger.error(f"Failed to fetch user photos: {str(e)}")
            raise AuthorizationError(
                message=f"Failed to fetch user photos: {str(e)}",
                service_name="photos-service",
            )

    async def get_photo(
        self,
        photo_id: str,
        user_id: str,
        token: str,
    ) -> Dict[str, Any]:
        """Get photo metadata by photo ID.

        Args:
            photo_id: Photo ID
            user_id: User ID (for authorization)
            token: JWT access token

        Returns:
            Photo metadata object containing:
            - id: Photo ID
            - user_id: Owner user ID
            - google_photo_id: Google Photos ID
            - filename: File name
            - mime_type: MIME type
            - blur_score: Blur detection score (if analyzed)
            - is_blurred: Boolean indicating if photo is blurred
            - processed_at: Timestamp of analysis

        Raises:
            ResourceNotFoundError: If photo doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        try:
            logger.info(f"Fetching photo metadata {photo_id} for user {user_id}")

            response = await self.get(
                f"/photos/{photo_id}/meta",
                params={"user_id": user_id},
                headers={"Authorization": f"Bearer {token}"},
            )

            return response

        except Exception as e:
            logger.error(f"Failed to fetch photo: {str(e)}")
            if "404" in str(e) or "not found" in str(e).lower():
                raise ResourceNotFoundError(
                    message="Photo not found",
                    resource_type="photo",
                    resource_id=photo_id,
                    service_name="photos-service",
                )
            raise AuthorizationError(
                message=f"Failed to fetch photo: {str(e)}",
                service_name="photos-service",
            )

    async def update_photo(
        self,
        photo_id: str,
        user_id: str,
        token: str,
        update_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update photo metadata.

        Note: photos-service uses PATCH, not PUT.

        Args:
            photo_id: Photo ID
            user_id: User ID (for authorization)
            token: JWT access token
            update_data: Data to update (blur_score, is_blurred, etc.)

        Returns:
            Updated photo object

        Raises:
            ResourceNotFoundError: If photo doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        try:
            logger.info(f"Updating photo {photo_id} for user {user_id}")

            # Use base_client's _request method for PATCH
            response = await self._request(
                "PATCH",
                f"/photos/{photo_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"user_id": user_id},
                json=update_data,
            )

            return response.json()

        except Exception as e:
            logger.error(f"Failed to update photo: {str(e)}")
            if "404" in str(e) or "not found" in str(e).lower():
                raise ResourceNotFoundError(
                    message="Photo not found",
                    resource_type="photo",
                    resource_id=photo_id,
                    service_name="photos-service",
                )
            raise AuthorizationError(
                message=f"Failed to update photo: {str(e)}",
                service_name="photos-service",
            )

    async def create_photo(
        self,
        user_id: str,
        token: str,
        photo_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create new photo metadata entry.

        Note: This endpoint is not yet implemented in photos-service.
        Photos are currently created via the /mediaItems/{user_id} endpoint
        which fetches from Google Photos Picker.
        TODO: Implement POST /photos endpoint in photos-service if direct creation is needed.

        Args:
            user_id: User ID
            token: JWT access token
            photo_data: Photo data (google_photo_id, url, etc.)

        Returns:
            Created photo object

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        try:
            logger.info(f"Creating photo for user {user_id}")

            # TODO: Implement this endpoint in photos-service
            response = await self.post(
                f"/photos",
                headers={"Authorization": f"Bearer {token}"},
                json={**photo_data, "user_id": user_id},
            )

            return response

        except Exception as e:
            logger.error(f"Failed to create photo: {str(e)}")
            raise AuthorizationError(
                message=f"Failed to create photo: {str(e)}",
                service_name="photos-service",
            )

    async def delete_photo(
        self,
        photo_id: str,
        user_id: str,
        token: str,
    ) -> Dict[str, Any]:
        """Delete photo metadata.

        Note: This endpoint is not yet implemented in photos-service.
        TODO: Implement DELETE /photos/{photo_id} endpoint in photos-service.

        Args:
            photo_id: Photo ID
            user_id: User ID (for authorization)
            token: JWT access token

        Returns:
            Success message

        Raises:
            ResourceNotFoundError: If photo doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        try:
            logger.info(f"Deleting photo {photo_id} for user {user_id}")

            # TODO: Implement this endpoint in photos-service
            response = await self.delete(
                f"/photos/{photo_id}",
                params={"user_id": user_id},
                headers={"Authorization": f"Bearer {token}"},
            )

            return response

        except Exception as e:
            logger.error(f"Failed to delete photo: {str(e)}")
            if "404" in str(e) or "not found" in str(e).lower():
                raise ResourceNotFoundError(
                    message="Photo not found",
                    resource_type="photo",
                    resource_id=photo_id,
                    service_name="photos-service",
                )
            raise AuthorizationError(
                message=f"Failed to delete photo: {str(e)}",
                service_name="photos-service",
            )
