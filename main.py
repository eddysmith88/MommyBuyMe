"""
Основний файл
Запуск бота
Додаткові функції для автоматичних задач
"""
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router

import logging

from datetime import datetime, UTC
from sqlalchemy import select

from db.models import Promo
from db.session import AsyncSessionLocal

from app_config import BOT_TOKEN
from services.client_export import export_clients_to_gsheet
from utils.bot_commands import set_default_commands
from handlers.start import router as start_router
from handlers.client import router as client_router
from handlers.geo import router as geolocation
from handlers.show_posts_promo import router as show_posts_promos
from handlers.super_admin import router as super_admin
from handlers.reject import router as reject
from handlers.admin import router as admin
from handlers.city_change import router as city_change


logging.basicConfig(level=logging.INFO)

# Головний роутер
main_router = Router()
main_router.include_router(start_router)
main_router.include_router(client_router)
main_router.include_router(geolocation)
main_router.include_router(show_posts_promos)
main_router.include_router(super_admin)
main_router.include_router(reject)
main_router.include_router(admin)
main_router.include_router(city_change)


# Конфігурації ботів
BOTS_CONFIG = [
    {"token": BOT_TOKEN, "router": main_router, "name": "MainBot"},
]


async def export_clients_worker(interval_seconds: int = 1800):
    while True:
        try:
            await export_clients_to_gsheet()
            logging.info("✅ Автоматичний експорт клієнтів виконано")
        except Exception as e:
            logging.warning(f"❌ Помилка автоматичного експорту клієнтів: {e}")
        await asyncio.sleep(interval_seconds)


async def promo_cleanup_worker(interval_seconds: int = 360):
    """
    функція видалення акцій
    :param interval_seconds:
    :return:
    """
    while True:
        deleted = await delete_expired_promos()
        if deleted:
            logging.info(f"🗑 Видалено {deleted} прострочених акцій")
        await asyncio.sleep(interval_seconds)


async def delete_expired_promos():
    """
    Функція автовидалення акцій за терміном придатності
    :return:
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo))
        promos = result.scalars().all()

        deleted_count = 0
        for promo in promos:
            # promo.date_expire — це об'єкт datetime.date
            if isinstance(promo.date_expire, datetime):
                expire_date = promo.date_expire.date()
            else:
                expire_date = promo.date_expire

            if expire_date < datetime.utcnow().date():
                await session.delete(promo)
                deleted_count += 1

        await session.commit()
        return deleted_count


async def run_bot(token: str, router, name: str):
    """
    Запуск бота,
    Запуск роутерів,
    Бокові кнопки
    :param token:
    :param router:
    :param name:
    :return:
    """
    try:
        bot = Bot(token=token)
        dp = Dispatcher(storage=MemoryStorage())

        dp.include_router(router)
        logging.info(f"[{name}] Запуск...")
        await set_default_commands(bot)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"[{name}] ❌ Помилка: {e}")


async def main():
    service_bot = Bot(token=BOTS_CONFIG[0]["token"])

    tasks = [
        run_bot(config["token"], config["router"], config["name"])
        for config in BOTS_CONFIG
    ]
    
    tasks.append(promo_cleanup_worker())

    # tasks.append(export_clients_worker())

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("⛔️ Зупинено вручну")