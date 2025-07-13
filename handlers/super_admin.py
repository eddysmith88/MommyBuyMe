from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from db.models import Admin, Post, Promo, Client
from db.session import AsyncSessionLocal
from info import how_to_create, CITIES_LOCATION, VALID_CITIES
# from services.clients_export import export_clients_to_gsheet
from states.admin_states import AdminCreation, AdminDeletion
from filters.is_superadmin import IsSuperAdmin
from keyboard.keyboards import super_admin_menu, generate_post_action_kb, generate_promo_action_kb, cancel_kb
from states.superadmin_post_promo_states import CreatePostToCity, CreatePromoToCity, EditPromo, EditPost
from app_config import BOT_TOKEN

from datetime import datetime

import logging


logger = logging.getLogger(__name__)

main_router = Router()


BOTS_CONFIG = [
    {"token": BOT_TOKEN, "router": main_router, "name": "MainBot"},
]


router = Router()

# 🔐 Список дозволених супер-адмінів
SUPER_ADMIN_IDS = [887934499, 6539889022]


# VALID_CITIES = [
#     "Чернівці", "Чернігів", "Івано-Франківськ",
#     "Ужгород", "Запоріжжя", "Київ"
# ]

VALID_CITY_MAP = {city.lower().replace("-", "").replace(" ", ""): city for city in VALID_CITIES}


text = ("Що ви можете тут робити:\n"
      "- створити та видалити адміна;\n"
      "- оновити список клієнтів в гугл таблиці;\n"
      "- Створити новину;\n"
      "- Створити акцію\n"
      "- Акції видаляються автоматично після закінчення їх терміну\n"
      "Новини можна видаляти вручну")


# 📥 Вхід до меню супер-адміна
@router.callback_query(F.data == "admin", IsSuperAdmin())
async def show_admin_menu(callback: CallbackQuery):

    await callback.message.answer_photo(
        photo="https://optim.tildacdn.one/tild6430-3632-4466-a565-393138306265/-/resize/666x/-/format/webp/2_2.png.webp",
        caption=f"Меню адміністратора \n",
        parse_mode="Markdown",
        reply_markup=super_admin_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "how_to_create", IsSuperAdmin())
async def show_admin_menu2(callback: CallbackQuery):
    await callback.message.answer(f"{how_to_create}", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Створити адміна", callback_data="create_admin")]]
    ))
    await callback.answer()


# ▶️ Кнопка створення адміна
@router.callback_query(F.data == "create_admin", IsSuperAdmin())
async def create_admin_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "👤 Введіть Telegram ID та місто через пробіл (наприклад `123456789 Чернівці`):",
        reply_markup=cancel_kb()
    )
    await state.set_state(AdminCreation.waiting_for_admin_id_and_city)
    await callback.answer()


# 💾 Збереження адміна
@router.message(AdminCreation.waiting_for_admin_id_and_city, IsSuperAdmin())
async def admin_step1_get_name(message: Message, state: FSMContext):
    # if message.from_user.id not in SUPER_ADMIN_IDS:
    #     return

    try:
        telegram_id_str, city = message.text.strip().split(maxsplit=1)
        telegram_id = int(telegram_id_str)
    except:
        return await message.answer("⚠️ Формат неправильний. Введіть: `123456789 Чернівці`")

    # Перевірка на дубль
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        if result.scalar_one_or_none():
            await state.clear()
            return await message.answer("⚠️ Адмін із таким ID вже існує.")

    # Зберігаємо тимчасово у FSM
    await state.update_data(telegram_id=telegram_id, city=city)

    await message.answer("✍️ Тепер введіть ім’я адміна:", reply_markup=cancel_kb())
    await state.set_state(AdminCreation.waiting_for_admin_name)


