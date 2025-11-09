-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Photos table
CREATE TABLE photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    google_photo_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(500),
    media_type VARCHAR(50) DEFAULT 'IMAGE',
    mime_type VARCHAR(100),
    base_url TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    file_size BIGINT,
    blur_score DECIMAL(5,4),
    is_blurred BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    google_created_time TIMESTAMP WITH TIME ZONE,
    tag TEXT,
    tagged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_photos_user_id ON photos(user_id);
CREATE INDEX idx_photos_google_photo_id ON photos(google_photo_id);
CREATE INDEX idx_photos_user_blur ON photos(user_id, is_blurred);
CREATE INDEX idx_photos_processed ON photos(processed_at) WHERE processed_at IS NULL;
