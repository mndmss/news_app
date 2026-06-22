import os
import secrets
from datetime import datetime, timezone
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib import messages
from .database import get_db_session
from .models import Post, ApiKey, MediaFile, PostMedia

def post_list(request):
    """Главная страница - список всех новостей"""
    with get_db_session() as db:
        posts = (
            db.query(Post)
            .filter(Post.is_deleted == False)
            .order_by(Post.created_at.desc())
            .all()
        )

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    api_key = None
    with get_db_session() as db:
        key_obj = db.query(ApiKey).filter(ApiKey.is_active == True).first()
        if key_obj:
            api_key = key_obj.key

    return render(request, 'news/post_list.html', {'page_obj': page_obj, 'api_key': api_key})

def admin_login(request):
    """Страница входа в админ-панель"""
    if request.user.is_authenticated:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'admin_dashboard')
            return redirect(next_url)
        return render(request, 'admin/login.html', {'error': 'Неверный логин или пароль'})

    return render(request, 'admin/login.html')

@login_required(login_url='/admin/login/')
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

@login_required(login_url='/admin/login/')
def admin_dashboard(request):
    """Панель управления - список всех постов"""
    with get_db_session() as db:
        posts = db.query(Post).filter(Post.is_deleted == False).order_by(Post.created_at.desc()).all()
    for p in posts:
        p.ts = _ts(p.created_at)
    return render(request, 'admin/dashboard.html', {'posts': posts})


@login_required(login_url='/admin/login/')
def admin_post_create(request):
    """Создание нового поста"""
    api_key = _get_api_key()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        media_ids = request.POST.getlist('media_ids')

        if not content and not media_ids:
            return render(request, 'admin/post_form.html', {
                'error': 'Заполните содержание или прикрепите медиафайлы',
                'title': title,
                'content': content,
                'media_ids': media_ids,
                'api_key': api_key,
                'MEDIA_URL': settings.MEDIA_URL,
            })

        with get_db_session() as db:
            post = Post(
                title=title,
                content=content,
            )
            db.add(post)
            db.flush()

            seen = set()
            for i, media_id in enumerate(media_ids):
                try:
                    mid = int(media_id)
                except (ValueError, TypeError):
                    continue
                if mid in seen:
                    continue
                seen.add(mid)
                media = db.query(MediaFile).filter(MediaFile.id == mid).first()
                if media:
                    attachment = PostMedia(
                        post_id=post.id,
                        media_id=mid,
                        order=i,
                        is_primary=(i == 0)
                    )
                    db.add(attachment)

            db.commit()

        return redirect('admin_dashboard')

    return render(request, 'admin/post_form.html', {
        'title': 'Создать пост',
        'api_key': api_key,
        'MEDIA_URL': settings.MEDIA_URL,
    })


@login_required(login_url='/admin/login/')
def admin_post_edit(request, post_id):
    """Редактирование поста"""
    api_key = _get_api_key()

    with get_db_session() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post or post.is_deleted:
            return redirect('admin_dashboard')

        attachments = db.query(PostMedia).filter(
            PostMedia.post_id == post_id
        ).order_by(PostMedia.order).all()

        post_media = []
        for att in attachments:
            media = db.query(MediaFile).filter(MediaFile.id == att.media_id).first()
            if media:
                post_media.append({
                    'media': media,
                    'icon': _get_file_icon(media.mime_type),
                })

        media_ids = [att.media_id for att in attachments]

        if request.method == 'POST':
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()
            new_media_ids = request.POST.getlist('media_ids')

            if not content and not new_media_ids:
                return render(request, 'admin/post_form.html', {
                    'error': 'Заполните содержание или прикрепите медиафайлы',
                    'post': post,
                    'post_media': [],
                    'media_ids': [],
                    'api_key': api_key,
                    'MEDIA_URL': settings.MEDIA_URL,
                })

            post.title = title
            post.content = content

            existing = db.query(PostMedia).filter(PostMedia.post_id == post_id).all()
            for att in existing:
                db.delete(att)

            seen = set()
            for i, media_id in enumerate(new_media_ids):
                try:
                    mid = int(media_id)
                except (ValueError, TypeError):
                    continue
                if mid in seen:
                    continue
                seen.add(mid)
                media = db.query(MediaFile).filter(MediaFile.id == mid).first()
                if media:
                    attachment = PostMedia(
                        post_id=post_id,
                        media_id=mid,
                        order=i,
                        is_primary=(i == 0)
                    )
                    db.add(attachment)

            db.commit()

            return redirect('admin_dashboard')

    return render(request, 'admin/post_form.html', {
        'post': post,
        'post_media': post_media,
        'media_ids': media_ids,
        'title': 'Редактировать пост',
        'api_key': api_key,
        'MEDIA_URL': settings.MEDIA_URL,
    })

