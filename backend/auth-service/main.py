from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import sys
import os
import uuid
import secrets
from datetime import datetime, timedelta

from token_manager import TokenManager
from database import get_db, engine
from models import Base, User, OAuthToken
from pydantic import BaseModel, ConfigDict
from typing import Optional
import jwt
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Classify Auth Service", version="1.0.0")
token_manager = TokenManager()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# Pydantic models with UUID handling
class UserCreate(BaseModel):
    google_id: str
    email: str
    name: Optional[str] = None
    profile_picture_url: Optional[str] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    google_id: str
    email: str
    name: Optional[str] = None
    profile_picture_url: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class OAuthInitRequest(BaseModel):
    redirect_uri: Optional[str] = None

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str

class OAuthInitResponse(BaseModel):
    authorization_url: str
    state: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_user_response(user: User) -> UserResponse:
    """Helper function to create UserResponse with proper UUID conversion"""
    return UserResponse(
        id=str(user.id),
        google_id=user.google_id,
        email=user.email,
        name=user.name,
        profile_picture_url=user.profile_picture_url
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth-service"}

@app.post("/register", response_model=Token)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.google_id == user_data.google_id).first()
        if existing_user:
            # User exists, update last login and return token
            existing_user.last_login_at = datetime.utcnow()
            db.commit()

            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": str(existing_user.id)}, expires_delta=access_token_expires
            )

            return Token(
                access_token=access_token,
                token_type="bearer",
                user=create_user_response(existing_user)
            )

        # Create new user
        new_user = User(
            google_id=user_data.google_id,
            email=user_data.email,
            name=user_data.name,
            profile_picture_url=user_data.profile_picture_url,
            last_login_at=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(new_user.id)}, expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=create_user_response(new_user)
        )

    except Exception as e:
        # Log the actual error
        print(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"User registration failed: {str(e)}"
        )

@app.post("/oauth/store-token")
async def store_oauth_token(request: dict, db: Session = Depends(get_db)):
    # Save the OAuth token from NextAuth.js
    try:
        user_id = request.get('user_id')
        access_token = request.get('access_token')
        refresh_token = request.get('refresh_token')
        expires_at = request.get('expires_at')
        scope = request.get('scope')

        # Check existing tokens
        oauth_token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()

        if oauth_token:
            # Update
            oauth_token.access_token = access_token
            oauth_token.refresh_token = refresh_token
            oauth_token.token_expires_at = datetime.fromtimestamp(expires_at)
            oauth_token.scope = scope
            oauth_token.updated_at = datetime.utcnow()
        else:
            # Create
            oauth_token = OAuthToken(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=datetime.fromtimestamp(expires_at),
                scope=scope
            )
            db.add(oauth_token)

        db.commit()
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to store OAuth token: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/verify")
async def verify_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user_id": user_id, "valid": True}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return create_user_response(user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Google OAuth endpoints (placeholders - will implement with google_oauth.py)
@app.post("/oauth/google/init", response_model=OAuthInitResponse)
async def init_google_oauth(request: OAuthInitRequest):
    """Initialize Google OAuth flow - placeholder"""
    state = secrets.token_urlsafe(32)

    # This is a placeholder - would use GoogleOAuthService
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?state={state}&placeholder=true"

    return OAuthInitResponse(
        authorization_url=auth_url,
        state=state
    )

@app.post("/oauth/google/callback", response_model=Token)
async def google_oauth_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback - placeholder"""
    # This is a placeholder - would implement full OAuth flow
    raise HTTPException(
        status_code=501,
        detail="OAuth callback not implemented yet"
    )

@app.get("/tokens/{user_id}")
def get_access_token(user_id: str, db: Session = Depends(get_db)):
    # Returns the valid access token for the specified user.
    try:
        token = token_manager.get_valid_token(user_id, db)
        return {"access_token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get access token: {str(e)}")

@app.post("/oauth/refresh")
async def refresh_oauth_token(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Refresh Google OAuth token - placeholder"""
    oauth_token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
    if not oauth_token:
        raise HTTPException(status_code=404, detail="OAuth token not found")

    # This is a placeholder - would implement token refresh
    return {"message": "Token refresh not implemented yet"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
