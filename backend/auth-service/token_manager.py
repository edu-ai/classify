from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from models import OAuthToken
import os
import logging
import requests

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class TokenManager:
    def __init__(self):
        self.google_token_url = "https://oauth2.googleapis.com/token"

    def get_valid_token(self, user_id: str, db: Session) -> str:
        # Retrieve the access token from the database and refresh it if expired.
        oauth_token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
        if not oauth_token:
            raise Exception(f"OAuth token not found for user {user_id}")

        # Token Expiration Check
        if not oauth_token.access_token or oauth_token.token_expires_at <= datetime.now(timezone.utc):
            return self.refresh_access_token(oauth_token, db)

        return oauth_token.access_token

    def refresh_access_token(self, oauth_token: OAuthToken, db: Session) -> str:
        # Refresh Token for Access Token Renewal
        try:
            if oauth_token.refresh_token:
                # Refresh Using Google Credentials
                creds = Credentials(
                    token=None,
                    refresh_token=oauth_token.refresh_token,
                    token_uri=self.google_token_url,
                    client_id=os.getenv("GOOGLE_CLIENT_ID"),
                    client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
                )
                creds.refresh(Request())

                oauth_token.access_token = creds.token
                # Convert expiration date to timezone-aware format
                oauth_token.token_expires_at = creds.expiry.replace(tzinfo=timezone.utc)
                oauth_token.updated_at = datetime.now(timezone.utc)

                db.commit()
                logger.info(f"Refreshed access token for user {oauth_token.user_id}")
                return creds.token
            else:
                raise Exception("No refresh token available")

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise e