@router.message(AdminCreation.waiting_for_admin_name, IsSuperAdmin())
async def admin_step2_save(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = data.get("telegram_id")
    city = data.get("city")
    name = message.text.strip()

    async with AsyncSessionLocal() as session:
        new_admin = Admin(
            telegram_id=telegram_id,
            name=name,
            city=city
        )
        session.add(new_admin)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Адмін *{name}* для міста *{city}* створений.", reply_markup=super_admin_menu(), parse_mode="Markdown")



# ▶️ Кнопка видалення адміна
@router.callback_query(F.data == "delete_admin", IsSuperAdmin())
async def delete_admin_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🗑️ Введіть Telegram ID адміна, якого треба видалити:", reply_markup=cancel_kb())
    await state.set_state(AdminDeletion.waiting_for_admin_id)
    await callback.answer()

# 🧹 Видалення адміна
@router.message(AdminDeletion.waiting_for_admin_id, IsSuperAdmin())
async def delete_admin_confirm(message: Message, state: FSMContext):

    try:
        telegram_id = int(message.text.strip())
    except:
        return await message.answer("⚠️ Введіть лише числовий Telegram ID")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        admin = result.scalar_one_or_none()

        if not admin:
            await state.clear()
            return await message.answer("❌ Адміна з таким ID не знайдено.")

        await session.delete(admin)
        await session.commit()

    await state.clear()
    await message.answer("✅ Адмін видалений.", reply_markup=super_admin_menu())

# ❌ Скасування дії
@router.callback_query(F.data == "cancel", IsSuperAdmin())
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Дію скасовано.", reply_markup=super_admin_menu())
    await callback.answer()

# 🔙 Назад до меню
@router.callback_query(F.data == "admin_back", IsSuperAdmin())
async def admin_back(callback: CallbackQuery):
    await callback.message.answer("🔙 Повернення в меню:", reply_markup=super_admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_list", IsSuperAdmin())
async def list_admins(callback: CallbackQuery):

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin))
        admins = result.scalars().all()

    if not admins:
        await callback.message.answer("📭 Адміністраторів ще немає.")
        return await callback.answer()

    await callback.answer()  # Закриваємо спінер

    for admin in admins:
        text = (
            f"👤 *{admin.name}*\n"
            f"ID: `{admin.telegram_id}`\n"
            f"Місто: {admin.city or '🌐 (супер-адмін)'}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔢 Скопіювати ID",
                    callback_data=f"copy_id:{admin.telegram_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Видалити",
                    callback_data=f"remove_admin:{admin.telegram_id}"
                )
            ]
        ])

        await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data.startswith("copy_id:"), IsSuperAdmin())
async def copy_admin_id(callback: CallbackQuery):
    telegram_id = callback.data.split(":")[1]
    await callback.message.answer(f"`{telegram_id}`", parse_mode="Markdown")
    await callback.answer("ID скопійовано ✅")


