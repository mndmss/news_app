import os
import shutil
import uuid
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from news.models import MediaFile, PostMedia
from news.image_processor import ImageProcessor
from news.video_processor import VideoProcessor


class MediaService:
    UPLOAD_DIR = 'uploads'

    @classmethod
    def process_upload(cls, uploaded_file: UploadedFile) -> MediaFile:
        filename = uploaded_file.name
        file_type = cls.get_file_type(filename)

        if file_type == 'image' and ImageProcessor.is_supported(filename):
            return cls._process_image(uploaded_file)
        elif file_type == 'video' and VideoProcessor.is_supported(filename):
            return cls._process_video(uploaded_file)
        else:
            return cls._process_document(uploaded_file)

    @classmethod
    def _process_image(cls, uploaded_file: UploadedFile) -> MediaFile:
        temp_path = cls._save_temp(uploaded_file)

        try:
            result = ImageProcessor.process(temp_path)
            media = MediaFile(
                file_name=uploaded_file.name,
                file_path=result['path'],
                original_path=None,
                file_type='image',
                mime_type=ImageProcessor.get_mime_type(uploaded_file.name),
                file_size=result['size'],
                width=result['width'],
                height=result['height'],
                is_processed=True,
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return media

    @classmethod
    def _process_video(cls, uploaded_file: UploadedFile):
        temp_path = cls._save_temp(uploaded_file)

        try:
            result = VideoProcessor.process(temp_path)
            media = MediaFile(
                file_name=uploaded_file.name,
                file_path=result['path'],
                original_path=None,
                file_type='video',
                mime_type=VideoProcessor.get_mime_type(uploaded_file.name),
                file_size=result['size'],
                width=result['width'],
                height=result['height'],
                is_processed=True,
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return media

    @classmethod
    def _process_document(cls, uploaded_file: UploadedFile) -> MediaFile:
        upload_dir = os.path.join(settings.MEDIA_ROOT, cls.UPLOAD_DIR, 'documents')
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(uploaded_file.name)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, 'wb') as dest:
            shutil.copyfileobj(uploaded_file.file, dest)

        return MediaFile(
            file_name=uploaded_file.name,
            file_path=os.path.join(cls.UPLOAD_DIR, 'documents', filename),
            file_type='document',
            mime_type=uploaded_file.content_type,
            file_size=uploaded_file.size,
            is_processed=False,
        )

    @classmethod
    def _save_temp(cls, uploaded_file: UploadedFile) -> str:
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        ext = os.path.splitext(uploaded_file.name)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(temp_dir, filename)

        with open(temp_path, 'wb') as dest:
            shutil.copyfileobj(uploaded_file.file, dest)

        return temp_path

    @classmethod
    def get_file_type(cls, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower().lstrip('.')

        if ext in settings.MEDIA_PROCESSING['IMAGE']['FORMATS']:
            return 'image'
        elif ext in settings.MEDIA_PROCESSING['VIDEO']['FORMATS']:
            return 'video'
        else:
            return 'document'

    @classmethod
    def attach_to_post(cls, db, media: MediaFile, post_id: int, order: int = 0, is_primary: bool = False):
        post_media = PostMedia(
            post_id=post_id,
            media_id=media.id,
            order=order,
            is_primary=is_primary,
        )
        db.add(post_media)
        return post_media

    @classmethod
    def get_post_media(cls, db, post_id: int) -> list:
        attachments = db.query(PostMedia).filter(
            PostMedia.post_id == post_id
        ).order_by(PostMedia.order).all()

        media_files = []
        for att in attachments:
            media = db.query(MediaFile).filter(MediaFile.id == att.media_id).first()
            if media:
                media_files.append({
                    'attachment': att,
                    'media': media,
                })

        return media_files

    @classmethod
    def detach_from_post(cls, db, post_id: int, media_id: int):
        attachment = db.query(PostMedia).filter(
            PostMedia.post_id == post_id,
            PostMedia.media_id == media_id
        ).first()

        if attachment:
            db.delete(attachment)
            return True
        return False

    @classmethod
    def delete_media(cls, db, media_id: int):
        media = db.query(MediaFile).filter(MediaFile.id == media_id).first()
        if not media:
            return False

        file_path = os.path.join(settings.MEDIA_ROOT, media.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

        if media.original_path and os.path.exists(media.original_path):
            os.remove(media.original_path)

        db.delete(media)
        return True

    @classmethod
    def get_media_url(cls, media: MediaFile) -> str:
        return f"{settings.MEDIA_URL}{media.file_path}"

    @classmethod
    def get_icon_for_document(cls, mime_type: str) -> str:
        icons = {
            'application/pdf': '📕',
            'application/msword': '📘',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📘',
            'application/vnd.ms-excel': '📗',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📗',
            'application/zip': '📦',
            'application/x-rar-compressed': '📦',
            'application/x-7z-compressed': '📦',
            'text/plain': '📄',
            'text/csv': '📊',
        }
        return icons.get(mime_type, '📁')
