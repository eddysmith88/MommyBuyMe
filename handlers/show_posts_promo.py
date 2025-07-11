from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from db.models import Admin, Post, Promo, Client
from db.session import AsyncSessionLocal
from info import CITIES_LOCATION, VALID_CITIES
from filters.is_superadmin import IsSuperAdmin
from keyboard.keyboards import generate_promo_action_kb, cancel_kb, get_posts_pagination_kb, get_pagination_kb
from states.superadmin_post_promo_states import CreatePostToCity, CreatePromoToCity, EditPromo, EditPost


from datetime import datetime

import logging


router = Router()


SUPER_ADMIN_IDS = [887934499, 6539889022,]


VALID_CITY_MAP = {city.lower().replace("-", "").replace(" ", ""): city for city in VALID_CITIES}

POSTS_PER_PAGE = 3

def get_post_caption(post):
    return (
        f"📍 Місто: *{post.city}*\n"
        f"📝 {post.text or '—'}\n"
        f"🕒 {post.created_at.strftime('%d.%m.%Y %H:%M')}"
    )

# POST BLOCK
@router.callback_query(IsSuperAdmin(), F.data == "show_posts_button")
async def choose_post_view_option(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Усі новини", callback_data="view_all_posts")],
        [InlineKeyboardButton(text="🏙 По містах", callback_data="choose_post_city")]
    ])
    await callback.message.answer("Оберіть тип перегляду:", reply_markup=kb)
    await callback.answer()


@router.callback_query(IsSuperAdmin(), F.data.startswith("view_all_posts"))
async def view_all_posts(callback: CallbackQuery):
    # Парсимо номер сторінки
    page = 1
    if ":" in callback.data:
        try:
            page = int(callback.data.split(":")[1])
        except Exception:
            page = 1

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).order_by(Post.created_at.desc()))
        posts = result.scalars().all()

    if not posts:
        await callback.message.answer("📭 Ще немає жодної новини.")
        return await callback.answer()

    total = len(posts)
    total_pages = (total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
    page = max(1, min(page, total_pages))

    start = (page - 1) * POSTS_PER_PAGE
    end = start + POSTS_PER_PAGE
    page_posts = posts[start:end]

    for post in page_posts:
        caption = get_post_caption(post)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_post:{post.id}"),
                InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"delete_post:{post.id}")
            ]
        ])
        try:
            if post.image_file_id:
                await callback.message.answer_photo(
                    photo=post.image_file_id,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=kb
                )
            else:
                await callback.message.answer(
                    caption,
                    parse_mode="Markdown",
                    reply_markup=kb
                )
        except Exception as e:
            await callback.message.answer(
                f"⚠️ Помилка з відображенням поста (ID={post.id}): {str(e)}",
                reply_markup=kb
            )

    pag_kb = get_posts_pagination_kb(page, total_pages, "view_all_posts")
    if pag_kb:
        await callback.message.answer(f"Сторінка {page}/{total_pages}", reply_markup=pag_kb)
    await callback.answer()


@router.callback_query(F.data == "choose_post_city")
async def choose_city_for_posts(callback: CallbackQuery):
    buttons = [
        [InlineKeyboardButton(text=city, callback_data=f"view_posts_city:{city}")]
        for city in VALID_CITIES
    ]
    await callback.message.answer("Оберіть місто:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("view_posts_city:"))
async def view_posts_by_city(callback: CallbackQuery):
    parts = callback.data.split(":")
    city = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.city == city).order_by(Post.created_at.desc())
        )
        posts = result.scalars().all()

    if not posts:
        return await callback.message.answer(f"📭 У місті {city} ще немає новин")

    total = len(posts)
    total_pages = (total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
    page = max(1, min(page, total_pages))

    start = (page - 1) * POSTS_PER_PAGE
    end = start + POSTS_PER_PAGE
    page_posts = posts[start:end]

    for post in page_posts:
        caption = get_post_caption(post)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_post:{post.id}"),
                InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"delete_post:{post.id}")
            ]
        ])
        try:
            if post.image_file_id:
                await callback.message.answer_photo(
                    photo=post.image_file_id,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=kb
                )
            else:
                await callback.message.answer(
                    caption,
                    parse_mode="Markdown",
                    reply_markup=kb
                )
        except Exception as e:
            await callback.message.answer(
                f"⚠️ Помилка з відображенням поста (ID={post.id}): {str(e)}",
                reply_markup=kb
            )

    pag_kb = get_posts_pagination_kb(page, total_pages, "view_posts_city", city)
    if pag_kb:
        await callback.message.answer(f"Сторінка {page}/{total_pages} | {city}", reply_markup=pag_kb)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_post:"))
