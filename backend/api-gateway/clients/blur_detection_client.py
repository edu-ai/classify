"""Blur detection service client for blur analysis."""

from typing import Dict, Any, Optional
import logging

from clients.base_client import ServiceClient
from exceptions import ResourceNotFoundError, ServiceError
from config import settings

logger = logging.getLogger(__name__)


class BlurDetectionServiceClient(ServiceClient):
    """Client for communicating with blur-detection-service.

    Handles:
    - Submitting photos for blur analysis
    - Checking job status
    - Getting analysis results
    """

    def __init__(self):
        """Initialize blur detection service client."""
        super().__init__(
            base_url=settings.blur_detection_service_url,
            timeout=settings.service_timeout,
            max_retries=settings.service_max_retries,
        )

    async def analyze_photo(
        self,
        photo_id: str,
        photo_url: str,
        user_id: str,
        token: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit photo for blur analysis.

        This will perform synchronous blur analysis.
        Note: photo_url parameter is kept for API compatibility but not used.
        The service fetches photos directly from photos-service.

        Args:
            photo_id: Photo ID
            photo_url: URL to download photo from (not used, kept for compatibility)
            user_id: User ID (for authorization)
            token: JWT access token
            options: Analysis options (e.g., {"use_face_detection": true})

        Returns:
            Dictionary containing blur analysis result:
            - photo_id: Photo ID
            - google_photo_id: Google Photos ID
            - filename: File name
            - blur_score: Blur score
            - is_blurred: Boolean indicating if blurred
            - processed_at: Processing timestamp
            - processing_time_ms: Processing time in milliseconds

        Raises:
            ServiceError: If analysis submission fails
        """
        try:
            logger.info(f"Submitting photo {photo_id} for blur analysis")

            # Extract options for query parameters
            params = {"user_id": user_id}
            if options:
                # Add optional parameters if provided
                if "threshold" in options:
                    params["threshold"] = options["threshold"]
                if "method" in options:
                    params["method"] = options["method"]
                if "use_face_detection" in options:
                    params["use_face_detection"] = options["use_face_detection"]

            response = await self.post(
                f"/analyze/{photo_id}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )

            return response

        except Exception as e:
            logger.error(f"Failed to submit photo for analysis: {str(e)}")
            raise ServiceError(
                message=f"Failed to submit photo for analysis: {str(e)}",
                service_name="blur-detection-service",
            )

    async def get_job_status(
        self,
        job_id: str,
        token: str,
    ) -> Dict[str, Any]:
        """Get blur analysis job status.

        Note: This endpoint is not yet implemented in blur-detection-service.
        The current blur-detection-service performs synchronous analysis without
        job tracking. For async job tracking with Redis Queue, this needs to be
        implemented in blur-detection-service.

        TODO: Implement job status tracking in blur-detection-service:
        - Store job metadata in Redis
        - GET /jobs/{job_id} endpoint
        - Return job status, progress, and results

        Args:
            job_id: Job ID
            token: JWT access token

        Returns:
            Dictionary containing:
            - job_id: Job ID
            - status: Job status (queued, processing, completed, failed)
            - result: Analysis result (if completed)
            - error: Error message (if failed)
            - created_at: Job creation timestamp
            - updated_at: Job last update timestamp

        Raises:
            NotImplementedError: This endpoint is not yet implemented
        """
        logger.warning(f"Job status tracking not implemented for job {job_id}")
        raise NotImplementedError(
            "Job status tracking is not yet implemented in blur-detection-service. "
            "The service currently performs synchronous analysis. "
            "For async processing, check the photo metadata via photos-service."
        )

    async def get_analysis_result(
        self,
        photo_id: str,
        user_id: str,
        token: str,
    ) -> Dict[str, Any]:
        """Get blur analysis result for a photo.

        Note: This retrieves results from photos-service, not blur-detection-service.
        The blur analysis results are stored in the photo metadata after processing.

        Args:
            photo_id: Photo ID
            user_id: User ID (for authorization)
            token: JWT access token

        Returns:
            Dictionary containing:
            - photo_id: Photo ID
            - blur_score: Blur score (lower = more blurred)
            - is_blurred: Boolean indicating if photo is blurred
            - processed_at: Analysis timestamp

        Raises:
            ResourceNotFoundError: If analysis result doesn't exist
        """
        try:
            logger.info(f"Fetching analysis result for photo {photo_id}")

            # Import photos client to avoid circular dependency
            from clients.photos_client import PhotosServiceClient

            async with PhotosServiceClient() as photos_client:
                photo_data = await photos_client.get_photo(
                    photo_id=photo_id,
                    user_id=user_id,
                    token=token,
                )

            # Extract blur analysis data from photo metadata
            if photo_data.get("blur_score") is None:
                raise ResourceNotFoundError(
                    message="Analysis result not found (photo not analyzed yet)",
                    resource_type="analysis_result",
                    resource_id=photo_id,
                    service_name="photos-service",
                )

            return {
                "photo_id": photo_data.get("id"),
                "blur_score": photo_data.get("blur_score"),
                "is_blurred": photo_data.get("is_blurred"),
                "processed_at": photo_data.get("processed_at"),
            }

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get analysis result: {str(e)}")
            raise ServiceError(
                message=f"Failed to get analysis result: {str(e)}",
                service_name="photos-service",
            )

    async def batch_analyze(
        self,
        photo_ids: list[str],
        user_id: str,
        token: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit multiple photos for blur analysis.

        This enqueues jobs to Redis Queue for async processing by blur-worker.

        Args:
            photo_ids: List of photo IDs (as UUIDs)
            user_id: User ID (for authorization, as UUID)
            token: JWT access token
            options: Analysis options:
                - threshold: float (default 0.30)
                - method: str (default "hybrid")
                - use_face_detection: bool (default True)

        Returns:
            Dictionary containing:
            - status: Status message (e.g., "queued")
            - count: Number of photos queued

        Raises:
            ServiceError: If batch submission fails
        """
        try:
            logger.info(f"Submitting batch of {len(photo_ids)} photos for analysis")

            # Build request payload according to blur-detection-service's BatchRequest schema
            payload = {
                "user_id": user_id,
                "photo_ids": photo_ids,
            }

            # Add optional parameters
            if options:
                if "threshold" in options:
                    payload["threshold"] = options["threshold"]
                if "method" in options:
                    payload["method"] = options["method"]
                if "use_face_detection" in options:
                    payload["use_face_detection"] = options["use_face_detection"]

            response = await self.post(
                "/analyze/batch",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )

            return response

        except Exception as e:
            logger.error(f"Failed to submit batch analysis: {str(e)}")
            raise ServiceError(
                message=f"Failed to submit batch analysis: {str(e)}",
                service_name="blur-detection-service",
            )

    async def tag_photo(
        self,
        photo_id: str,
        user_id: str,
        token: str,
    ) -> Dict[str, Any]:
        """Generate AI tags for a photo using OpenAI API.

        This will analyze the photo and generate descriptive tags using
        OpenAI's vision model (gpt-4o-mini).

        Args:
            photo_id: Photo ID
            user_id: User ID (for authorization)
            token: JWT access token

        Returns:
            Dictionary containing:
            - photo_id: Photo ID
            - tag: Generated tag string
            - tagged_at: Tagging timestamp

        Raises:
            ServiceError: If tagging fails
        """
        try:
            logger.info(f"Requesting AI tags for photo {photo_id}")

            response = await self.post(
                f"/tag/{photo_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"user_id": user_id},
            )

            return response

        except Exception as e:
            logger.error(f"Failed to generate tags for photo: {str(e)}")
            raise ServiceError(
                message=f"Failed to generate tags for photo: {str(e)}",
                service_name="blur-detection-service",
            )
