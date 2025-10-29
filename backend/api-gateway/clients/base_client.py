"""Base HTTP client for service-to-service communication."""

import logging
from typing import Any, Dict, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from exceptions import ServiceUnavailableError, ServiceError

logger = logging.getLogger(__name__)


class ServiceClient:
    """Base client for communicating with backend microservices.

    Features:
    - Async HTTP client using httpx
    - Automatic retry with exponential backoff (3 attempts)
    - Configurable timeout (default 30s)
    - Centralized error handling
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize service client.

        Args:
            base_url: Base URL of the service (e.g., http://auth-service:8000)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ServiceClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API endpoint path (e.g., /verify-token)
            headers: Optional HTTP headers
            json: Optional JSON body
            params: Optional query parameters

        Returns:
            HTTP response

        Raises:
            ServiceUnavailableError: If service is unreachable after retries
            ServiceError: For other HTTP errors
        """
        try:
            response = await self.client.request(
                method=method,
                url=path,
                headers=headers,
                json=json,
                params=params,
            )

            # Log retry attempts
            logger.debug(
                f"{method} {self.base_url}{path} - Status: {response.status_code}"
            )

            response.raise_for_status()
            return response

        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling {self.base_url}{path}: {str(e)}")
            raise ServiceUnavailableError(
                f"Service timeout: {self.base_url}",
                service_name=self._get_service_name(),
            )
        except httpx.NetworkError as e:
            logger.error(f"Network error calling {self.base_url}{path}: {str(e)}")
            raise ServiceUnavailableError(
                f"Service unavailable: {self.base_url}",
                service_name=self._get_service_name(),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} calling {self.base_url}{path}: {str(e)}"
            )
            raise ServiceError(
                f"Service error: {e.response.status_code}",
                status_code=e.response.status_code,
                service_name=self._get_service_name(),
            )
        except Exception as e:
            logger.error(f"Unexpected error calling {self.base_url}{path}: {str(e)}")
            raise ServiceError(
                f"Unexpected service error: {str(e)}",
                service_name=self._get_service_name(),
            )

    async def get(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make GET request.

        Args:
            path: API endpoint path
            headers: Optional HTTP headers
            params: Optional query parameters

        Returns:
            JSON response as dictionary
        """
        response = await self._request("GET", path, headers=headers, params=params)
        return response.json()

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make POST request.

        Args:
            path: API endpoint path
            json: JSON body
            headers: Optional HTTP headers

        Returns:
            JSON response as dictionary
        """
        response = await self._request("POST", path, headers=headers, json=json)
        return response.json()

    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make PUT request.

        Args:
            path: API endpoint path
            json: JSON body
            headers: Optional HTTP headers

        Returns:
            JSON response as dictionary
        """
        response = await self._request("PUT", path, headers=headers, json=json)
        return response.json()

    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make DELETE request.

        Args:
            path: API endpoint path
            headers: Optional HTTP headers

        Returns:
            JSON response as dictionary
        """
        response = await self._request("DELETE", path, headers=headers)
        return response.json()

    def _get_service_name(self) -> str:
        """Extract service name from base URL."""
        # Extract service name from URL like http://auth-service:8000
        return self.base_url.split("//")[-1].split(":")[0]

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
