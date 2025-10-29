"""Blur detection endpoints for API Gateway."""

import logging
from fastapi import APIRouter, Depends, Path, HTTPException, status, Body
from typing import Optional

from clients.blur_detection_client import BlurDetectionServiceClient
from clients.photos_client import PhotosServiceClient
from middleware.auth import get_current_user
from schemas.blur import (
    BlurAnalysisJobResponse,
    BlurAnalysisResultResponse,
    AnalyzePhotoRequest,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    JobStatus,
)
from exceptions import ResourceNotFoundError, AuthorizationError, ServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Blur Detection"])


@router.post(
    "/photos/{photo_id}/analyze",
    response_model=BlurAnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start blur analysis",
    description="Submit a photo for blur detection analysis. "
    "The analysis is performed asynchronously by a background worker. "
    "Use the returned job_id to check the status.",
)
async def analyze_photo(
    photo_id: str = Path(..., description="Photo ID to analyze"),
    request: AnalyzePhotoRequest = Body(default=AnalyzePhotoRequest()),
    current_user: dict = Depends(get_current_user),
):
    """Start blur analysis for a photo.

    Flow:
    1. Verify photo exists and user owns it
    2. Submit analysis job to blur-detection-service
    3. Job is queued in Redis for background worker
    4. Worker processes the photo and stores results in photos-service
    5. Return job_id for status tracking

    Headers:
        Authorization: Bearer {access_token}

    Args:
        photo_id: Unique photo identifier
        request: Analysis options (e.g., use_face_detection)
        current_user: User info from authentication middleware

    Returns:
        BlurAnalysisJobResponse with job_id and status

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if photo not found or user doesn't own it
        HTTPException: 503 if blur-detection-service is unavailable
    """
    try:
        user_id = current_user.get("user_id")
        token = current_user.get("token")

        if not user_id or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication data",
            )

        logger.info(f"Starting blur analysis for photo {photo_id}")

        # Verify photo exists and user owns it
        async with PhotosServiceClient() as photos_client:
            photo_data = await photos_client.get_photo(
                photo_id=photo_id,
                user_id=user_id,
                token=token,
            )

        # Verify ownership
        if photo_data.get("user_id") != user_id:
            logger.warning(f"User {user_id} attempted to analyze photo {photo_id} owned by {photo_data.get('user_id')}")
            raise ResourceNotFoundError(
                message="Photo not found",
                resource_type="photo",
                resource_id=photo_id,
            )

        # Construct photo URL from Google Photos ID or stored URL
        # Note: This may need to be adjusted based on actual photo storage
        photo_url = photo_data.get("url") or f"https://photoslibrary.googleapis.com/v1/mediaItems/{photo_data.get('google_photo_id')}"

        # Submit blur analysis job
        options = {}
        if request.use_face_detection:
            options["use_face_detection"] = True

        async with BlurDetectionServiceClient() as blur_client:
            job_data = await blur_client.analyze_photo(
                photo_id=photo_id,
                photo_url=photo_url,
                user_id=user_id,
                token=token,
                options=options if options else None,
            )

        logger.info(f"Blur analysis job created: {job_data.get('job_id')}")

        return BlurAnalysisJobResponse(
            job_id=job_data.get("job_id"),
            photo_id=photo_id,
            status=JobStatus.PENDING,
            created_at=job_data.get("created_at"),
            completed_at=None,
            error=None,
        )

    except ResourceNotFoundError as e:
        logger.error(f"Photo not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except (AuthorizationError, ServiceError) as e:
        logger.error(f"Error starting blur analysis: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error starting blur analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start blur analysis",
        )


@router.get(
    "/blur/jobs/{job_id}",
    response_model=BlurAnalysisJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job status",
    description="Get the status of a blur analysis job. "
    "Use this to check if analysis is complete.",
)
async def get_job_status(
    job_id: str = Path(..., description="Job ID (currently treated as photo_id)"),
    current_user: dict = Depends(get_current_user),
):
    """Get blur analysis job status.

    TEMPORARY IMPLEMENTATION:
    Since blur-detection-service does not yet implement job status tracking,
    this endpoint treats job_id as photo_id and checks the photo metadata
    to determine the analysis status.

    TODO: Implement proper job status tracking in blur-detection-service with:
    - Redis-based job metadata storage
    - GET /jobs/{job_id} endpoint
    - Real-time status updates (queued, processing, completed, failed)

    Check the progress of an analysis job. Possible statuses:
    - pending: Photo not analyzed yet (blur_score is null)
    - completed: Analysis finished successfully (processed_at exists)
    - failed: Analysis failed (currently not tracked)

    Headers:
        Authorization: Bearer {access_token}

    Args:
        job_id: Unique job identifier (currently treated as photo_id)
        current_user: User info from authentication middleware

    Returns:
        BlurAnalysisJobResponse with current status

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if photo not found
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

        logger.info(f"Checking status of job {job_id} (treating as photo_id)")

        # Temporary implementation: treat job_id as photo_id
        # and check photo metadata for analysis status
        async with PhotosServiceClient() as photos_client:
            photo_data = await photos_client.get_photo(
                photo_id=job_id,
                user_id=user_id,
                token=token,
            )

        # Verify ownership
        if photo_data.get("user_id") != user_id:
            logger.warning(f"User {user_id} attempted to check status for photo {job_id} owned by {photo_data.get('user_id')}")
            raise ResourceNotFoundError(
                message="Job not found",
                resource_type="job",
                resource_id=job_id,
            )

        # Determine status based on photo metadata
        blur_score = photo_data.get("blur_score")
        processed_at = photo_data.get("processed_at")

        if processed_at or blur_score is not None:
            job_status = JobStatus.COMPLETED
            completed_at = processed_at
        else:
            job_status = JobStatus.PENDING
            completed_at = None

        logger.info(f"Job {job_id} status: {job_status}")

        return BlurAnalysisJobResponse(
            job_id=job_id,
            photo_id=job_id,  # Since job_id is treated as photo_id
            status=job_status,
            created_at=photo_data.get("google_created_time"),  # Use photo creation time as fallback
            completed_at=completed_at,
            error=None,
        )

    except ResourceNotFoundError as e:
        logger.error(f"Job/Photo not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except (AuthorizationError, ServiceError) as e:
        logger.error(f"Error getting job status: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status",
        )


@router.get(
    "/photos/{photo_id}/result",
    response_model=Optional[BlurAnalysisResultResponse],
    status_code=status.HTTP_200_OK,
    summary="Get analysis result",
    description="Get the blur analysis result for a photo. "
    "Returns null if photo hasn't been analyzed yet.",
)
async def get_analysis_result(
    photo_id: str = Path(..., description="Photo ID"),
    current_user: dict = Depends(get_current_user),
):
    """Get blur analysis result for a photo.

    After analysis is complete, the results are stored in the photo metadata.
    This endpoint retrieves those results.

    Returns null if the photo hasn't been analyzed yet.

    Headers:
        Authorization: Bearer {access_token}

    Args:
        photo_id: Unique photo identifier
        current_user: User info from authentication middleware

    Returns:
        BlurAnalysisResultResponse with analysis results, or null if not analyzed

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

        logger.info(f"Fetching analysis result for photo {photo_id}")

        # Get photo data with analysis results
        async with PhotosServiceClient() as photos_client:
            photo_data = await photos_client.get_photo(
                photo_id=photo_id,
                user_id=user_id,
                token=token,
            )

        # Verify ownership
        if photo_data.get("user_id") != user_id:
            logger.warning(f"User {user_id} attempted to access result for photo {photo_id} owned by {photo_data.get('user_id')}")
            raise ResourceNotFoundError(
                message="Photo not found",
                resource_type="photo",
                resource_id=photo_id,
            )

        # Check if analysis result exists
        if photo_data.get("blur_score") is None:
            logger.info(f"Photo {photo_id} has not been analyzed yet")
            return None

        logger.info(f"Analysis result found for photo {photo_id}")

        return BlurAnalysisResultResponse(
            photo_id=photo_id,
            blur_score=photo_data.get("blur_score"),
            is_blurred=photo_data.get("is_blurred"),
            analysis_method=photo_data.get("analysis_method", "opencv"),
            processed_at=photo_data.get("processed_at"),
        )

    except ResourceNotFoundError as e:
        logger.error(f"Photo not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except (AuthorizationError, ServiceError) as e:
        logger.error(f"Error getting analysis result: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting analysis result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysis result",
        )


@router.post(
    "/blur/analyze-batch",
    response_model=BatchAnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch blur analysis",
    description="Submit multiple photos for blur analysis at once. "
    "Efficiently process large numbers of photos.",
)
async def analyze_batch(
    request: BatchAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit multiple photos for batch blur analysis.

    This endpoint allows you to analyze multiple photos in one request.
    Each photo gets its own job, which can be tracked individually.

    Use this for bulk processing of photo libraries.

    Headers:
        Authorization: Bearer {access_token}

    Args:
        request: Batch analysis request with photo IDs
        current_user: User info from authentication middleware

    Returns:
        BatchAnalyzeResponse with list of created jobs

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 422 if photo_ids list is invalid
        HTTPException: 503 if blur-detection-service is unavailable
    """
    try:
        user_id = current_user.get("user_id")
        token = current_user.get("token")

        if not user_id or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication data",
            )

        logger.info(f"Starting batch blur analysis for {len(request.photo_ids)} photos")

        # Submit batch analysis
        async with BlurDetectionServiceClient() as blur_client:
            batch_data = await blur_client.batch_analyze(
                photo_ids=request.photo_ids,
                user_id=user_id,
                token=token,
            )

        # Parse response - could be a list of jobs or a batch object
        jobs_list = batch_data.get("jobs") or batch_data.get("job_ids", [])

        jobs = []
        for job in jobs_list:
            # Handle different response formats
            if isinstance(job, dict):
                jobs.append(
                    BlurAnalysisJobResponse(
                        job_id=job.get("job_id"),
                        photo_id=job.get("photo_id"),
                        status=JobStatus.PENDING,
                        created_at=job.get("created_at"),
                        completed_at=None,
                        error=None,
                    )
                )
            else:
                # If just job IDs are returned
                jobs.append(
                    BlurAnalysisJobResponse(
                        job_id=str(job),
                        photo_id="",  # Will be populated by worker
                        status=JobStatus.PENDING,
                        created_at=batch_data.get("created_at"),
                        completed_at=None,
                        error=None,
                    )
                )

        logger.info(f"Batch analysis created {len(jobs)} jobs")

        return BatchAnalyzeResponse(
            jobs=jobs,
            total=len(jobs),
        )

    except (ServiceError,) as e:
        logger.error(f"Error starting batch analysis: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error starting batch analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start batch analysis",
        )
