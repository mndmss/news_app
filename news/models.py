import secrets
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    image = Column(String(500), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"


class ApiKey(Base):
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name='{self.name}')>"


class MediaFile(Base):
    __tablename__ = 'media_files'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    original_path = Column(String(500), nullable=True)
    file_type = Column(String(20), nullable=False)  # image, video, document
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    def __repr__(self):
        return f"<MediaFile(id={self.id}, file_name='{self.file_name}', type='{self.file_type}')>"


class PostMedia(Base):
    __tablename__ = 'post_media'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    media_id = Column(Integer, ForeignKey('media_files.id', ondelete='CASCADE'), nullable=False)
    order = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<PostMedia(post_id={self.post_id}, media_id={self.media_id})>"
