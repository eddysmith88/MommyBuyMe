from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from db.models import Admin
from db.session import AsyncSessionLocal


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
            return result.scalar_one_or_none() is not None
