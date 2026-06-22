import os
import uuid
from PIL import Image
from django.conf import settings


class ImageProcessor:
    MAX_WIDTH = settings.MEDIA_PROCESSING['IMAGE']['MAX_WIDTH']
    MAX_HEIGHT = settings.MEDIA_PROCESSING['IMAGE']['MAX_HEIGHT']
    QUALITY = settings.MEDIA_PROCESSING['IMAGE']['QUALITY']

    @classmethod
    def process(cls, input_path: str, output_dir: str = None) -> dict:
        if output_dir is None:
            output_dir = os.path.join(settings.MEDIA_ROOT, 'processed', 'images')

        os.makedirs(output_dir, exist_ok=True)

        original_image = Image.open(input_path)
        original_width, original_height = original_image.size

        image = original_image.copy()

        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        aspect_ratio = original_width / original_height
        target_aspect = cls.MAX_WIDTH / cls.MAX_HEIGHT

        if original_width > cls.MAX_WIDTH or original_height > cls.MAX_HEIGHT:
            if aspect_ratio > target_aspect:
                new_width = cls.MAX_WIDTH
                new_height = int(cls.MAX_WIDTH / aspect_ratio)
            else:
                new_height = cls.MAX_HEIGHT
                new_width = int(cls.MAX_HEIGHT * aspect_ratio)

            image = image.resize((new_width, new_height), Image.LANCZOS)

        ext = 'jpg'
        if original_image.format and original_image.format.lower() in ['png', 'webp']:
            ext = original_image.format.lower()

        filename = f"{uuid.uuid4().hex}.{ext}"
        output_path = os.path.join(output_dir, filename)

        save_kwargs = {'quality': cls.QUALITY, 'optimize': True}
        if ext == 'png':
            save_kwargs = {'optimize': True}

        image.save(output_path, **save_kwargs)

        final_width, final_height = image.size

        return {
            'path': os.path.join('processed', 'images', filename),
            'original_path': input_path,
            'width': final_width,
            'height': final_height,
            'size': os.path.getsize(output_path),
            'ext': ext,
        }

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        return ext in settings.MEDIA_PROCESSING['IMAGE']['FORMATS']

    @classmethod
    def get_mime_type(cls, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        return mime_types.get(ext, 'application/octet-stream')
