from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Base, Photo
import os
import requests

app = FastAPI(title="Classify Photos Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PICKER_API_URL = "https://photospicker.googleapis.com/v1"
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
PHOTOS_SERVICE_URL = "http://localhost:8002"

def get_access_token_from_auth_service(user_id: str) -> str:
    try:
        print(f"{AUTH_SERVICE_URL}/tokens/{user_id}")
        res = requests.get(f"{AUTH_SERVICE_URL}/tokens/{user_id}")
        res.raise_for_status()
        data = res.json()
        return data["access_token"]
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to get access token from Auth Service: {e}")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "photos-service"}

@app.get("/sessions/{user_id}")
def create_picker_session(user_id: str, db: Session = Depends(get_db)):
    try:
        access_token = get_access_token_from_auth_service(user_id)
        url = f"{PICKER_API_URL}/sessions"
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.post(url, headers=headers)
        r.raise_for_status()
        return {
            "session": {
                "id": r.json().get("id"),
                "pickerUri": r.json().get("pickerUri"),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create picker session: {str(e)}")

@app.get("/mediaItems/{user_id}")
def fetch_media_items(user_id: str, session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    try:
        access_token = get_access_token_from_auth_service(user_id)
        url = f"{PICKER_API_URL}/mediaItems?sessionId={session_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            return False

        mediaItems = r.json().get("mediaItems", [])

        for item in mediaItems:
            photo = db.query(Photo).filter(Photo.google_photo_id == item["id"]).first()
            if photo:
                photo.base_url = item["mediaFile"]["baseUrl"]
            else:
                photo = Photo(
                    user_id=user_id,
                    google_photo_id=item["id"],
                    filename=item["mediaFile"]["filename"],
                    media_type=item.get("type", "IMAGE"),
                    base_url=f'{item["mediaFile"]["baseUrl"]}=w200-h200',
                    mime_type=item["mediaFile"]["mimeType"],
                    width=item["mediaFile"].get("mediaFileMetadata", {}).get("width"),
                    height=item["mediaFile"].get("mediaFileMetadata", {}).get("height"),
                    file_size=item["mediaFile"].get("mediaFileMetadata", {}).get("fileSize"),
                    google_created_time=item.get("createTime")
                )
                db.add(photo)

        db.commit()
        return True
    except Exception as e:
        print(f"Error in fetch_media_items: {e}")
        db.rollback()
        return False

@app.get("/photos/{user_id}")
def get_media_items(user_id: str, db: Session = Depends(get_db)):
    try:
        photos = db.query(Photo).filter(Photo.user_id == user_id).all()
        if not photos:
            return {"formattedItems": []}

        formattedItems = [
            {
                "id": photo.id,
                "filename": photo.filename,
                "proxyUrl": f"{PHOTOS_SERVICE_URL}/photo/{photo.google_photo_id}?user_id={user_id}",
                "google_created_time": photo.google_created_time,
                "blur_score": photo.blur_score,
                "is_blurred": photo.is_blurred,
            }
            for photo in photos
        ]

        return {"formattedItems": formattedItems}
    except Exception as e:
        print(f"Error fetching media items for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch media items")

@app.get("/photo/{photo_id}")
def get_photo(photo_id: str, user_id: str, db: Session = Depends(get_db)):
    access_token = get_access_token_from_auth_service(user_id)
    photo = db.query(Photo).filter(Photo.google_photo_id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    url = f"{photo.base_url}=w200-h200"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, stream=True)

    if r.status_code == 403 or r.status_code == 404:
        return {"status": "expired", "message": "Photo URL expired, please pick photos again"}

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return StreamingResponse(
        r.iter_content(chunk_size=8192),
        media_type=photo.mime_type or "image/jpeg"
    )

@app.get("/photos/{photo_id}/meta")
def get_photo_meta(photo_id: str, user_id: str, db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == user_id
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return {
        "id": str(photo.id),
        "user_id": str(photo.user_id),
        "google_photo_id": photo.google_photo_id,
        "filename": photo.filename,
        "mime_type": photo.mime_type,
        "blur_score": photo.blur_score,
        "is_blurred": photo.is_blurred,
        "processed_at": photo.processed_at,
    }

@app.patch("/photos/{photo_id}")
def update_photo(photo_id: str, user_id: str, updates: dict = Body(...), db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == user_id
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    for key, value in updates.items():
        if hasattr(photo, key):
            setattr(photo, key, value)

    db.commit()
    db.refresh(photo)

    return {"status": "success", "photo": {
        "id": str(photo.id),
        "blur_score": photo.blur_score,
        "is_blurred": photo.is_blurred,
        "processed_at": photo.processed_at,
    }}