@router.callback_query(F.data.startswith("remove_admin:"), IsSuperAdmin())
async def confirm_admin_removal(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split(":")[1])

    # 🔒 Не можна видаляти себе
    if callback.from_user.id == telegram_id:
        return await callback.answer("❗ Ви не можете видалити себе", show_alert=True)

    # Зберігаємо ID адміна для підтвердження
    await state.update_data(remove_id=telegram_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так", callback_data="confirm_delete"),
            InlineKeyboardButton(text="❌ Ні", callback_data="cancel_delete")
        ]
    ])

    await callback.message.edit_text(
        f"❗ Ви точно хочете видалити адміна з ID `{telegram_id}`?",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete")
async def delete_admin_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    telegram_id = data.get("remove_id")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        admin = result.scalar_one_or_none()

        if not admin:
            await state.clear()
            return await callback.message.edit_text("❌ Адміна не знайдено.")

        await session.delete(admin)
        await session.commit()

    await state.clear()
    await callback.message.edit_text("✅ Адмін успішно видалений.")
    await callback.answer("Видалено ✅")


@router.callback_query(F.data == "cancel_delete")
async def cancel_admin_delete(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Видалення скасовано.")
    await callback.answer("Скасовано")

# TODO СТВОРИТИ ТАБЛИЦІ
#### SEND TO GOOGLE SHEETS
# @router.callback_query(F.data == "export_clients", IsSuperAdmin())
# async def export_clients_callback(callback: CallbackQuery):
#     await callback.message.answer("📤 Експорт клієнтів...")
#     await export_clients_to_gsheet()
#     await callback.message.answer("✅ Дані експортовано у Google Sheets!")
#     await callback.answer()


### CREATE POST AND PROMO FROM SUPER ADMIN
@router.callback_query(IsSuperAdmin(), F.data == "create_post_to_city")
async def create_post_to_city(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        f"🏙 Введіть назву міста для посту:\n Бердичів, Дніпро, Житомир, Ізмаїл,"
                                  "Запоріжжя, Івано-Франківськ, Львів, Кривій Ріг, Кропивницький, Луцьк, Одеса, "
                                  "Первомайськ, Рівне, Ужгород, Київ, Харків, Чернігів",
        reply_markup=cancel_kb()
    )
    await state.set_state(CreatePostToCity.waiting_for_city)
    await callback.answer()


@router.message(CreatePostToCity.waiting_for_city)
async def receive_post_city(message: Message, state: FSMContext):
    user_input = message.text.strip().lower().replace("-", "").replace(" ", "")
    normalized_city = VALID_CITY_MAP.get(user_input)

    if not normalized_city:
        await message.answer("❌ Невірна назва міста. Спробуйте ще раз:", reply_markup=cancel_kb())
        return

    await state.update_data(city=normalized_city)
    await message.answer("📝 Введіть текст новини:", reply_markup=cancel_kb())
    await state.set_state(CreatePostToCity.waiting_for_text)


@router.message(CreatePostToCity.waiting_for_text)
async def receive_post_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    await message.answer("📷 Надішліть фото (або пропустіть)", reply_markup=cancel_kb())
    await state.set_state(CreatePostToCity.waiting_for_photo)


@router.message(CreatePostToCity.waiting_for_photo)
async def receive_post_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.photo[-1].file_id if message.photo else None

    post = Post(
        city=data['city'],
        text=data['text'],
        image_file_id=file_id,
        created_at=datetime.utcnow()
    )

    async with AsyncSessionLocal() as session:
        session.add(post)
        await session.commit()

    await state.clear()

    await message.answer("✅ Пост створено!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Надіслати всім", callback_data=f"send_to_all:{post.id}")],
        [InlineKeyboardButton(text="Надіслати на місто", callback_data=f"send_to_city:{post.id}")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="admin")]
    ]))


#### SEND POST
@router.callback_query(F.data.startswith("send_to_all:"))
async def send_post_to_all(callback: CallbackQuery):
    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()
        if not post:
            return await callback.message.answer("⚠️ Пост не знайдено")

        result = await session.execute(select(Client.telegram_id))
        client_ids = result.scalars().all()

    for client_id in client_ids:
        try:
            if post.image_file_id:
                await callback.bot.send_photo(chat_id=client_id, photo=post.image_file_id, caption=post.text)
            else:
                await callback.bot.send_message(chat_id=client_id, text=post.text)
        except Exception:
            continue

    await callback.message.answer("✅ Пост надіслано всім користувачам.")
    await callback.answer()


@router.callback_query(F.data.startswith("send_to_city:"))
async def send_post_to_city(callback: CallbackQuery):
    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()
        if not post:
            return await callback.message.answer("⚠️ Пост не знайдено")

        result = await session.execute(
            select(Client.telegram_id).where(Client.city == post.city)
        )
        client_ids = result.scalars().all()

    for client_id in client_ids:
        try:
            if post.image_file_id:
                await callback.bot.send_photo(chat_id=client_id, photo=post.image_file_id, caption=post.text)
            else:
                await callback.bot.send_message(chat_id=client_id, text=post.text)
        except Exception:
            continue

    await callback.message.answer(f"✅ Пост надіслано в місто {post.city}.")
    await callback.answer()



# --- АКЦІЯ ---
@router.callback_query(IsSuperAdmin(), F.data == "create_promo_to_city")
async def create_promo_to_city(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🏙 Введіть назву міста для акції:\n Бердичів, Дніпро, Житомир, Ізмаїл,"
                                  "Запоріжжя, Івано-Франківськ, Львів, Кривій Ріг, Кропивницький, Луцьк, Одеса, "
                                  "Первомайськ, Рівне, Ужгород, Київ, Харків, Чернігів",
        reply_markup=cancel_kb()
    )
    await state.set_state(CreatePromoToCity.waiting_for_city)
    await callback.answer()


