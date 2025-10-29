"""Health check endpoints for API Gateway."""

import logging
from fastapi import APIRouter, status
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from schemas.responses import HealthResponse
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic health status of the API Gateway. "
    "This endpoint is lightweight and suitable for liveness probes.",
)
async def health_check():
    """Basic health check endpoint.

    Returns health status without checking external dependencies.
    Use this for Kubernetes liveness probes.

    Returns:
        HealthResponse with status "healthy"
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Returns health status including external dependencies. "
    "Checks Redis connection. Use this for Kubernetes readiness probes.",
)
async def readiness_check():
    """Readiness check endpoint.

    Checks external dependencies like Redis to determine if the service
    is ready to handle requests. Use this for Kubernetes readiness probes.

    Returns:
        HealthResponse with status "healthy", "degraded", or "unhealthy"
    """
    checks = {}
    overall_status = "healthy"

    # Check Redis connection
    try:
        logger.debug("Checking Redis connection")
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        checks["redis"] = "connected"
        await redis_client.close()
        logger.debug("Redis connection successful")
    except RedisError as e:
        logger.error(f"Redis connection failed: {str(e)}")
        checks["redis"] = f"failed: {str(e)}"
        overall_status = "degraded"
    except Exception as e:
        logger.error(f"Unexpected error checking Redis: {str(e)}")
        checks["redis"] = "error"
        overall_status = "degraded"

    # Could add more checks here for other services if needed
    # For example, ping auth-service, photos-service, etc.

    # If Redis is down, consider the service degraded but not unhealthy
    # The service can still handle some requests without Redis

    return HealthResponse(
        status=overall_status,
        service=settings.app_name,
        version=settings.app_version,
        checks=checks,
    )


@router.get(
    "/health/services",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Backend services health check",
    description="Returns health status of all backend services. "
    "This is more comprehensive but slower than /health/ready.",
)
async def services_health_check():
    """Check health of all backend services.

    This endpoint checks connectivity to all backend microservices.
    It's more comprehensive but slower than /health/ready.

    Returns:
        HealthResponse with detailed status of each service
    """
    checks = {}
    overall_status = "healthy"
    failed_services = 0

    # Check Redis
    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        checks["redis"] = "connected"
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis check failed: {str(e)}")
        checks["redis"] = "failed"
        failed_services += 1

    # Check Auth Service
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.auth_service_url}/health")
            if response.status_code == 200:
                checks["auth_service"] = "reachable"
            else:
                checks["auth_service"] = f"unhealthy: {response.status_code}"
                failed_services += 1
    except Exception as e:
        logger.error(f"Auth service check failed: {str(e)}")
        checks["auth_service"] = "unreachable"
        failed_services += 1

    # Check Photos Service
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.photos_service_url}/health")
            if response.status_code == 200:
                checks["photos_service"] = "reachable"
            else:
                checks["photos_service"] = f"unhealthy: {response.status_code}"
                failed_services += 1
    except Exception as e:
        logger.error(f"Photos service check failed: {str(e)}")
        checks["photos_service"] = "unreachable"
        failed_services += 1

    # Check Blur Detection Service
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.blur_detection_service_url}/health"
            )
            if response.status_code == 200:
                checks["blur_detection_service"] = "reachable"
            else:
                checks["blur_detection_service"] = f"unhealthy: {response.status_code}"
                failed_services += 1
    except Exception as e:
        logger.error(f"Blur detection service check failed: {str(e)}")
        checks["blur_detection_service"] = "unreachable"
        failed_services += 1

    # Determine overall status
    total_services = 4  # redis + 3 backend services
    if failed_services == 0:
        overall_status = "healthy"
    elif failed_services < total_services:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        service=settings.app_name,
        version=settings.app_version,
        checks=checks,
    )
