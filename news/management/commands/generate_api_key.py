import secrets
from django.core.management.base import BaseCommand
from news.database import get_db_session
from news.models import ApiKey


class Command(BaseCommand):
    help = 'Генерация нового API-ключа'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Название/описание ключа')

    def handle(self, *args, **options):
        name = options['name']
        key = secrets.token_hex(32)  # 64 символа

        with get_db_session() as db:
            api_key = ApiKey(key=key, name=name)
            db.add(api_key)
            db.commit()

        self.stdout.write(self.style.SUCCESS(f'API-Key создан!'))
        self.stdout.write(self.style.WARNING(f'Name: {name}'))
        self.stdout.write(self.style.WARNING(f'Key:  {key}'))
        self.stdout.write(self.style.SUCCESS('Сохраните ключ — он больше не будет показан.'))
