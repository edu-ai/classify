from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, DECIMAL, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Photo(Base):
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
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
    tag = Column(String(100))
    tagged_at = Column(DateTime(timezone=True))
