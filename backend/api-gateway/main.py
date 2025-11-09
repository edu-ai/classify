import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from exceptions import ServiceError
from routes import health, auth, photos, blur, public_proxy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Classify API Gateway",
    version=settings.app_version,
    description="RESTful API Gateway for Classify photo blur detection service",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    """Handle all ServiceError exceptions with consistent format."""
    logger.error(
        f"Service error: {exc.message} (status: {exc.status_code}, service: {exc.service_name})"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "status_code": 500,
        },
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router)
app.include_router(photos.router)
app.include_router(blur.router)
app.include_router(public_proxy.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Classify API Gateway",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
        "health_endpoints": {
            "basic": "/health",
            "ready": "/health/ready",
            "services": "/health/services",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint for ALB"""
    return {
        "status": "healthy",
        "service": "Classify API Gateway",
        "version": settings.app_version,
        "checks": None
    }


@app.get("/api/health")
async def health_api():
    """Health check endpoint with /api prefix"""
    return {
        "status": "healthy",
        "service": "Classify API Gateway",
        "version": settings.app_version,
        "checks": None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