@login_required(login_url='/admin/login/')
def admin_post_delete(request, post_id):
    """Удаление поста"""
    with get_db_session() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post or post.is_deleted:
            return redirect('admin_dashboard')

        post.is_deleted = True

        attachments = db.query(PostMedia).filter(PostMedia.post_id == post_id).all()
        for att in attachments:
            other = db.query(PostMedia).filter(
                PostMedia.media_id == att.media_id,
                PostMedia.post_id != post_id
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
    return redirect('admin_dashboard')

@login_required(login_url='/admin/login/')
def admin_api_keys(request):
    """Список апи-ключей"""
    with get_db_session() as db:
        keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return render(request, 'admin/api_keys.html', {'keys': keys})

@login_required(login_url='/admin/login/')
def admin_api_key_create(request):
    """Создание нового апи-ключа"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            with get_db_session() as db:
                keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
            return render(request, 'admin/api_keys.html', {
                'keys': keys,
                'error': 'Название обязательно',
            })

        key = secrets.token_hex(32)
        with get_db_session() as db:
            api_key = ApiKey(key=key, name=name)
            db.add(api_key)
            db.commit()

        return redirect('admin_api_keys')

    return redirect('admin_api_keys')

@login_required(login_url='/admin/login/')
def admin_api_key_toggle(request, key_id):
    """Активация/деактивация ключа"""
    with get_db_session() as db:
        api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if api_key:
            api_key.is_active = not api_key.is_active
            db.commit()
    return redirect('admin_api_keys')

@login_required(login_url='/admin/login/')
def admin_api_key_delete(request, key_id):
    """Удаление апи-ключа"""
    with get_db_session() as db:
        api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if api_key:
            db.delete(api_key)
            db.commit()
    return redirect('admin_api_keys')

@login_required(login_url='/admin/login/')
def admin_users(request):
    """Список администраторов"""
    users = User.objects.order_by('-date_joined').all()
    return render(request, 'admin/users.html', {'users': users})

@login_required(login_url='/admin/login/')
def admin_user_create(request):
    """Создание нового администратора"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        email = request.POST.get('email', '').strip()

        if not username or not password:
            users = User.objects.order_by('-date_joined').all()
            return render(request, 'admin/users.html', {
                'users': users,
                'error': 'Логин и пароль обязательны',
            })

        if User.objects.filter(username=username).exists():
            users = User.objects.order_by('-date_joined').all()
            return render(request, 'admin/users.html', {
                'users': users,
                'error': 'Пользователь с таким логином уже существует',
            })

        User.objects.create_superuser(username, email or f'{username}@local', password)
        return redirect('admin_users')

    return redirect('admin_users')

@login_required(login_url='/admin/login/')
def admin_user_delete(request, user_id):
    """Удаление администратора"""
    total = User.objects.count()
    if total <= 1:
        messages.error(request, 'Нельзя удалить последнего пользователя')
        return redirect('admin_users')

    user = User.objects.filter(id=user_id).first()
    if user:
        user.delete()

    return redirect('admin_users')

def _ts(dt):
    """Преобразовать datetime в unix timestamp"""
    if dt is None:
        return None
    if isinstance(dt, datetime) and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

def _get_api_key():
    """Получить активный апи-ключ"""
    try:
        with get_db_session() as db:
            key = db.query(ApiKey).filter(ApiKey.is_active == True).first()
            return key.key if key else ''
    except Exception:
        return ''

def _get_file_icon(mime_type):
    """Получить иконку для типа файла"""
    if mime_type:
        if 'pdf' in mime_type or 'word' in mime_type or 'document' in mime_type:
            return '<i class="bi bi-file-text" style="font-size:32px;"></i>'
        elif 'excel' in mime_type or 'spreadsheet' in mime_type:
            return '<i class="bi bi-file-spreadsheet" style="font-size:32px;"></i>'
        elif 'zip' in mime_type or 'rar' in mime_type or '7z' in mime_type:
            return '<i class="bi bi-file-zip" style="font-size:32px;"></i>'
        elif 'image' in mime_type:
            return '<i class="bi bi-file-image" style="font-size:32px;"></i>'
        elif 'video' in mime_type:
            return '<i class="bi bi-file-play" style="font-size:32px;"></i>'
    return '<i class="bi bi-file-earmark" style="font-size:32px;"></i>'
