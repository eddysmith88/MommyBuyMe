from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from db.models import Admin
from db.session import AsyncSessionLocal

SUPER_ADMIN_IDS = [887934499, 6539889022]

class IsSuperAdmin(BaseFilter):
    async def __call__(self, callback: CallbackQuery) -> bool:

        user_id = callback.from_user.id

        if user_id in SUPER_ADMIN_IDS:
            return True

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Admin).where(Admin.telegram_id == callback.from_user.id)
            )
            admin = result.scalar_one_or_none()
            return admin is not None and admin.status is True




# @router.message(Command("start"), IsSuperAdmin())
# async def start_for_superadmin(message: Message):
#     await message.answer("Ви супер-адміністратор. Меню ЦО...")
#
# @router.message(Command("start"), IsAdmin())
# async def start_for_admin(message: Message):
#     await message.answer("Ви звичайний адмін")