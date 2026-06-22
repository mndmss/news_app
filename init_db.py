"""
Скрипт для инициализации SQLAlchemy таблиц.
Запускать после первого запуска Django, чтобы создать таблицы.
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from news.database import init_db

if __name__ == '__main__':
    print('Создание таблиц SQLAlchemy...')
    init_db()
    print('Готово! Таблицы созданы.')
