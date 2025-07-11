from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.filters import CommandStart
from sqlalchemy import select
from db.models import Client, Admin, Promo
from db.session import AsyncSessionLocal

from keyboard.keyboards import super_admin_menu, city_kb, admin_menu
# 887934499

SUPER_ADMIN_IDS = [6539889022, 887934499]


router = Router()


cities = [
    "Бердичів", "Дніпро", "Житомир", "Ізмаїл" , "Запоріжжя" , "Івано-Франківськ", "Львів",
    "Кривій Ріг", "Кропивницький", "Луцьк", "Одеса", "Первомайськ", "Рівне", "Ужгород",
    "Київ", "Харків", "Чернігів"
]


@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    is_superadmin = user_id in SUPER_ADMIN_IDS

    async with AsyncSessionLocal() as session:
        # Перевірка на адміна
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()
        is_admin = bool(admin)

        # Перевірка на клієнта (але тільки якщо не адмін і не супер)
        client = None
        if not is_admin and not is_superadmin:
            result = await session.execute(select(Client).where(Client.telegram_id == user_id))
            client = result.scalar_one_or_none()

            if not client:
                # Попросити вибрати місто
                choose_city_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=city, callback_data=f"choose_city:{city}")]
                    for city in cities
                ])
                return await message.answer("🏙 Оберіть ваше місто:", reply_markup=choose_city_kb)

        # Визначення міста (для вітання)
        city_name = (admin.city if is_admin else client.city) if not is_superadmin else "всі міста"
        greeting = f"👋 Привіт {user_name}!\n🧸 Вас вітає 'Мама ну купи' 🧸{city_name}"

        if is_superadmin:
            await message.answer_photo(
                photo="https://optim.tildacdn.one/tild6430-3632-4466-a565-393138306265/-/resize/666x/-/format/webp/2_2.png.webp",
                caption=f"{greeting} \n🔐 Ви супер-адміністратор",
                parse_mode="Markdown",
                reply_markup=super_admin_menu()
            )
        elif is_admin:
            await message.answer(greeting + "\n✅ Ви адміністратор", reply_markup=admin_menu())
        else:
            await message.answer_photo(
                photo="https://optim.tildacdn.one/tild6430-3632-4466-a565-393138306265/-/resize/666x/-/format/webp/2_2.png.webp",
                caption=greeting,
                reply_markup=city_kb()
            )

            # Якщо ще немає телефону — просимо його
            # if client and not client.phone_number:
            #     phone_kb = ReplyKeyboardMarkup(
            #         keyboard=[
            #             [KeyboardButton(text="📱 Надати номер телефону", request_contact=True)],
            #             [KeyboardButton(text="⏭ Пропустити")]
            #         ],
            #         resize_keyboard=True,
            #         one_time_keyboard=False
            #     )
            #     await message.answer(
            #         "Будь ласка, поділіться номером телефону або натисніть «Пропустити»:",
            #         reply_markup=phone_kb
            #     )

            # Показати всі акції для міста клієнта
            result = await session.execute(
                select(Promo).where(Promo.city == client.city).order_by(Promo.created_at.desc())
            )
            promos = result.scalars().all()

            if promos:
                await message.answer("🎉 Актуальні акції у вашому місті:")
                for promo in promos:
                    if promo.image_file_id:
                        await message.answer_photo(
                            photo=promo.image_file_id,
                            caption=promo.text or "🛍 Акція",
                            parse_mode="Markdown"
                        )
                    else:
                        await message.answer(promo.text or "🛍 Акція")
            else:
                await message.answer("📭 На жаль, зараз немає активних акцій у вашому місті.")


@router.callback_query(F.data.startswith("choose_city:"))
async def process_city_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    city = callback.data.split(":")[1]

    # Не реєструємо, якщо адмін або суперадмін
    if user_id in SUPER_ADMIN_IDS:
        return await callback.message.answer(f"👋 Вітаю {user_name}\n Ви супер-адміністратор 😄")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()
        if admin:
            return await callback.message.answer(f"👋Привіт {user_name} \n✅ Ви адміністратор — .")

        # Реєстрація в clients
        result = await session.execute(select(Client).where(Client.telegram_id == user_id))
        client = result.scalar_one_or_none()

        if not client:
            new_client = Client(
                telegram_id=user_id,
                name=user_name,
                city=city
            )
            session.add(new_client)
            await session.commit()
        else:
            client.city = city
            await session.commit()

    greeting = f"👋 Привіт {user_name}!\n🧸 Вас вітає 'Мама ну купи' 🧸{city}"

    await callback.message.answer_photo(
        photo="https://optim.tildacdn.one/tild3330-6238-4464-b633-346436316437/-/resize/968x/-/format/webp/__.png.webp",
        caption=greeting,
        reply_markup=city_kb()
    )

    phone_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Надати номер телефону", request_contact=True)],
            [KeyboardButton(text="⏭ Пропустити")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await callback.message.answer("Будь ласка, поділіться номером телефону або натисніть «Пропустити»:",
                                  reply_markup=phone_kb)
    await callback.answer()


@router.message(F.contact)
async def handle_contact(message: Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Client).where(Client.telegram_id == user_id))
        client = result.scalar_one_or_none()

        if client:
            client.phone = phone
            await session.commit()

    await message.answer("✅ Дякуємо! Ваш номер збережено.", reply_markup=city_kb())


@router.message(F.text == "⏭ Пропустити")
async def skip_phone(message: Message):
    await message.answer("✅ Реєстрацію завершено без номера.", reply_markup=city_kb())