async def delete_post(callback: CallbackQuery):
    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            return await callback.message.answer("❌ Пост не знайдено.")

        await session.delete(post)
        await session.commit()

    await callback.message.answer("✅ Пост успішно видалено.")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_post:"))
async def start_edit_post(callback: CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split(":")[1])
    await state.update_data(post_id=post_id)

    await callback.message.answer("📝 Введіть новий текст посту:", reply_markup=cancel_kb())
    await state.set_state(EditPost.waiting_for_text)
    await callback.answer()


@router.message(EditPost.waiting_for_text)
async def edit_post_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    await message.answer("📷 Надішліть нове фото (або пропустіть)", reply_markup=cancel_kb())
    await state.set_state(EditPost.waiting_for_photo)


@router.message(EditPost.waiting_for_photo)
async def edit_post_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    image_file_id = None

    if message.photo:
        photo = message.photo[-1]
        image_file_id = photo.file_id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == data["post_id"]))
        post = result.scalar_one_or_none()

        if not post:
            return await message.answer("❌ Пост не знайдено.")

        post.text = data["text"]
        if image_file_id:
            post.image_file_id = image_file_id

        await session.commit()

    await state.clear()
    await message.answer("✅ Пост успішно оновлено.")


# PROMO BLOCK
@router.callback_query(IsSuperAdmin(), F.data == "show_promo_button")
async def show_promo_button_handler(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗂 Усі акції", callback_data="view_all_promos")],
        [InlineKeyboardButton(text="🏢 По містах", callback_data="choose_promo_city")]
    ])
    await callback.message.answer("Оберіть як переглянути акції:", reply_markup=kb)
    await callback.answer()


PROMOS_PER_PAGE = 5

def get_promo_caption(promo):
    return f"{promo.text or '—'}\n🗓 До: {promo.date_expire.strftime('%d.%m.%Y')}"

@router.callback_query(F.data.startswith("view_all_promos"))
async def view_all_promos(callback: CallbackQuery):
    # Витягуємо сторінку
    page = 1
    if ":" in callback.data:
        try:
            page = int(callback.data.split(":")[1])
        except:
            page = 1

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).order_by(Promo.created_at.desc()))
        promos = result.scalars().all()

    if not promos:
        return await callback.message.answer("📭 Немає жодної акції")

    total = len(promos)
    total_pages = (total + PROMOS_PER_PAGE - 1) // PROMOS_PER_PAGE
    page = max(1, min(page, total_pages))

    start = (page - 1) * PROMOS_PER_PAGE
    end = start + PROMOS_PER_PAGE
    page_promos = promos[start:end]

    # Під кожною сторінкою - пагінація
    for promo in page_promos:
        caption = get_promo_caption(promo)
        try:
            if promo.image_file_id:
                await callback.message.answer_photo(
                    photo=promo.image_file_id,
                    caption=caption,
                    reply_markup=generate_promo_action_kb(promo.id)
                )
            else:
                await callback.message.answer(caption, reply_markup=generate_promo_action_kb(promo.id))
        except Exception as e:
            logging.warning(f"❌ Помилка зображення акції ID={promo.id}: {e}")
            await callback.message.answer(caption, reply_markup=generate_promo_action_kb(promo.id))

    kb = get_pagination_kb(page, total_pages, "view_all_promos")
    if kb:
        await callback.message.answer(f"Сторінка {page}/{total_pages}", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "choose_promo_city")
