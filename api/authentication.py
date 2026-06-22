from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from news.models import ApiKey
from news.database import get_db_session


class ApiKeyAuthentication(BaseAuthentication):
    keyword = 'X-API-Key'

    def authenticate(self, request: Request):
        api_key = request.headers.get(self.keyword)
        if not api_key:
            return None

        with get_db_session() as db:
            key_obj = db.query(ApiKey).filter(
                ApiKey.key == api_key,
                ApiKey.is_active == True
            ).first()

            if not key_obj:
                raise AuthenticationFailed('Invalid or inactive API key')

        return (None, api_key)

    def authenticate_header(self, request):
        return self.keyword
