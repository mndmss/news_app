import os
import uuid
import subprocess
from django.conf import settings


class VideoProcessor:
    MAX_WIDTH = settings.MEDIA_PROCESSING['VIDEO']['MAX_WIDTH']
    MAX_HEIGHT = settings.MEDIA_PROCESSING['VIDEO']['MAX_HEIGHT']
    CRF = settings.MEDIA_PROCESSING['VIDEO']['CRF']
    PRESET = settings.MEDIA_PROCESSING['VIDEO']['PRESET']

    @classmethod
    def process(cls, input_path: str, output_dir: str = None) -> dict:
        if not cls.check_ffmpeg_installed():
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg and add it to PATH. "
                "Download: https://ffmpeg.org/download.html"
            )

        if output_dir is None:
            output_dir = os.path.join(settings.MEDIA_ROOT, 'processed', 'videos')

        os.makedirs(output_dir, exist_ok=True)

        probe_result = cls._probe(input_path)
        original_width = probe_result.get('width', 0)
        original_height = probe_result.get('height', 0)
        duration = probe_result.get('duration', 0)

        scale_filter = f'scale={cls.MAX_WIDTH}:{cls.MAX_HEIGHT}:force_original_aspect_ratio=decrease:force_divisible_by=2'

        filename = f"{uuid.uuid4().hex}.mp4"
        output_path = os.path.join(output_dir, filename)

        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', scale_filter,
            '-c:v', 'libx264',
            '-crf', str(cls.CRF),
            '-preset', cls.PRESET,
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr}")

        output_probe = cls._probe(output_path)
        return {
            'path': os.path.join('processed', 'videos', filename),
            'original_path': input_path,
            'width': output_probe.get('width', original_width),
            'height': output_probe.get('height', original_height),
            'size': os.path.getsize(output_path),
            'duration': duration,
            'ext': 'mp4',
        }

    @classmethod
    def _probe(cls, input_path: str) -> dict:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration',
            '-of', 'csv=p=0',
            input_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                if len(parts) >= 2:
                    return {
                        'width': int(parts[0]),
                        'height': int(parts[1]),
                        'duration': float(parts[2]) if len(parts) > 2 else 0,
                    }
        except Exception:
            pass

        return {'width': 0, 'height': 0, 'duration': 0}

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        return ext in settings.MEDIA_PROCESSING['VIDEO']['FORMATS']

    @classmethod
    def get_mime_type(cls, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.webm': 'video/webm',
            '.avi': 'video/x-msvideo',
        }
        return mime_types.get(ext, 'video/mp4')

    @classmethod
    def check_ffmpeg_installed(cls) -> bool:
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
