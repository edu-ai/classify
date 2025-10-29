from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Base, Photo
import os
import requests
import json
from datetime import datetime
import time


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
GOOGLE_PHOTOS_API_URL = "https://photoslibrary.googleapis.com/v1"

def get_access_token_from_auth_service(user_id: str) -> str:
    try:
        print(f"{AUTH_SERVICE_URL}/tokens/{user_id}")
        res = requests.get(f"{AUTH_SERVICE_URL}/tokens/{user_id}")
        res.raise_for_status()
        data = res.json()
        return data["access_token"]
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to get access token from Auth Service: {e}")

def create_unblurred_album(user_id: str, db: Session) -> dict:
    """
    Create a new Google Photos album containing only unblurred images for the specified user.
    """
    try:
        # 1. データベースから未ブレ写真を取得
        unblurred_photos = db.query(Photo).filter(
            Photo.user_id == user_id,
            Photo.is_blurred == False
        ).all()

        if not unblurred_photos:
            raise HTTPException(status_code=404, detail="No unblurred photos found for this user")

        # 2. アクセストークン取得
        access_token = get_access_token_from_auth_service(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}

        # 3. アルバム作成
        timestamp = datetime.now().strftime("%Y-%m-%d")
        album_title = f"Unblurred Photos {timestamp}"
        album_data = {"album": {"title": album_title}}

        print(f"Creating album: {album_title}")
        album_response = requests.post(
            f"{GOOGLE_PHOTOS_API_URL}/albums",
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps(album_data)
        )
        album_response.raise_for_status()
        album_result = album_response.json()
        album_id = album_result["id"]
        print(f"Album created with ID: {album_id}")

        # 4. 写真アップロード＆メディアアイテム作成
        media_items = []
        uploaded_count = 0

        for photo in unblurred_photos:
            try:
                # 4-1. Google Photos からダウンロード
                photo_url = f"{photo.base_url}=d"
                photo_response = requests.get(photo_url, headers=headers)
                photo_response.raise_for_status()

                # 4-2. Google Photos へアップロード
                upload_response = requests.post(
                    f"{GOOGLE_PHOTOS_API_URL}/uploads",
                    headers={"Authorization": f"Bearer {access_token}"},
                    data=photo_response.content
                )
                upload_response.raise_for_status()
                upload_token = upload_response.text

                # 4-3. メディアアイテム作成
                media_item_data = {
                    "newMediaItems": [{
                        "description": f"Uploaded from classify app - {photo.filename}",
                        "simpleMediaItem": {
                            "uploadToken": upload_token,
                            "fileName": photo.filename
                        }
                    }]
                }
                media_response = requests.post(
                    f"{GOOGLE_PHOTOS_API_URL}/mediaItems:batchCreate",
                    headers={**headers, "Content-Type": "application/json"},
                    data=json.dumps(media_item_data)
                )
                media_response.raise_for_status()
                media_result = media_response.json()
                results = media_result.get("newMediaItemResults", [])

                # 4-4. 成功判定を code=0 で行う
                for result in results:
                    status = result.get("status", {})
                    if status.get("code", 0) != 0:  # 0 以外は失敗
                        print(f"Failed to create media item {photo.filename}: {status}")
                        continue
                    media_item = result.get("mediaItem")
                    if media_item and media_item.get("id"):
                        media_items.append(media_item["id"])
                        uploaded_count += 1
                        print(f"Uploaded photo: {photo.filename}")

            except Exception as e:
                print(f"Failed to upload photo {photo.filename}: {e}")
                continue

        if not media_items:
            raise HTTPException(status_code=500, detail="Failed to upload any photos")

        # デバッグログ
        print(f"Adding media items to album {album_id}: {media_items}")

        # 安全のため 1 秒待機
        time.sleep(1)

        add_media_data = {"mediaItemIds": media_items}
        add_response = requests.post(
            f"{GOOGLE_PHOTOS_API_URL}/albums/{album_id}:batchAddMediaItems",
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps(add_media_data)
        )
        add_response.raise_for_status()
        print(f"Added {len(media_items)} photos to album")

        # 6. 結果返却
        return {
            "albumId": album_id,
            "albumTitle": album_title,
            "uploadedCount": uploaded_count
        }

    except requests.RequestException as e:
        print(f"Google Photos API error: {e}")
        raise HTTPException(status_code=500, detail=f"Google Photos API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


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

@app.post("/google/unblurred-album/{user_id}")
def create_unblurred_album_endpoint(user_id: str, db: Session = Depends(get_db)):
    """
    Create a new Google Photos album containing only unblurred images for the specified user.
    """
    return create_unblurred_album(user_id, db)
