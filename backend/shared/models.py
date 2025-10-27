from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, DECIMAL, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    profile_picture_url = Column(Text)
    blur_threshold = Column(DECIMAL(3, 2), server_default="0.50")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")
    oauth_token = relationship("OAuthToken", back_populates="user", uselist=False)

class Photo(Base):
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_photo_id = Column(String(255), unique=True, nullable=False)
    filename = Column(String(500))
    media_type = Column(String(50), default="IMAGE")
    blur_score = Column(DECIMAL(5, 4))
    is_blurred = Column(Boolean)
    processed_at = Column(DateTime(timezone=True))
    google_created_time = Column(DateTime(timezone=True))
    base_url = Column(Text, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="photos")

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    scope = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="oauth_token")
