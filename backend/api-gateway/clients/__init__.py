"""Service clients for inter-service communication."""

from clients.base_client import ServiceClient
from clients.auth_client import AuthServiceClient
from clients.photos_client import PhotosServiceClient
from clients.blur_detection_client import BlurDetectionServiceClient

__all__ = [
    "ServiceClient",
    "AuthServiceClient",
    "PhotosServiceClient",
    "BlurDetectionServiceClient",
]
