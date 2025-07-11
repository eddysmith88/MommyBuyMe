import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

from dotenv import load_dotenv
load_dotenv()

# Додаємо шлях до кореня проєкту, щоб імпорти працювали
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Імпорт моделей і metadata
from db.models import Base

# Підключення логів (не обов'язково, але корисно)
fileConfig(context.config.config_file_name)

# Це метадані, які Alembic буде використовувати для порівняння з БД
target_metadata = Base.metadata

# Отримуємо sync-URL для Alembic (НЕ asyncpg)
DB_URL = os.getenv("ALEMBIC_SYNC_DB_URL")

def run_migrations_offline():
    """Запуск офлайн-міграцій (без підключення до БД)"""
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Запуск онлайн-міграцій (через sync SQLAlchemy engine)"""
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


# Визначаємо режим запуску
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
