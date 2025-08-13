"""
Обробники Адмінів
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from db.session import AsyncSessionLocal
from db.models import Admin, Post, Promo, Client

from datetime import datetime

from filters.is_admin import IsAdmin
from info import SUPER_ADMIN_IDS
from states.post_states import PostCreation, RejectPost, RejectPromoFSM
from states.admin_states import PromoCreation
from keyboard.keyboards import send_post_kb, send_promo_kb, cancel_kb, check_post_kb
from states.superadmin_post_promo_states import RejectPromo



router = Router()
# Фільтри
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# Пост блок початок
@router.callback_query(F.data == "create_post")
async def start_create_post(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == callback.from_user.id)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            return await callback.message.answer("⛔ Ви не є адміном")

    await state.clear()
    await state.set_state(PostCreation.waiting_for_text)
    await callback.message.answer("📝 Введіть текст поста:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(PostCreation.waiting_for_text)
async def receive_post_text(message: Message, state: FSMContext):
    text = message.text
    if not text:
        return await message.answer("⚠️ Введіть текст поста")

    await state.update_data(text=text)
    await state.set_state(PostCreation.waiting_for_photo)

    await message.answer("📷 Надішліть фото для поста (або натисніть «Пропустити»)",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Пропустити", callback_data="skip_photo")]
                         ]))


@router.message(PostCreation.waiting_for_photo)
async def receive_post_photo(message: Message, state: FSMContext):
    if not message.photo:
        return await message.answer("⚠️ Надішліть фото або натисніть кнопку «Пропустити»")

    data = await state.get_data()
    text = data.get("text")
    photo = message.photo[-1].file_id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == message.from_user.id)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            return await message.answer("⛔ Ви не є адміном")

        post = Post(
            city=admin.city,
            text=text,
            image_file_id=photo,
            author_id=admin.telegram_id,  # ✅ Додаємо ID автора
            created_at=datetime.utcnow()
        )
        session.add(post)
        await session.commit()

    await state.clear()
    await message.answer("✅ Пост створено", reply_markup=check_post_kb())


@router.callback_query(F.data == "skip_photo")
async def skip_post_photo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == callback.from_user.id)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            return await callback.message.answer("⛔ Ви не є адміном")

        post = Post(
            city=admin.city,
            text=text,
            image_file_id=None,
            author_id=admin.telegram_id,  # ✅ Додаємо ID автора
            created_at=datetime.utcnow()
        )
        session.add(post)
        await session.commit()

    await state.clear()
    await callback.message.answer("✅ Пост створено без фото", reply_markup=check_post_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_post:"))
async def edit_post_start(callback: CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split(":")[1])
    await state.update_data(mode="edit", post_id=post_id)
    await state.set_state(PostCreation.waiting_for_text)
    await callback.message.answer(
        "✏️ Введіть новий текст поста (можна з фото):",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_post:"))
async def delete_post(callback: CallbackQuery):
    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if post:
            await session.delete(post)
            await session.commit()

    await callback.message.answer("🗑️ Пост видалено")
    await callback.answer()


@router.callback_query(F.data == "check_post")
async def show_latest_post(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        # Перевірка, чи користувач є адміном
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()

        if not admin:
            return await callback.message.answer("❌ Вас не знайдено серед адміністраторів.")

        city_name = admin.city

        # Отримати останній пост для цього міста
        result = await session.execute(
            select(Post).where(Post.city == city_name).order_by(Post.created_at.desc())
        )
        post = result.scalars().first()

    if not post:
        return await callback.message.answer("📭 Немає постів")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_post:{post.id}")],
        [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_post:{post.id}")],
        [InlineKeyboardButton(text="📤 Відправити на перевірку", callback_data="send_to_co")]
    ])

    if post.image_file_id:
        await callback.message.answer_photo(
            photo=post.image_file_id,
            caption=post.text,
            reply_markup=kb
        )
    else:
        await callback.message.answer(post.text, reply_markup=kb)

    await callback.answer()



@router.callback_query(F.data == "send_to_co")
async def send_to_coord(callback: CallbackQuery, state: FSMContext):
    from aiogram import Bot
    bot: Bot = callback.bot
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        # Перевірка, що це адмін
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()
        if not admin:
            return await callback.message.answer("⛔ Ви не адмін")

        # Останній пост цього міста
        result = await session.execute(
            select(Post).where(Post.city == admin.city).order_by(Post.created_at.desc())
        )
        post = result.scalars().first()
        if not post:
            return await callback.message.answer("❌ Немає постів для відправки")

        # Кнопки супер-адміна
        kb = send_post_kb(post)

        success = 0
        for sa_id in SUPER_ADMIN_IDS:
            try:
                if post.image_file_id:
                    await bot.send_photo(
                        sa_id,
                        photo=post.image_file_id,
                        caption=f"🔔 Пост з міста *{post.city}*:\n\n{post.text}",
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                else:
                    await bot.send_message(
                        sa_id,
                        text=f"🔔 Пост з міста *{post.city}*:\n\n{post.text}",
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                success += 1
            except Exception as e:
                print(f"❌ Не вдалося надіслати супер-адміну {sa_id}: {e}")
                continue

    await callback.message.answer(f"✅ Пост надіслано {success} супер-адміну(ам)")
    await callback.answer()



@router.callback_query(F.data.startswith("reject_post:"))
async def reject_post(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) != 3:
        return await callback.message.answer("⚠️ Невірний формат callback_data.")

    post_id = int(parts[1])
    author_id = int(parts[2])  # ← автор, який отримує повідомлення

    await state.update_data(post_id=post_id, author_id=author_id)
    await state.set_state(RejectPost.waiting_for_comment)

    await callback.message.answer("❌ Введіть причину відхилення поста:")
    await callback.answer()


@router.message(RejectPost.waiting_for_comment)
async def handle_reject_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    post_id = data.get("post_id")
    author_id = data.get("author_id")
    comment = message.text.strip()

    if not post_id or not author_id:
        await state.clear()
        return await message.answer("❌ Дані для відхилення поста відсутні.")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            await state.clear()
            return await message.answer("❌ Пост не знайдено")

        try:
            await message.bot.send_message(
                author_id,
                f"❌ Ваш пост було відхилено.\n\n📄 Причина: {comment}"
            )
            await message.answer("✅ Причину відхилення надіслано автору.")
        except Exception as e:
            await message.answer(f"⚠️ Не вдалося надіслати повідомлення автору: {e}")

    await state.clear()


@router.callback_query(F.data == "list_posts")
async def list_posts(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()

        if not admin:
            return await callback.message.answer("⛔ Ви не адмін")

        posts_result = await session.execute(
            select(Post).where(Post.city == admin.city).order_by(Post.created_at.desc())
        )
        posts = posts_result.scalars().all()

        if not posts:
            return await callback.message.answer("📭 У вашому місті ще немає постів")

        for post in posts:
            caption = f"📝 *Пост:*\n{post.text or '-'}\n🕒 *Дата:* {post.created_at.strftime('%d.%m.%Y %H:%M')}"

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
                    f"⚠️ Не вдалося відобразити зображення поста ID {post.id}. Причина: {str(e)}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_post:{post.id}")]
                    ])
                )

    await callback.answer()



@router.callback_query(F.data.startswith("delete_post:"))
async def delete_post(callback: CallbackQuery):
    post_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            return await callback.message.answer("❌ Пост не знайдено")

        await session.delete(post)
        await session.commit()

    await callback.message.answer("🗑️ Пост видалено")
    await callback.answer()

# Промо блок
@router.callback_query(F.data == "create_promo")
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📝 Введіть текст акційної пропозиції (можна з фото):",
        reply_markup=cancel_kb()
    )
    await state.update_data(mode="create")  # режим створення
    await state.set_state(PromoCreation.waiting_for_text)
    await callback.answer()

@router.message(PromoCreation.waiting_for_text)
async def promo_text_step(message: Message, state: FSMContext):
    text = message.caption or message.text
    photo = message.photo[-1].file_id if message.photo else None

    await state.update_data(text=text, photo=photo)
    await state.set_state(PromoCreation.waiting_for_expire_date)
    await message.answer("📅 Введіть дату завершення у форматі: дд.мм.рррр")

async def save_promo_to_db(city_name: str, text: str, photo: str | None, date_expire: str, mode: str,
                           author_id: int):
    async with AsyncSessionLocal() as session:
        if mode == "edit":
            result = await session.execute(
                select(Promo)
                .where(Promo.city == city_name)
                .order_by(Promo.created_at.desc())
            )
            promo = result.scalars().first()

            if promo:
                promo.text = text
                promo.image_file_id = photo
                promo.date_expire = date_expire
                promo.author_id = author_id
            else:
                promo = Promo(
                    city=city_name,
                    text=text,
                    image_file_id=photo,
                    date_expire=date_expire,
                    author_id=author_id
                )
                session.add(promo)
        else:  # mode == "create"
            promo = Promo(
                city=city_name,
                text=text,
                image_file_id=photo,
                date_expire=date_expire,
                author_id=author_id
            )
            session.add(promo)

        await session.commit()


@router.message(PromoCreation.waiting_for_expire_date, F.text.regexp(r"^\d{2}\.\d{2}\.\d{4}$"))
async def promo_date_step(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")
    photo = data.get("photo")
    mode = data.get("mode")
    date_str = message.text

    # ✅ Перетворюємо str у datetime.date
    try:
        date_expire = datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        return await message.answer("❌ Невірний формат дати. Введіть у форматі: дд.мм.рррр")

    # Отримуємо автора
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == message.from_user.id)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            return await message.answer("⛔ Ви не є адміном")

        author_id = admin.id
        city_name = admin.city

    await save_promo_to_db(city_name, text, photo, date_expire, mode, author_id)

    await state.clear()
    await message.answer(
        "✅ Акційна пропозиція збережена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Переглянути акцію", callback_data="check_promo")]
        ])
    )

@router.callback_query(F.data == "edit_promo")
async def edit_promo_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✏️ Введіть новий текст акції (можна з фото):",
        reply_markup=cancel_kb()
    )
    await state.update_data(mode="edit")  # режим редагування
    await state.set_state(PromoCreation.waiting_for_text)
    await callback.answer()


@router.message(PromoCreation.waiting_for_expire_date)
async def wrong_date_format(message: Message):
    await message.answer("⚠️ Невірний формат. Спробуйте ще раз: дд.мм.рррр")


@router.callback_query(F.data == "check_promo")
async def check_latest_promo(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()

        if not admin:
            return await callback.message.answer("⛔ Ви не адмін")

        city = admin.city
        result = await session.execute(
            select(Promo).where(Promo.city == city).order_by(Promo.id.desc())
        )
        promo = result.scalars().first()

        if not promo:
            return await callback.message.answer("❌ Акційних пропозицій ще немає")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редагувати", callback_data="edit_promo")],
            [InlineKeyboardButton(text="🗑️ Видалити", callback_data="delete_promo")],
            [InlineKeyboardButton(text="📤 Надіслати на перевірку", callback_data="send_promo_to_co")]
        ])

        if promo.image_file_id:
            await callback.message.answer_photo(
                photo=promo.image_file_id,
                caption=f"🟩 *Текст:* {promo.text or '—'}\n🗓 *До:* {promo.date_expire}",
                parse_mode="Markdown",
                reply_markup=kb
            )
        else:
            await callback.message.answer(
                f"🟩 *Текст:* {promo.text or '—'}\n🗓 *До:* {promo.date_expire}",
                parse_mode="Markdown",
                reply_markup=kb
            )

    await callback.answer()


# Наступний на переробку

@router.callback_query(F.data == "send_promo_to_co")
async def send_promo_to_co(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    bot: Bot = callback.bot
    SUPER_ADMIN_IDS = [887934499, 6539889022]  # 🔒 Вказані ID супер-адмінів

    async with AsyncSessionLocal() as session:
        # Перевірка, що це адмін
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()
        if not admin:
            return await callback.message.answer("⛔ Ви не адміністратор")

        # Остання акція для міста адміна
        result = await session.execute(
            select(Promo).where(Promo.city == admin.city).order_by(Promo.created_at.desc())
        )
        promo = result.scalars().first()
        if not promo:
            return await callback.message.answer("❌ Немає акцій для надсилання")

        # Формування тексту та клавіатури
        text = f"🔔 Акція з міста *{promo.city}*\n\n{promo.text or '-'}\n🗓 До: {promo.date_expire.strftime('%d.%m.%Y')}"
        kb = send_promo_kb(promo)

        # Надсилання кожному зі списку
        sent = 0
        for sa_id in SUPER_ADMIN_IDS:
            try:
                if promo.image_file_id:
                    await bot.send_photo(
                        chat_id=sa_id,
                        photo=promo.image_file_id,
                        caption=text,
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                else:
                    await bot.send_message(
                        chat_id=sa_id,
                        text=text,
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                sent += 1
            except Exception as e:
                print(f"❌ Не вдалося надіслати супер-адміну {sa_id}: {e}")
                continue

    await callback.message.answer(f"✅ Акцію надіслано {sent} супер-адміну(ам)")
    await callback.answer()




@router.callback_query(F.data.startswith("edit_promo:"))
async def edit_promo_callback(callback: CallbackQuery, state: FSMContext):
    promo_id = int(callback.data.split(":")[1])
    await state.set_state(PromoCreation.waiting_for_text)
    await state.update_data(mode="edit", promo_id=promo_id)
    await callback.message.answer("✏️ Введіть новий текст акції (можна з фото):", reply_markup=cancel_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("delete_promo:"))
async def delete_promo_callback(callback: CallbackQuery):
    promo_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).where(Promo.id == promo_id))
        promo = result.scalar_one_or_none()

        if not promo:
            return await callback.message.answer("❌ Акцію не знайдено")

        await session.delete(promo)
        await session.commit()

    await callback.message.answer("🗑️ Акцію видалено")
    await callback.answer()


@router.callback_query(F.data.startswith("reject_promo:"))
async def reject_promo(callback: CallbackQuery, state: FSMContext):
    promo_id = int(callback.data.split(":")[1])
    await state.update_data(promo_id=promo_id)
    await state.set_state(RejectPromo.waiting_for_comment)
    await callback.message.answer("❌ Введіть причину відхилення акції:")
    await callback.answer()


@router.message(RejectPromo.waiting_for_comment)
async def handle_reject_promo_comment(message: Message, state: FSMContext):
    comment = message.text
    data = await state.get_data()
    promo_id = data.get("promo_id")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Promo).where(Promo.id == promo_id))
        promo = result.scalar_one_or_none()

        if not promo:
            await state.clear()
            return await message.answer("❌ Акцію не знайдено")

        if not promo.author_id:
            await state.clear()
            return await message.answer("⚠️ Акція не має автора — неможливо надіслати повідомлення.")

        try:
            await message.bot.send_message(
                promo.author_id,
                f"❌ Ваша акція була відхилена.\n\n📄 Причина: {comment}"
            )
            await message.answer("✅ Причину відхилення надіслано автору.")
        except Exception as e:
            await message.answer(f"⚠️ Не вдалося надіслати повідомлення автору: {e}")

    await state.clear()


@router.callback_query(F.data == "list_promos")
async def list_promos(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()

        if not admin:
            return await callback.message.answer("⛔ Ви не адмін")

        promos_result = await session.execute(
            select(Promo).where(Promo.city == admin.city).order_by(Promo.id.desc())
        )
        promos = promos_result.scalars().all()

        if not promos:
            return await callback.message.answer("📭 Акцій ще немає")

        for promo in promos:
            text = f"📢 Акція:\n{promo.text or '-'}\n🗓 До: {promo.date_expire}"
            try:
                if promo.image_file_id:
                    await callback.message.answer_photo(
                        photo=promo.image_file_id,
                        caption=text,
                        parse_mode="Markdown"
                    )
                else:
                    await callback.message.answer(text, parse_mode="Markdown")

            except Exception as e:
                await callback.message.answer(
                    f"⚠️ Помилка з акцією ID {promo.id}: {str(e)}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_promo:{promo.id}")]
                    ])
                )

    await callback.answer()


@router.callback_query(F.data == "support_co")
async def support_central_office(callback: CallbackQuery):
    await callback.message.answer("@a")
    await callback.answer()


@router.callback_query(F.data == "instruction")
async def instructions(callback: CallbackQuery):
    await callback.message.answer("1. Створюємо пости, користувач буде бачити як Новини\n"
                                  "2. Вводимо текст і вставляємо зображення\n"
                                  "3. Редагуємо, видаляємо\n"
                                  "4. Відправляємо на перевірку ЦО. Розсилку робить ЦО\n"
                                  "ЦО може відхилити надісланий пост\n"
                                  "Створити акцію, має пункт дата закінчення, після закінчення дати\n"
                                  "автоматично видалиться")

    await callback.answer()

