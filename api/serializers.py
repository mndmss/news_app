from datetime import datetime, timezone

from rest_framework import serializers
from django.conf import settings


class TimestampField(serializers.Field):
    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())


class MediaFileSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    file_name = serializers.CharField(read_only=True)
    file_path = serializers.CharField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    width = serializers.IntegerField(read_only=True)
    height = serializers.IntegerField(read_only=True)
    is_processed = serializers.BooleanField(read_only=True)
    created_at = TimestampField(read_only=True)

    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return f"{settings.MEDIA_URL}{obj.file_path}"


class PostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    content = serializers.SerializerMethodField()
    image = serializers.CharField(allow_null=True, required=False)
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    media = serializers.SerializerMethodField()

    def validate_title(self, value):
        if value and len(value) > 255:
            raise serializers.ValidationError("Заголовок не может быть длиннее 255 символов")
        return value.strip() if value else ''

    def get_content(self, obj):
        if obj.title:
            return obj.title + '\n' + (obj.content or '')
        return obj.content or ''

    def get_media(self, obj):
        from news.services.media_service import MediaService
        from news.database import get_db_session

        with get_db_session() as db:
            attachments = MediaService.get_post_media(db, obj.id)
            media_list = []
            for att in attachments:
                media = att['media']
                serializer = MediaFileSerializer(media)
                data = serializer.data
                data['order'] = att['attachment'].order
                data['is_primary'] = att['attachment'].is_primary
                media_list.append(data)
            return media_list


class PostCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    content = serializers.CharField(required=False, allow_blank=True, default='')
    image = serializers.CharField(allow_null=True, required=False)
    media_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    def validate_title(self, value):
        if value and len(value) > 255:
            raise serializers.ValidationError("Заголовок не может быть длиннее 255 символов")
        return value.strip() if value else ''

    def validate_content(self, value):
        return value.strip() if value else ''

    def validate(self, data):
        if not data.get('content') and not data.get('media_ids', []):
            raise serializers.ValidationError(
                "Заполните содержание или прикрепите медиафайлы"
            )
        media_ids = data.get('media_ids', [])
        max_files = settings.MEDIA_PROCESSING['MAX_FILES_PER_POST']
        if len(media_ids) > max_files:
            raise serializers.ValidationError(
                f"Максимум {max_files} файлов на пост"
            )
        return data


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        max_size = settings.FILE_UPLOAD_MAX_SIZE
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Файл слишком большой. Максимум {max_size // (1024*1024)} МБ"
            )
        return value
