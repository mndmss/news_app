import os
import json
from django.http import HttpResponse, FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from .authentication import ApiKeyAuthentication
from .permissions import HasApiKey
from .serializers import PostSerializer, PostCreateSerializer, MediaFileSerializer, MediaUploadSerializer
from news.database import get_db_session
from news.models import Post, MediaFile, PostMedia
from news.services.media_service import MediaService


class MediaViewSet(viewsets.ViewSet):
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasApiKey]

    def list(self, request):
        with get_db_session() as db:
            media_files = db.query(MediaFile).order_by(MediaFile.created_at.desc()).all()
            serializer = MediaFileSerializer(media_files, many=True)

        return Response({'results': serializer.data})

    def retrieve(self, request, pk=None):
        with get_db_session() as db:
            media = db.query(MediaFile).filter(MediaFile.id == pk).first()
            if not media:
                return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = MediaFileSerializer(media)

        return Response(serializer.data)

    def destroy(self, request, pk=None):
        with get_db_session() as db:
            media = db.query(MediaFile).filter(MediaFile.id == pk).first()
            if not media:
                return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)

            attachments = db.query(PostMedia).filter(PostMedia.media_id == pk).all()
            for att in attachments:
                db.delete(att)

            file_path = os.path.join(settings.MEDIA_ROOT, media.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)

            db.delete(media)
            db.commit()

        return Response({'message': 'Media deleted'})

    @action(detail=False, methods=['post'])
    def upload(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data['file']

        try:
            media = MediaService.process_upload(uploaded_file)

            with get_db_session() as db:
                db.add(media)
                db.flush()
                db.commit()
                media_id = media.id

            return Response(
                MediaFileSerializer(media).data,
                status=status.HTTP_201_CREATED
            )
        except FileNotFoundError as e:
            error_msg = str(e)
            if 'ffmpeg' in error_msg.lower() or 'ffprobe' in error_msg.lower():
                return Response(
                    {'error': 'FFmpeg not found. Please install FFmpeg and add it to PATH.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            return Response(
                {'error': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except RuntimeError as e:
            error_msg = str(e)
            if 'ffmpeg' in error_msg.lower():
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            return Response(
                {'error': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        with get_db_session() as db:
            media = db.query(MediaFile).filter(MediaFile.id == pk).first()
            if not media:
                return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)

            file_path = os.path.join(settings.MEDIA_ROOT, media.file_path)
            if not os.path.exists(file_path):
                return Response({'error': 'File not found on disk'}, status=status.HTTP_404_NOT_FOUND)

            response = FileResponse(
                open(file_path, 'rb'),
                as_attachment=True,
                filename=media.file_name
            )
            return response


class PostViewSet(viewsets.ViewSet):
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasApiKey]

    def list(self, request):
        with get_db_session() as db:
            posts = db.query(Post).filter(Post.is_deleted == False).order_by(Post.created_at.desc()).all()
            serializer = PostSerializer(posts, many=True)
            data = serializer.data

        limit = request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                if limit > 0:
                    return Response({
                        'results': data[:limit],
                        'total_items': len(data),
                        'limit': limit,
                    })
            except (ValueError, TypeError):
                pass

        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        start = (page - 1) * per_page
        end = start + per_page

        return Response({
            'results': data[start:end],
            'page': page,
            'total_pages': (len(data) + per_page - 1) // per_page if data else 0,
            'total_items': len(data),
        })

    def create(self, request):
        serializer = PostCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with get_db_session() as db:
            post = Post(
                title=serializer.validated_data['title'],
                content=serializer.validated_data['content'],
                image=serializer.validated_data.get('image'),
            )
            db.add(post)
            db.flush()

            media_ids = serializer.validated_data.get('media_ids', [])
            for i, media_id in enumerate(media_ids):
                media = db.query(MediaFile).filter(MediaFile.id == media_id).first()
                if media:
                    attachment = PostMedia(
                        post_id=post.id,
                        media_id=media_id,
                        order=i,
                        is_primary=(i == 0)
                    )
                    db.add(attachment)

            db.commit()
            result = PostSerializer(post).data

        return Response(result, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        with get_db_session() as db:
            post = db.query(Post).filter(Post.id == pk).first()
            if not post or post.is_deleted:
                return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = PostSerializer(post)

        return Response(serializer.data)

    def update(self, request, pk=None):
        serializer = PostCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with get_db_session() as db:
            post = db.query(Post).filter(Post.id == pk).first()
            if not post or post.is_deleted:
                return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

            post.title = serializer.validated_data['title']
            post.content = serializer.validated_data['content']
            post.image = serializer.validated_data.get('image', post.image)

            existing = db.query(PostMedia).filter(PostMedia.post_id == pk).all()
            for att in existing:
                db.delete(att)

            media_ids = serializer.validated_data.get('media_ids', [])
            for i, media_id in enumerate(media_ids):
                media = db.query(MediaFile).filter(MediaFile.id == media_id).first()
                if media:
                    attachment = PostMedia(
                        post_id=post.id,
                        media_id=media_id,
                        order=i,
                        is_primary=(i == 0)
                    )
                    db.add(attachment)

            db.commit()
            result = PostSerializer(post).data

        return Response(result)

    def partial_update(self, request, pk=None):
        with get_db_session() as db:
            post = db.query(Post).filter(Post.id == pk).first()
            if not post or post.is_deleted:
                return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

            if 'title' in request.data:
                post.title = request.data['title']
            if 'content' in request.data:
                post.content = request.data['content']
            if 'image' in request.data:
                post.image = request.data['image']

            db.flush()
            result = PostSerializer(post)
            db.commit()

        return Response(result.data)

    def destroy(self, request, pk=None):
        with get_db_session() as db:
            post = db.query(Post).filter(Post.id == pk).first()
            if post and not post.is_deleted:
                post.is_deleted = True

                attachments = db.query(PostMedia).filter(PostMedia.post_id == pk).all()
                for att in attachments:
                    other = db.query(PostMedia).filter(
                        PostMedia.media_id == att.media_id,
                        PostMedia.post_id != pk
                    ).first()
                    if not other:
                        media = db.query(MediaFile).filter(MediaFile.id == att.media_id).first()
                        if media:
                            file_path = os.path.join(settings.MEDIA_ROOT, media.file_path)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            if media.original_path:
                                orig_path = os.path.join(settings.MEDIA_ROOT, media.original_path)
                                if os.path.exists(orig_path):
                                    os.remove(orig_path)
                            db.delete(media)
                    db.delete(att)

                db.commit()

        return Response(1)

    @action(detail=True, methods=['post'])
    def attach_media(self, request, pk=None):
        media_ids = request.data.get('media_ids', [])
        if not media_ids:
            return Response({'error': 'media_ids required'}, status=status.HTTP_400_BAD_REQUEST)

        max_files = settings.MEDIA_PROCESSING['MAX_FILES_PER_POST']
        if len(media_ids) > max_files:
            return Response(
                {'error': f'Максимум {max_files} файлов на пост'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with get_db_session() as db:
            post = db.query(Post).filter(Post.id == pk).first()
            if not post or post.is_deleted:
                return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

            existing_count = db.query(PostMedia).filter(
                PostMedia.post_id == pk
            ).count()

            for i, media_id in enumerate(media_ids):
                existing = db.query(PostMedia).filter(
                    PostMedia.post_id == pk,
                    PostMedia.media_id == media_id
                ).first()

                if not existing:
                    if existing_count + i < max_files:
                        attachment = PostMedia(
                            post_id=pk,
                            media_id=media_id,
                            order=existing_count + i,
                            is_primary=(existing_count == 0 and i == 0)
                        )
                        db.add(attachment)

            db.commit()

        return Response({'message': 'Media attached'})

    @action(detail=True, methods=['delete'], url_path='detach-media/(?P<media_id>[^/.]+)')
    def detach_media(self, request, pk=None, media_id=None):
        with get_db_session() as db:
            attachment = db.query(PostMedia).filter(
                PostMedia.post_id == pk,
                PostMedia.media_id == media_id
            ).first()

            if not attachment:
                return Response({'error': 'Attachment not found'}, status=status.HTTP_404_NOT_FOUND)

            db.delete(attachment)
            db.commit()

        return Response({'message': 'Media detached'})


class OpenAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        path = os.path.join(os.path.dirname(__file__), 'openapi.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Response(data)
