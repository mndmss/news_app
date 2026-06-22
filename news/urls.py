from django.urls import path
from . import views

urlpatterns = [
    # публичная часть
    path('', views.post_list, name='post_list'),

    # админ-панель - посты
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/create/', views.admin_post_create, name='admin_post_create'),
    path('admin/edit/<int:post_id>/', views.admin_post_edit, name='admin_post_edit'),
    path('admin/delete/<int:post_id>/', views.admin_post_delete, name='admin_post_delete'),

    # админ-панель - апи-ключи
    path('admin/keys/', views.admin_api_keys, name='admin_api_keys'),
    path('admin/keys/create/', views.admin_api_key_create, name='admin_api_key_create'),
    path('admin/keys/<int:key_id>/toggle/', views.admin_api_key_toggle, name='admin_api_key_toggle'),
    path('admin/keys/<int:key_id>/delete/', views.admin_api_key_delete, name='admin_api_key_delete'),

    # админ-панель - пользователи
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/create/', views.admin_user_create, name='admin_user_create'),
    path('admin/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),
]
