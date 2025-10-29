"""Authentication middleware for API Gateway."""

from typing import Dict, Any, Optional
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from clients.auth_client import AuthServiceClient
from exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify JWT token and return the token string.

    This is a lightweight dependency that only extracts and validates
    the token format. Use get_current_user() for full user information.

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        JWT token string

    Raises:
        HTTPException: If token is missing or invalid format
    """
    if not credentials or not credentials.credentials:
        logger.warning("Missing authentication credentials in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Basic token format validation
    if not token or len(token) < 10:
        logger.warning(f"Invalid token format (length: {len(token) if token else 0})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"Token extracted successfully (length: {len(token)})")
    return token


async def get_current_user(
    token: str = Depends(verify_token),
) -> Dict[str, Any]:
    """Get current authenticated user information.

    This dependency verifies the token with auth-service and returns
    the user information. Use this in endpoints that need user data.

    Note: auth-service's /verify endpoint returns {"user_id": str, "valid": bool}.
    For full user details (email, name), use /me endpoint separately.

    Args:
        token: JWT token from verify_token dependency

    Returns:
        User information dictionary containing:
        - user_id: User ID
        - valid: Token validity (always True if no exception)
        - token: Original JWT token (added for convenience)

    Raises:
        HTTPException: If token verification fails

    Example:
        ```python
        @app.get("/me")
        async def get_me(user: Dict = Depends(get_current_user)):
            return {"user": user}
        ```
    """
    try:
        logger.debug(f"Verifying token with auth-service (token length: {len(token)})")

        async with AuthServiceClient() as auth_client:
            # Call verify_token which uses GET /verify endpoint
            user_info = await auth_client.verify_token(token)

            logger.debug(f"Auth service response: {user_info}")

            # Validate response from auth-service
            if not user_info:
                logger.error("Empty response from auth service")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication response",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user_info.get("user_id"):
                logger.error(f"Missing user_id in auth service response: {user_info}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication data",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user_info.get("valid"):
                logger.warning(f"Token marked as invalid by auth service for user: {user_info.get('user_id')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is not valid",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Add token to user info for downstream service calls
            user_info["token"] = token

            logger.info(f"User authenticated successfully: user_id={user_info.get('user_id')}")
            return user_info

    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None.

    This is useful for endpoints that can work with or without authentication,
    but may provide additional features when authenticated.

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        User information dictionary if authenticated, None otherwise

    Example:
        ```python
        @app.get("/photos/public")
        async def get_public_photos(user: Optional[Dict] = Depends(get_optional_user)):
            if user:
                # Show user's photos
                pass
            else:
                # Show public photos only
                pass
        ```
    """
    if not credentials or not credentials.credentials:
        logger.debug("No credentials provided for optional authentication")
        return None

    try:
        token = credentials.credentials
        logger.debug(f"Attempting optional authentication (token length: {len(token)})")

        async with AuthServiceClient() as auth_client:
            user_info = await auth_client.verify_token(token)

            if not user_info or not user_info.get("user_id") or not user_info.get("valid"):
                logger.debug("Optional authentication failed: invalid response")
                return None

            user_info["token"] = token
            logger.debug(f"Optional authentication successful: user_id={user_info.get('user_id')}")
            return user_info

    except Exception as e:
        logger.debug(f"Optional authentication failed: {str(e)}")
        return None


def require_user_id(user_id: str):
    """Dependency factory to verify that the authenticated user matches a specific user_id.

    This is useful for endpoints that require the user to access their own resources.

    Args:
        user_id: The user_id from the request path/query

    Returns:
        Dependency function that validates user ownership

    Raises:
        HTTPException: If user doesn't match

    Example:
        ```python
        @app.get("/users/{user_id}/photos")
        async def get_user_photos(
            user_id: str,
            user: Dict = Depends(get_current_user),
            _: None = Depends(require_user_id(user_id))
        ):
            # user is guaranteed to be the owner
            pass
        ```
    """

    async def check_user_id(user: Dict[str, Any] = Depends(get_current_user)):
        if user.get("user_id") != user_id:
            logger.warning(
                f"User {user.get('user_id')} attempted to access resources of user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource",
            )
        return None

    return check_user_id
