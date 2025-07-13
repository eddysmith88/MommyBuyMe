from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Client
from info import cities
from keyboard.keyboards import city_keyboard, city_kb

router = Router()


# cities = [
#     "Чернівці", "Чернігів", "Івано-Франківськ", "Ужгород" , "Запоріжжя" , "Київ"
# ]


# def city_keyboard():
#     buttons = [
#         [InlineKeyboardButton(text=city_name, callback_data=f"select_city:{city_name}")]
#         for city_name, _ in cities
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=buttons)
#
# def city_kb():
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="💡Про нас", callback_data="about"),
#          InlineKeyboardButton(text="🆕Наші акції та новини", callback_data="news")],
#         [InlineKeyboardButton(text="❔Часті питання", callback_data="faq"),
#          InlineKeyboardButton(text="🗺Найближчі точки", callback_data="nearby")],
#         [InlineKeyboardButton(text="🤝Стати партнером", callback_data="partner"),
#          InlineKeyboardButton(text="🛠Тех. підтримка", callback_data="support")],
#         [InlineKeyboardButton(text="Змінити місто", callback_data="change_city")],
#     ])


@router.callback_query(F.data == "change_city")
async def change_city_accept(callback: CallbackQuery):
    await callback.message.answer("Бажаєте змінити місто", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так", callback_data="yes_change")],
        [InlineKeyboardButton(text="❌ Ні", callback_data="no_change")]
    ]))


@router.callback_query(F.data == "yes_change")
async def show_city_list(callback: CallbackQuery):
    await callback.message.edit_text("Оберіть нове місто:", reply_markup=city_keyboard())
    await callback.answer()


@router.callback_query(F.data == "no_change")
async def no_change(callback: CallbackQuery):
    await callback.message.edit_text("Зміна міста скасована.", reply_markup=city_kb())
    await callback.answer()



@router.callback_query(F.data.startswith("select_city:"))
async def select_city(callback: CallbackQuery, session: AsyncSession):
    selected_city = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Перевірка, чи користувач існує
    result = await session.execute(select(Client).where(Client.telegram_id == user_id))
    client = result.scalar_one_or_none()

    if client:
        # Оновлення міста
        await session.execute(update(Client).where(Client.telegram_id == user_id).values(city=selected_city))
        await session.commit()
        await callback.message.edit_text(f"Місто змінено на: {selected_city}", reply_markup=city_kb())
    else:
        await callback.message.edit_text("Користувача не знайдено у базі.")

    await callback.answer()
