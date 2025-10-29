"""Authentication endpoints for API Gateway."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from clients.auth_client import AuthServiceClient
from middleware.auth import get_current_user
from schemas.auth import (
    TokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    LogoutResponse,
)
from exceptions import AuthenticationError, ServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange OAuth code for tokens",
    description="Exchange Google OAuth authorization code for access and refresh tokens. "
    "This is the first step after user completes Google OAuth flow.",
)
async def exchange_token(request: TokenRequest):
    """Exchange Google OAuth authorization code for tokens.

    Flow:
    1. Frontend initiates Google OAuth and receives authorization code
    2. Frontend sends code to this endpoint
    3. API Gateway forwards code to auth-service
    4. Auth-service exchanges code with Google for tokens
    5. Returns JWT access token and refresh token

    Args:
        request: Token request with Google OAuth code

    Returns:
        TokenResponse with access_token, refresh_token, token_type, expires_in

    Raises:
        HTTPException: 401 if code is invalid or expired
        HTTPException: 503 if auth-service is unavailable
    """
    try:
        logger.info("Processing token exchange request")
        async with AuthServiceClient() as auth_client:
            token_data = await auth_client.exchange_code_for_token(request.code)

        logger.info("Token exchange successful")
        return TokenResponse(**token_data)

    except AuthenticationError as e:
        logger.error(f"Token exchange failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    except ServiceError as e:
        logger.error(f"Service error during token exchange: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"Unexpected error during token exchange: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange authorization code",
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Use refresh token to obtain a new access token. "
    "Call this when access token expires (typically after 1 hour).",
)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token.

    When the access token expires, use this endpoint to get a new one
    without requiring the user to re-authenticate with Google.

    Args:
        request: Refresh token request

    Returns:
        TokenResponse with new access_token and potentially new refresh_token

    Raises:
        HTTPException: 401 if refresh token is invalid or expired
        HTTPException: 503 if auth-service is unavailable
    """
    try:
        logger.info("Processing token refresh request")
        async with AuthServiceClient() as auth_client:
            token_data = await auth_client.refresh_token(request.refresh_token)

        logger.info("Token refresh successful")
        return TokenResponse(**token_data)

    except AuthenticationError as e:
        logger.error(f"Token refresh failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    except ServiceError as e:
        logger.error(f"Service error during token refresh: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the currently authenticated user. "
    "Requires valid access token in Authorization header.",
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information.

    This endpoint verifies the access token and returns user details.
    Use this to get user info after authentication or to verify token validity.

    Headers:
        Authorization: Bearer {access_token}

    Args:
        current_user: User info from authentication middleware

    Returns:
        UserResponse with user details

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    try:
        logger.info(f"Getting user info for user_id: {current_user.get('user_id')}")

        # The current_user dict from get_current_user middleware needs to be
        # mapped to UserResponse format. We need to get full user details
        # from auth-service if necessary.
        user_id = current_user.get("user_id")
        token = current_user.get("token")

        if not user_id or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication data",
            )

        async with AuthServiceClient() as auth_client:
            user_data = await auth_client.get_user_by_id(user_id, token)

        logger.info(f"User info retrieved for user_id: {user_id}")
        return UserResponse(**user_data)

    except AuthenticationError as e:
        logger.error(f"Failed to get user info: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    except ServiceError as e:
        logger.error(f"Service error getting user info: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information",
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Logout the current user. Since JWT tokens are stateless, "
    "the client should discard the tokens after calling this endpoint.",
)
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout the current user.

    Note: JWT tokens are stateless, so server-side logout is limited.
    The primary responsibility is on the client to discard tokens.

    This endpoint can be used for:
    - Logging logout events
    - Invalidating refresh tokens (if implemented)
    - Analytics and audit trails

    Headers:
        Authorization: Bearer {access_token}

    Args:
        current_user: User info from authentication middleware

    Returns:
        LogoutResponse with success message

    Raises:
        HTTPException: 401 if token is invalid
    """
    try:
        user_id = current_user.get("user_id")
        logger.info(f"User logout: {user_id}")

        # In a more advanced implementation, you could:
        # 1. Invalidate refresh token in auth-service
        # 2. Add access token to a blacklist (requires Redis)
        # 3. Log the logout event for analytics

        # For now, we just acknowledge the logout
        # The client should discard the tokens

        return LogoutResponse(
            success=True,
            message="Logged out successfully. Please discard your tokens.",
        )

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        # Even if logging fails, we return success since logout is client-side
        return LogoutResponse(
            success=True,
            message="Logged out successfully. Please discard your tokens.",
        )