@router.message(CreatePromoToCity.waiting_for_city)
async def receive_promo_city(message: Message, state: FSMContext):
    user_input = message.text.strip().lower().replace("-", "").replace(" ", "")
    normalized_city = VALID_CITY_MAP.get(user_input)

    if not normalized_city:
        await message.answer("❌ Невірна назва міста. Спробуйте ще раз:", reply_markup=cancel_kb())
        return

    await state.update_data(city=normalized_city)
    await message.answer("📝 Введіть текст акції:", reply_markup=cancel_kb())
    await state.set_state(CreatePromoToCity.waiting_for_text)


@router.message(CreatePromoToCity.waiting_for_text)
async def receive_promo_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    await message.answer("📷 Надішліть фото (або пропустіть)", reply_markup=cancel_kb())
    await state.set_state(CreatePromoToCity.waiting_for_photo)


@router.message(CreatePromoToCity.waiting_for_photo)
async def receive_promo_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id if message.photo else None
    await state.update_data(image_file_id=file_id)
    await message.answer("📅 Введіть дату завершення акції у форматі дд.мм.рррр:", reply_markup=cancel_kb())
    await state.set_state(CreatePromoToCity.waiting_for_date)


@router.message(CreatePromoToCity.waiting_for_date)
async def receive_promo_date(message: Message, state: FSMContext):
    try:
        date_expire = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        return await message.answer("⚠️ Невірний формат. Введіть дату як дд.мм.рррр", reply_markup=cancel_kb())

    data = await state.get_data()

    promo = Promo(
        city=data["city"],
        text=data["text"],
        image_file_id=data.get("image_file_id"),
        created_at=datetime.utcnow(),
        date_expire=date_expire
    )

    async with AsyncSessionLocal() as session:
        session.add(promo)
        await session.commit()

    await state.clear()

    await message.answer("✅ Акцію успішно створено!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Надіслати акцію всім", callback_data=f"send_promo_all:{promo.id}")],
        [InlineKeyboardButton(text="Надіслати на окреме місто", callback_data=f"send_promo_city:{promo.id}")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="admin")]
    ]))



#### SEND PROMO TO ALL

@router.callback_query(F.data.startswith("send_promo_all:"))
async def send_promo_to_all(callback: CallbackQuery):
    promo_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).where(Promo.id == promo_id))
        promo = result.scalar_one_or_none()
        if not promo:
            return await callback.message.answer("⚠️ Акцію не знайдено.")

        result = await session.execute(select(Client.telegram_id))
        client_ids = result.scalars().all()

    for client_id in client_ids:
        try:
            caption = f"{promo.text or '—'}\n🗓 До: {promo.date_expire.strftime('%d.%m.%Y')}"
            if promo.image_file_id:
                await callback.bot.send_photo(chat_id=client_id, photo=promo.image_file_id, caption=caption)
            else:
                await callback.bot.send_message(chat_id=client_id, text=caption)
        except Exception:
            continue

    await callback.message.answer("✅ Акцію надіслано всім клієнтам.")
    await callback.answer()


@router.callback_query(F.data.startswith("send_promo_city:"))
async def send_promo_to_city(callback: CallbackQuery):
    promo_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).where(Promo.id == promo_id))
        promo = result.scalar_one_or_none()
        if not promo:
            return await callback.message.answer("⚠️ Акцію не знайдено.")

        result = await session.execute(select(Client.telegram_id).where(Client.city == promo.city))
        client_ids = result.scalars().all()

    for client_id in client_ids:
        try:
            caption = f"{promo.text or '—'}\n🗓 До: {promo.date_expire.strftime('%d.%m.%Y')}"
            if promo.image_file_id:
                await callback.bot.send_photo(chat_id=client_id, photo=promo.image_file_id, caption=caption)
            else:
                await callback.bot.send_message(chat_id=client_id, text=caption)
        except Exception:
            continue

    await callback.message.answer(f"✅ Акцію надіслано у місто {promo.city}.")
    await callback.answer()