async def choose_promo_city(callback: CallbackQuery):
    buttons = [[InlineKeyboardButton(text=city, callback_data=f"view_promos_city:{city}")]
               for city in CITIES_LOCATION.keys()]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("Оберіть місто для перегляду акцій:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("view_promos_city:"))
async def view_promos_by_city(callback: CallbackQuery):
    # Витягуємо місто і сторінку
    parts = callback.data.split(":")
    city = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).where(Promo.city == city).order_by(Promo.created_at.desc()))
        promos = result.scalars().all()

    if not promos:
        return await callback.message.answer(f"📭 У місті {city} ще немає акцій")

    total = len(promos)
    total_pages = (total + PROMOS_PER_PAGE - 1) // PROMOS_PER_PAGE
    page = max(1, min(page, total_pages))

    start = (page - 1) * PROMOS_PER_PAGE
    end = start + PROMOS_PER_PAGE
    page_promos = promos[start:end]

    for promo in page_promos:
        caption = get_promo_caption(promo)
        try:
            if promo.image_file_id:
                await callback.message.answer_photo(
                    photo=promo.image_file_id,
                    caption=caption,
                    reply_markup=generate_promo_action_kb(promo.id)
                )
            else:
                await callback.message.answer(caption, reply_markup=generate_promo_action_kb(promo.id))
        except Exception as e:
            logging.warning(f"❌ Помилка зображення акції ID={promo.id}: {e}")
            await callback.message.answer(caption, reply_markup=generate_promo_action_kb(promo.id))

    kb = get_pagination_kb(page, total_pages, "view_promos_city", city)
    if kb:
        await callback.message.answer(f"Сторінка {page}/{total_pages} | {city}", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_promo:"))
async def delete_promo(callback: CallbackQuery):
    promo_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).where(Promo.id == promo_id))
        promo = result.scalar_one_or_none()

        if not promo:
            return await callback.message.answer("❌ Акцію не знайдено.")

        await session.delete(promo)
        await session.commit()

    await callback.message.answer("✅ Акцію успішно видалено.")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_promo:"))
async def start_edit_promo(callback: CallbackQuery, state: FSMContext):
    promo_id = int(callback.data.split(":")[1])
    await state.update_data(promo_id=promo_id)

    await callback.message.answer("📝 Введіть новий текст акції:", reply_markup=cancel_kb())
    await state.set_state(EditPromo.waiting_for_text)
    await callback.answer()


@router.message(EditPromo.waiting_for_text)
async def edit_promo_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    await message.answer("📷 Надішліть нове фото (або пропустіть)", reply_markup=cancel_kb())
    await state.set_state(EditPromo.waiting_for_photo)


@router.message(EditPromo.waiting_for_photo)
async def edit_promo_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    image_file_id = None

    if message.photo:
        photo = message.photo[-1]
        image_file_id = photo.file_id

    await state.update_data(image_file_id=image_file_id)
    await message.answer("📅 Введіть нову дату завершення акції у форматі дд.мм.рррр:", reply_markup=cancel_kb())
    await state.set_state(EditPromo.waiting_for_date)


@router.message(EditPromo.waiting_for_date)
async def edit_promo_date(message: Message, state: FSMContext):
    try:
        date_expire = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        return await message.answer("⚠️ Невірний формат. Введіть дату як дд.мм.рррр", reply_markup=cancel_kb())

    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).where(Promo.id == data["promo_id"]))
        promo = result.scalar_one_or_none()

        if not promo:
            return await message.answer("❌ Акцію не знайдено.")

        promo.text = data["text"]
        promo.date_expire = date_expire

        if data.get("image_file_id"):
            promo.image_file_id = data["image_file_id"]

        await session.commit()

    await state.clear()
    await message.answer("✅ Акцію успішно оновлено.")
