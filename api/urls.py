from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PostViewSet, MediaViewSet, OpenAPIView
from .views_ui import swagger_ui

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'media', MediaViewSet, basename='media')

urlpatterns = [
    path('', include(router.urls)),
    path('swagger/', swagger_ui, name='swagger_ui'),
    path('openapi.json', OpenAPIView.as_view(), name='openapi_json'),
]
