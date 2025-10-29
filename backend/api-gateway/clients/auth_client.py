"""Auth service client for authentication and token management."""

from typing import Dict, Any, Optional
import logging

from clients.base_client import ServiceClient
from exceptions import AuthenticationError, AuthorizationError
from config import settings

logger = logging.getLogger(__name__)


class AuthServiceClient(ServiceClient):
    """Client for communicating with auth-service.

    Handles:
    - Token verification
    - Token refresh
    - User authentication
    """

    def __init__(self):
        """Initialize auth service client."""
        super().__init__(
            base_url=settings.auth_service_url,
            timeout=settings.service_timeout,
            max_retries=settings.service_max_retries,
        )

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange Google OAuth authorization code for tokens.

        Args:
            code: Google OAuth authorization code

        Returns:
            Dictionary containing:
            - access_token: JWT access token
            - refresh_token: Refresh token
            - token_type: Token type (bearer)
            - expires_in: Token expiration time in seconds

        Raises:
            AuthenticationError: If code exchange fails
        """
        try:
            logger.info("Exchanging OAuth code for tokens")
            response = await self.post(
                "/oauth/google/callback",
                json={"code": code},
            )

            if not response.get("access_token"):
                raise AuthenticationError(
                    message="Failed to exchange authorization code",
                    service_name="auth-service",
                )

            return response

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Code exchange failed: {str(e)}")
            raise AuthenticationError(
                message="Failed to exchange authorization code",
                service_name="auth-service",
                details={"error": str(e)},
            )

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user information.

        Args:
            token: JWT access token

        Returns:
            User information dictionary containing:
            - user_id: User ID
            - valid: Token validity

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            logger.info("Verifying token with auth-service")
            response = await self.get(
                "/verify",
                headers={"Authorization": f"Bearer {token}"},
            )

            if not response.get("valid"):
                raise AuthenticationError(
                    message="Invalid or expired token",
                    service_name="auth-service",
                )

            return response

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise AuthenticationError(
                message="Token verification failed",
                service_name="auth-service",
                details={"error": str(e)},
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary containing:
            - access_token: New access token
            - refresh_token: New refresh token (optional)
            - expires_in: Token expiration time in seconds

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            logger.info("Refreshing token with auth-service")
            response = await self.post(
                "/oauth/refresh",
                json={"refresh_token": refresh_token},
            )

            if not response.get("access_token"):
                raise AuthenticationError(
                    message="Failed to refresh token",
                    service_name="auth-service",
                )

            return {
                "access_token": response["access_token"],
                "refresh_token": response.get("refresh_token", refresh_token),
                "expires_in": response.get("expires_in", 3600),
            }

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError(
                message="Token refresh failed",
                service_name="auth-service",
                details={"error": str(e)},
            )

    async def get_user_by_id(self, user_id: str, token: str) -> Dict[str, Any]:
        """Get user information by user ID.

        Note: This now uses the /me endpoint which gets user info from the token.
        The user_id parameter is kept for API compatibility but not used.

        Args:
            user_id: User ID (kept for compatibility, not used)
            token: JWT access token

        Returns:
            User information dictionary

        Raises:
            AuthenticationError: If token is invalid
            AuthorizationError: If user doesn't have permission
        """
        try:
            logger.info(f"Fetching user info from auth-service")
            response = await self.get(
                "/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            return response

        except Exception as e:
            logger.error(f"Failed to fetch user: {str(e)}")
            raise AuthenticationError(
                message=f"Failed to fetch user: {str(e)}",
                service_name="auth-service",
            )

    async def validate_oauth_token(
        self, user_id: str, token: str
    ) -> Dict[str, Any]:
        """Validate OAuth token for Google Photos access.

        Note: This endpoint is not yet implemented in auth-service.
        TODO: Implement /oauth/validate/{user_id} in auth-service.

        Args:
            user_id: User ID
            token: JWT access token

        Returns:
            OAuth token validation result

        Raises:
            AuthenticationError: If OAuth token is invalid or expired
        """
        try:
            logger.info(f"Validating OAuth token for user {user_id}")
            # TODO: Update endpoint when implemented in auth-service
            response = await self.get(
                f"/oauth/validate/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if not response.get("valid"):
                raise AuthenticationError(
                    message="OAuth token is invalid or expired",
                    service_name="auth-service",
                    details={"requires_reauth": True},
                )

            return response

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"OAuth token validation failed: {str(e)}")
            raise AuthenticationError(
                message="OAuth token validation failed",
                service_name="auth-service",
                details={"error": str(e)},
            )
