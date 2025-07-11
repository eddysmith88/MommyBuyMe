import os
from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql+asyncpg://")


def set_main_option(param, DB_URL):
    return None