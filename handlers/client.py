"""
Обробник для меню клієнтів
"""

import logging


from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from db.models import Client, Post, Promo
from db.session import AsyncSessionLocal
from filters.is_superadmin import IsSuperAdmin
from info import (about_info, question_1, question_5, question_2, question_3, question_4,
                  question_6, answer_1, answer_6, answer_2, answer_3, answer_4, answer_5)
from keyboard.keyboards import generate_promo_action_kb, generate_post_action_kb

router = Router()


PROMOS_PER_PAGE = 5


def promo_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"promo_page:{page - 1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="➡️ Далі", callback_data=f"promo_page:{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


def generate_posts_pagination_kb(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"posts_page:{current_page - 1}"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="➡️ Далі", callback_data=f"posts_page:{current_page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


@router.callback_query(F.data == "news")
async def news_menu(callback: CallbackQuery):
    await callback.message.answer("Новини та акції", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Новини", callback_data="show_my_posts"),
         InlineKeyboardButton(text="Наші акції", callback_data="show_my_promos")],
    ]))
    await callback.answer()


@router.callback_query(F.data == "about")
async def about_information(callback: CallbackQuery):
    await callback.message.answer(f"{about_info}")
    await callback.answer()


@router.callback_query(F.data == "faq")
async def questions(callback: CallbackQuery):
    await callback.message.answer(f"Ось найчастіше задавані питання, можливо тут є Ваше",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                      [InlineKeyboardButton(text=question_1, callback_data="answer_1")],
                                      [InlineKeyboardButton(text=question_2, callback_data="answer_2")],
                                      [InlineKeyboardButton(text=question_3, callback_data="answer_3")],
                                      [InlineKeyboardButton(text=question_4, callback_data="answer_4")],
                                      [InlineKeyboardButton(text=question_5, callback_data="answer_5")],
                                      [InlineKeyboardButton(text=question_6, callback_data="answer_6")],
                                  ]))
    await callback.answer()


@router.callback_query(F.data.in_({"answer_1", "answer_2", "answer_3", "answer_4", "answer_5", "answer_6"}))
async def handle_faq_answers(callback: CallbackQuery):
    answers = {
        "answer_1": answer_1,
        "answer_2": answer_2,
        "answer_3": answer_3,
        "answer_4": answer_4,
        "answer_5": answer_5,
        "answer_6": answer_6,
    }

    answer_text = answers.get(callback.data, "❓ Невідоме питання")
    await callback.message.answer(answer_text)
    await callback.answer()


@router.callback_query(F.data == "support")
async def support_call(callback: CallbackQuery):
    await callback.message.answer("Номер тех. підтримки: +380 68 150 23 09")
    await callback.answer()


@router.callback_query(F.data == "partner")
async def partnership(callback: CallbackQuery):
    await callback.message.answer(f"https://vending.in.ua/#contact\n")
    await callback.answer()


# SHOW POSTS
@router.callback_query(F.data == "show_my_posts")
async def show_posts_list(callback: CallbackQuery, state: FSMContext):
    await show_posts_page(callback, state, page=1)


@router.callback_query(F.data.startswith("posts_page:"))
async def show_posts_page(callback: CallbackQuery, state: FSMContext, page: int | None = None):
    if page is None:
        page = int(callback.data.split(":")[1])

    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Client).where(Client.telegram_id == user_id))
        client = result.scalar_one_or_none()

        if not client:
            return await callback.message.answer("⛔ Вас не знайдено в базі")

        posts_result = await session.execute(
            select(Post).where(Post.city == client.city).order_by(Post.created_at.desc())
        )
        posts = posts_result.scalars().all()

    if not posts:
        return await callback.message.answer("📭 У вашому місті ще немає постів")

    per_page = 5
    total_pages = (len(posts) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    current_posts = posts[start:end]

    for post in current_posts:
        caption = post.text or "—"
        try:
            if post.image_file_id:
                await callback.message.answer_photo(
                    photo=post.image_file_id,  # ✅ напряму file_id
                    caption=caption
                )
            else:
                await callback.message.answer(caption)
        except Exception as e:
            logging.warning(f"❌ Помилка зображення в пості ID={post.id}: {e}")
            await callback.message.answer(caption)

        if await IsSuperAdmin()(callback):
            await callback.message.answer("⚙️ Дії з постом:", reply_markup=generate_post_action_kb(post.id))

    keyboard = generate_posts_pagination_kb(current_page=page, total_pages=total_pages)
    if keyboard:
        await callback.message.answer("🔄 Переглянути більше:", reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data == "show_my_promos")
async def start_show_promos(callback: CallbackQuery):
    await show_promos_page(callback, page=1)


@router.callback_query(F.data.startswith("promo_page:"))
async def paginate_promos(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await show_promos_page(callback, page)

async def show_promos_page(callback: CallbackQuery, page: int):
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Client).where(Client.telegram_id == user_id))
        client = result.scalar_one_or_none()

        if not client:
            return await callback.message.answer("⛔ Вас не знайдено в базі")

        promos_result = await session.execute(
            select(Promo)
            .where(Promo.city == client.city)
            .order_by(Promo.created_at.desc())
        )
        promos = promos_result.scalars().all()

        if not promos:
            return await callback.message.answer("📭 У вашому місті ще немає акцій")

        total_pages = (len(promos) + PROMOS_PER_PAGE - 1) // PROMOS_PER_PAGE
        start = (page - 1) * PROMOS_PER_PAGE
        end = start + PROMOS_PER_PAGE
        page_promos = promos[start:end]

        for promo in page_promos:
            caption = f"{promo.text or '—'}\n🗓 До: {promo.date_expire.strftime('%d.%m.%Y')}"
            try:
                if promo.image_file_id:
                    await callback.message.answer_photo(
                        photo=promo.image_file_id,  # ✅ напряму file_id з Telegram
                        caption=caption
                    )
                else:
                    await callback.message.answer(caption)
            except Exception as e:
                logging.warning(f"❌ Помилка зображення в акції ID={promo.id}: {e}")
                await callback.message.answer(caption)

            if await IsSuperAdmin()(callback):
                await callback.message.answer("⚙️ Дії з акцією:", reply_markup=generate_promo_action_kb(promo.id))

        nav_kb = promo_pagination_kb(page, total_pages)
        if nav_kb:
            await callback.message.answer("⬇️ Перегортайте сторінки ⬇️", reply_markup=nav_kb)

    await callback.answer()
