from rest_framework.permissions import BasePermission

class HasApiKey(BasePermission):
    message = 'API key required'

    def has_permission(self, request, view):
        return request.auth is not None
